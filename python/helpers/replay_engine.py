"""
Replay Engine — snapshot + re-execution deterministe + detection de divergence.

Capture un snapshot complet de chaque session (inputs, config, outputs)
et permet de rejouer une decision pour verifier l'integrite et la reproductibilite.

Integration :
  - Extension monologue_end/_35_replay_snapshot.py capture automatiquement
  - API /replay permet de declencher un replay a la demande
  - Les snapshots sont stockes dans tmp/chats/{ctxid}/replay_snapshot.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("replay_engine")


class DivergenceLevel(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    SIGNIFICANT = "SIGNIFICANT"
    CRITICAL = "CRITICAL"


@dataclass
class ModelSnapshot:
    """Configuration exacte du modele au moment de l'execution."""
    provider: str = "unknown"
    name: str = "unknown"
    temperature: Optional[float] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionSnapshot:
    """Snapshot complet d'une session pour replay."""

    snapshot_version: str = "1.0.0"
    correlation_id: str = ""
    context_id: str = ""
    session_id: str = ""

    captured_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: Optional[int] = None

    username: Optional[str] = None
    organization: Optional[str] = None
    agent_profile: str = "unknown"

    query: str = ""
    system_prompt_hash: Optional[str] = None
    history_hash: Optional[str] = None
    memory_snapshot_hash: Optional[str] = None

    model_config: ModelSnapshot = field(default_factory=ModelSnapshot)

    response: str = ""
    response_hash: Optional[str] = None

    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    delegation_chain: List[str] = field(default_factory=list)

    execution_budget: Dict[str, Any] = field(default_factory=dict)
    tokens_input: int = 0
    tokens_output: int = 0

    integrity_hash: str = ""

    def compute_integrity(self) -> str:
        """SHA-256 sur les champs critiques pour detecter toute alteration.

        Couvre : identite (context_id, session_id, correlation_id),
        contenu (query, response_hash, system_prompt_hash, history_hash),
        et configuration (model_config).
        """
        payload = json.dumps({
            "context_id": self.context_id,
            "query": self.query,
            "response_hash": self.response_hash,
            "system_prompt_hash": self.system_prompt_hash,
            "history_hash": self.history_hash,
            "model_config": self.model_config.to_dict(),
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
        }, sort_keys=True, ensure_ascii=False)
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["model_config"] = self.model_config.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSnapshot":
        mc = data.pop("model_config", {})
        snap = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        snap.model_config = ModelSnapshot(**{k: v for k, v in mc.items() if k in ModelSnapshot.__dataclass_fields__})
        return snap


@dataclass
class DivergenceReport:
    """Resultat de comparaison entre deux executions."""

    level: DivergenceLevel = DivergenceLevel.NONE
    response_match: bool = True
    response_similarity: float = 1.0
    hash_match: bool = True
    details: List[str] = field(default_factory=list)
    original_hash: str = ""
    replay_hash: str = ""
    compared_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["level"] = self.level.value
        return d


@dataclass
class ReplayOutcome:
    """Resultat complet d'un replay."""

    replay_id: str = ""
    original_snapshot: Optional[SessionSnapshot] = None
    replay_response: str = ""
    replay_response_hash: str = ""
    divergence: DivergenceReport = field(default_factory=DivergenceReport)
    replayed_at: str = ""
    replay_duration_ms: int = 0
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "replayed_at": self.replayed_at,
            "replay_duration_ms": self.replay_duration_ms,
            "success": self.success,
            "error": self.error,
            "replay_response_hash": self.replay_response_hash,
            "divergence": self.divergence.to_dict(),
        }


def _sha256(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def capture_snapshot(
    *,
    context_id: str,
    session_id: str = "",
    query: str = "",
    response: str = "",
    system_prompt: str = "",
    history_text: str = "",
    agent_profile: str = "unknown",
    model_provider: str = "unknown",
    model_name: str = "unknown",
    model_temperature: Optional[float] = None,
    model_kwargs: Optional[Dict[str, Any]] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    delegation_chain: Optional[List[str]] = None,
    execution_budget: Optional[Dict[str, Any]] = None,
    tokens_input: int = 0,
    tokens_output: int = 0,
    username: Optional[str] = None,
    organization: Optional[str] = None,
    correlation_id: str = "",
    started_at: str = "",
) -> SessionSnapshot:
    """Capture un snapshot complet de la session courante."""
    now = datetime.now(timezone.utc)

    snap = SessionSnapshot(
        correlation_id=correlation_id or hashlib.sha256(
            f"{context_id}-{now.isoformat()}".encode()
        ).hexdigest()[:16],
        context_id=context_id,
        session_id=session_id,
        captured_at=now.isoformat(),
        started_at=started_at or now.isoformat(),
        completed_at=now.isoformat(),
        username=username,
        organization=organization,
        agent_profile=agent_profile,
        query=query,
        system_prompt_hash=_sha256(system_prompt) if system_prompt else None,
        history_hash=_sha256(history_text) if history_text else None,
        model_config=ModelSnapshot(
            provider=model_provider,
            name=model_name,
            temperature=model_temperature,
            kwargs=model_kwargs or {},
        ),
        response=response,
        response_hash=_sha256(response) if response else None,
        tool_calls=tool_calls or [],
        delegation_chain=delegation_chain or [],
        execution_budget=execution_budget or {},
        tokens_input=tokens_input,
        tokens_output=tokens_output,
    )

    snap.integrity_hash = snap.compute_integrity()
    return snap


def save_snapshot(snapshot: SessionSnapshot, base_dir: str = "") -> str:
    """Persiste le snapshot en JSON. Retourne le chemin du fichier."""
    if not base_dir:
        from python.helpers.files import get_base_dir
        base_dir = get_base_dir()

    chat_dir = os.path.join(base_dir, "tmp", "chats", snapshot.context_id)
    os.makedirs(chat_dir, exist_ok=True)

    path = os.path.join(chat_dir, "replay_snapshot.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)

    logger.info("Snapshot saved: %s (%s)", path, snapshot.correlation_id)
    return path


def load_snapshot(context_id: str, base_dir: str = "") -> Optional[SessionSnapshot]:
    """Charge un snapshot depuis le filesystem."""
    if not base_dir:
        from python.helpers.files import get_base_dir
        base_dir = get_base_dir()

    path = os.path.join(base_dir, "tmp", "chats", context_id, "replay_snapshot.json")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return SessionSnapshot.from_dict(data)


def compare_responses(original: str, replayed: str) -> DivergenceReport:
    """Compare deux reponses et classifie la divergence."""
    report = DivergenceReport(compared_at=datetime.now(timezone.utc).isoformat())

    orig_hash = _sha256(original)
    replay_hash = _sha256(replayed)
    report.original_hash = orig_hash
    report.replay_hash = replay_hash
    report.hash_match = orig_hash == replay_hash

    if report.hash_match:
        report.level = DivergenceLevel.NONE
        report.response_match = True
        report.response_similarity = 1.0
        return report

    report.response_match = False

    orig_words = set(original.lower().split())
    replay_words = set(replayed.lower().split())
    if orig_words and replay_words:
        intersection = orig_words & replay_words
        union = orig_words | replay_words
        report.response_similarity = len(intersection) / len(union) if union else 0.0
    else:
        report.response_similarity = 0.0

    if report.response_similarity >= 0.95:
        report.level = DivergenceLevel.MINOR
        report.details.append("Reponses quasi-identiques (>95% Jaccard)")
    elif report.response_similarity >= 0.70:
        report.level = DivergenceLevel.SIGNIFICANT
        report.details.append(
            f"Divergence significative ({report.response_similarity:.1%} Jaccard)"
        )
    else:
        report.level = DivergenceLevel.CRITICAL
        report.details.append(
            f"Divergence critique ({report.response_similarity:.1%} Jaccard)"
        )

    if len(original) > 0 and len(replayed) > 0:
        length_ratio = min(len(original), len(replayed)) / max(len(original), len(replayed))
        if length_ratio < 0.5:
            report.details.append(
                f"Difference de longueur importante (ratio={length_ratio:.2f})"
            )
            if report.level != DivergenceLevel.CRITICAL:
                report.level = DivergenceLevel.SIGNIFICANT

    return report


def verify_snapshot_integrity(snapshot: SessionSnapshot) -> bool:
    """Verifie que le snapshot n'a pas ete altere.

    Controle double :
      1. Le hash d'integrite global (champs critiques) correspond au stocke
      2. Le hash de la reponse correspond au contenu reel de response
    """
    if snapshot.integrity_hash != snapshot.compute_integrity():
        return False

    if snapshot.response and snapshot.response_hash:
        actual = _sha256(snapshot.response)
        if actual != snapshot.response_hash:
            return False

    return True
