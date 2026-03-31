"""
PipelineTracker — Observer pour le suivi d'execution des agents Evidence.

Collecte les agents actives, leur role, statut, duree d'execution,
et expose la liste des agents non actives (registre complet - actives).

Ce module est un pur observer : il n'influe jamais sur le flux d'execution.
Toute erreur interne au tracker est silencieusement logguee — le pipeline
principal ne doit jamais etre impacte par le tracker.

Thread-safe : utilisation d'un Lock pour gerer les acces concurrents.
"""

import logging
import os
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set

logger = logging.getLogger("pipeline_tracker")


class StepStatus(str, Enum):
    """Statut d'une etape d'agent dans le pipeline."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


AGENT_ROLE_DESCRIPTIONS: Dict[str, str] = {
    "default": "Agent generaliste — traitement par defaut",
    "developer": "Agent developpeur — code, architecture, debug",
    "finance": "Agent financier — analyse, previsions, budgets",
    "hacker": "Agent test/securite — tests de robustesse",
    "legal_drafting_guarded": "Agent redaction juridique — contrats, clauses",
    "legal_safe": "Agent juridique — conformite, reglementation",
    "marketing": "Agent marketing — strategie, positionnement",
    "medical": "Agent medical — sante, reglementation sanitaire",
    "multitask": "Agent polyvalent — requetes generales",
    "researcher": "Agent recherche — veille, sources, donnees",
    "sales": "Agent commercial — ventes, pricing, go-to-market",
}

_SYSTEM_AGENT_REGISTRY: FrozenSet[str] = frozenset(AGENT_ROLE_DESCRIPTIONS.keys())


def _discover_agents_from_filesystem() -> FrozenSet[str]:
    """
    Decouvre les profils d'agents depuis le dossier agents/ du projet.
    Fallback sur le registre statique si le dossier est inaccessible.
    """
    try:
        base = os.path.join(os.path.dirname(__file__), "..", "..", "agents")
        base = os.path.normpath(base)
        if not os.path.isdir(base):
            return _SYSTEM_AGENT_REGISTRY
        dirs = {
            d for d in os.listdir(base)
            if os.path.isdir(os.path.join(base, d)) and not d.startswith("_")
        }
        if not dirs:
            return _SYSTEM_AGENT_REGISTRY
        return frozenset(dirs)
    except Exception:
        logger.debug("Cannot discover agents from filesystem, using static registry")
        return _SYSTEM_AGENT_REGISTRY


def get_full_agent_registry() -> FrozenSet[str]:
    """Registre complet = union du statique et du filesystem."""
    return _SYSTEM_AGENT_REGISTRY | _discover_agents_from_filesystem()


@dataclass
class AgentStep:
    """
    Enregistrement d'une etape d'execution d'un agent dans le pipeline.

    Attributs immutables a la creation : agent_name, role_description.
    Attributs mutes par le tracker : status, started_at, completed_at, duration_ms, error.
    """
    agent_name: str
    role_description: str = ""
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    _start_monotonic: Optional[float] = field(default=None, repr=False)

    def __post_init__(self):
        if not self.role_description:
            self.role_description = AGENT_ROLE_DESCRIPTIONS.get(
                self.agent_name, "Agent specialise"
            )

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.duration_ms is None:
            return None
        return round(self.duration_ms / 1000, 2)

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "role_description": self.role_description,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class PipelineTracker:
    """
    Observer thread-safe pour le suivi du pipeline d'agents Evidence.

    Usage :
        tracker = PipelineTracker()
        tracker.start_step("researcher")
        ...
        tracker.complete_step("researcher")
        activated = tracker.get_activated()
        non_activated = tracker.get_non_activated()
    """

    def __init__(self, registry: Optional[FrozenSet[str]] = None):
        self._registry: FrozenSet[str] = registry or get_full_agent_registry()
        self._steps: Dict[str, AgentStep] = {}
        self._lock = threading.Lock()
        self._order: List[str] = []

    @property
    def registry(self) -> FrozenSet[str]:
        return self._registry

    def start_step(self, agent_name: str, role_description: str = "") -> None:
        """
        Enregistre le demarrage d'un agent.

        Fail-safe : si start_step est appele deux fois pour le meme agent,
        l'ancien step est ecrase avec un warning (pas de crash).
        """
        try:
            with self._lock:
                if agent_name in self._steps:
                    prev = self._steps[agent_name]
                    if prev.status == StepStatus.RUNNING:
                        logger.warning(
                            "start_step(%s) called while already RUNNING — "
                            "overwriting previous step (started_at=%s)",
                            agent_name, prev.started_at,
                        )
                step = AgentStep(
                    agent_name=agent_name,
                    role_description=role_description,
                    status=StepStatus.RUNNING,
                    started_at=datetime.now(timezone.utc).isoformat(),
                    _start_monotonic=time.monotonic(),
                )
                self._steps[agent_name] = step
                if agent_name not in self._order:
                    self._order.append(agent_name)
        except Exception as exc:
            logger.error("PipelineTracker.start_step(%s) failed: %s", agent_name, exc)

    def complete_step(
        self,
        agent_name: str,
        *,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Enregistre la fin d'execution d'un agent.

        Fail-safe :
        - complete_step sans start_step prealable cree un step FAILED avec warning.
        - complete_step sur un step deja completed est un no-op avec warning.
        """
        try:
            with self._lock:
                now_mono = time.monotonic()
                now_utc = datetime.now(timezone.utc).isoformat()

                if agent_name not in self._steps:
                    logger.warning(
                        "complete_step(%s) called without prior start_step — "
                        "creating synthetic FAILED step", agent_name,
                    )
                    self._steps[agent_name] = AgentStep(
                        agent_name=agent_name,
                        status=StepStatus.FAILED,
                        completed_at=now_utc,
                        error=error or "complete_step called without start_step",
                    )
                    if agent_name not in self._order:
                        self._order.append(agent_name)
                    return

                step = self._steps[agent_name]

                if step.status in (StepStatus.COMPLETED, StepStatus.FAILED):
                    logger.warning(
                        "complete_step(%s) called on already %s step — ignoring",
                        agent_name, step.status.value,
                    )
                    return

                step.completed_at = now_utc
                step.status = StepStatus.COMPLETED if success else StepStatus.FAILED
                step.error = error

                if step._start_monotonic is not None:
                    step.duration_ms = max(
                        0, int((now_mono - step._start_monotonic) * 1000)
                    )
        except Exception as exc:
            logger.error("PipelineTracker.complete_step(%s) failed: %s", agent_name, exc)

    def skip_step(self, agent_name: str, reason: str = "") -> None:
        """Marque un agent comme volontairement non execute."""
        try:
            with self._lock:
                self._steps[agent_name] = AgentStep(
                    agent_name=agent_name,
                    status=StepStatus.SKIPPED,
                    error=reason or None,
                )
                if agent_name not in self._order:
                    self._order.append(agent_name)
        except Exception as exc:
            logger.error("PipelineTracker.skip_step(%s) failed: %s", agent_name, exc)

    def get_activated(self) -> List[AgentStep]:
        """
        Retourne les agents qui ont ete actives (RUNNING, COMPLETED, FAILED),
        dans l'ordre d'activation.
        """
        with self._lock:
            active_statuses = {StepStatus.RUNNING, StepStatus.COMPLETED, StepStatus.FAILED}
            return [
                self._steps[name]
                for name in self._order
                if name in self._steps and self._steps[name].status in active_statuses
            ]

    def get_non_activated(self) -> List[str]:
        """
        Retourne les noms des agents du registre qui n'ont pas ete actives,
        tries alphabetiquement.
        """
        with self._lock:
            active_statuses = {StepStatus.RUNNING, StepStatus.COMPLETED, StepStatus.FAILED}
            activated_names = {
                name for name, step in self._steps.items()
                if step.status in active_statuses
            }
            return sorted(self._registry - activated_names)

    def get_step(self, agent_name: str) -> Optional[AgentStep]:
        """Retourne le step d'un agent specifique, ou None."""
        with self._lock:
            return self._steps.get(agent_name)

    def total_duration_ms(self) -> int:
        """Somme des durees de tous les steps completes."""
        with self._lock:
            return sum(
                s.duration_ms for s in self._steps.values()
                if s.duration_ms is not None
            )

    def summary(self) -> Dict[str, int]:
        """Compteurs par statut."""
        with self._lock:
            counts: Dict[str, int] = {}
            for step in self._steps.values():
                counts[step.status.value] = counts.get(step.status.value, 0) + 1
            return counts

    def to_report_table(self) -> str:
        """Rendu markdown pour le bloc 'Pipeline des agents' du rapport."""
        activated = self.get_activated()
        non_activated = self.get_non_activated()

        lines = [
            "### Agents actives",
            "",
            "| # | Agent | Role | Statut | Duree |",
            "|---|---|---|:---:|---|",
        ]

        for i, step in enumerate(activated, 1):
            status_icon = {
                StepStatus.RUNNING: "⏳",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
            }.get(step.status, "—")

            duration = "—"
            if step.duration_seconds is not None:
                duration = f"{step.duration_seconds}s"

            lines.append(
                f"| {i} | `{step.agent_name}` | {step.role_description} "
                f"| {status_icon} | {duration} |"
            )

        if not activated:
            lines.append("| — | _(aucun agent active)_ | — | — | — |")

        lines.extend([
            "",
            "### Agents non actives",
            "",
        ])

        if non_activated:
            lines.append(", ".join(f"`{n}`" for n in non_activated))
        else:
            lines.append("_(tous les agents ont ete actives)_")

        total = self.total_duration_ms()
        if total > 0:
            lines.extend([
                "",
                f"**Duree totale pipeline** : {round(total / 1000, 2)}s",
            ])

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialisation pour JSON / metadonnees."""
        return {
            "activated": [s.to_dict() for s in self.get_activated()],
            "non_activated": self.get_non_activated(),
            "summary": self.summary(),
            "total_duration_ms": self.total_duration_ms(),
        }

    def reset(self) -> None:
        """Reinitialise le tracker (nouvelle session)."""
        with self._lock:
            self._steps.clear()
            self._order.clear()
