"""
SESSION 7A — ReportMetadata: metadonnees techniques du rapport d'audit.

Assemble depuis SessionEnvelope, PipelineTracker et RouteDecision les
informations techniques qui completent le rapport d'audit Evidence :
modele principal, agents actives, score de confiance, temps de traitement,
categorie AI Act, residency.

Fail-safe : toutes les methodes gerent les None / exceptions sans crash.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.session_envelope import SessionEnvelope
    from python.helpers.pipeline_tracker import PipelineTracker
    from python.helpers.router.routing_contract import RouteDecision

logger = logging.getLogger("report_metadata")


@dataclass
class ReportMetadata:
    """Metadonnees techniques pour le rapport d'audit Evidence."""

    session_id: str = ""
    model_primary: str = "unknown"
    agents_activated: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    ai_act_category: str = "unknown"
    data_residency: str = "EU (OVH Cloud, Gravelines)"
    evidence_version: str = "unknown"

    @classmethod
    def from_session(
        cls,
        envelope: Optional["SessionEnvelope"] = None,
        tracker: Optional["PipelineTracker"] = None,
        route_decision: Optional["RouteDecision"] = None,
        model_config=None,
    ) -> "ReportMetadata":
        """Factory: assemble depuis les composants de session.

        Chaque source est optionnelle — les valeurs non-resolubles restent
        aux defauts ("unknown" / None).
        """
        meta = cls()

        if envelope is not None:
            meta.session_id = envelope.session_id or ""
            meta.evidence_version = envelope.evidence_version or "unknown"
            if envelope.duration_ms is not None:
                meta.processing_time_ms = envelope.duration_ms

        if tracker is not None:
            try:
                activated = tracker.get_activated()
                meta.agents_activated = [s.agent_name for s in activated]
            except Exception as exc:
                logger.warning("ReportMetadata: tracker.get_activated() failed: %s", exc)

        if route_decision is not None:
            try:
                cat = route_decision.ai_act_category
                meta.ai_act_category = cat.value if cat else "unknown"
            except Exception:
                pass
            try:
                meta.confidence_score = route_decision.routing_strength
            except Exception:
                pass

        if model_config is not None:
            try:
                name = getattr(model_config, "name", None) or "unknown"
                provider = getattr(model_config, "provider", None) or ""
                meta.model_primary = f"{provider}/{name}" if provider else name
            except Exception:
                pass

        return meta

    def to_dict(self) -> dict:
        """Serialisation dict-safe (JSON-compatible)."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialisation JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown_block(self) -> str:
        """Rendu Markdown pour le rapport d'audit Evidence."""
        rows = [
            ("Session ID", self.session_id or "—"),
            ("Version Evidence", self.evidence_version if self.evidence_version != "unknown" else "unknown (non resolu)"),
            ("Modele principal", f"`{self.model_primary}`" if self.model_primary != "unknown" else "unknown"),
            ("Agents actives", ", ".join(self.agents_activated) if self.agents_activated else "—"),
            ("Score de confiance", f"{self.confidence_score:.2f}" if self.confidence_score is not None else "—"),
            ("Temps de traitement", f"{self.processing_time_ms:,} ms" if self.processing_time_ms is not None else "—"),
            ("Categorie AI Act", self.ai_act_category if self.ai_act_category != "unknown" else "unknown"),
            ("Residence des donnees", self.data_residency),
        ]

        lines = ["| PARAMETRE | VALEUR |", "|---|---|"]
        for label, value in rows:
            lines.append(f"| {label} | {value} |")

        return "\n".join(lines)
