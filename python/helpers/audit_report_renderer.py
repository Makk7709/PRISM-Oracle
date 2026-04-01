"""
SESSION 8 — AuditReportRenderer: assemblage centralise du rapport d'audit.

Assemble tous les blocs du rapport d'audit Evidence dans l'ordre canonique :

    1. Identite de la session     (SessionEnvelope)
    2. Pipeline d'execution       (PipelineTracker)
    3. Grille de conformite       (ComplianceGrid)
    4. Taxonomie des sources      (SourceTaxonomy — quand disponible)
    5. Metadonnees techniques     (ReportMetadata)
    6. Integrite et securite      (IntegrityBlock)
    7. Footer                     (avertissement + Evidence branding)

Remplace l'assemblage bloc-par-bloc de _20_audit_metadata_append.py (S6/7A).
Chaque bloc est fail-safe — si un renderer crashe, les autres sont presents.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.session_envelope import SessionEnvelope
    from python.helpers.pipeline_tracker import PipelineTracker
    from python.helpers.integrity_block import IntegrityBlock

logger = logging.getLogger("audit_report_renderer")

_FOOTER_TEXT = (
    "---\n\n"
    "*Ce rapport d'audit a ete genere automatiquement par **KOREV Evidence**. "
    "Il constitue une trace de conformite pour les obligations de transparence "
    "et de tracabilite exigees par le Reglement AI Act (UE) 2024/1689.*\n\n"
    "*Pour obtenir ce rapport au format PDF, utilisez la commande "
    "`/export_audit` ou contactez votre administrateur Evidence.*\n\n"
    "*Les hashes et signatures permettent de verifier l'integrite de ce rapport. "
    "Toute modification du contenu invalidera les hashes.*"
)


class AuditReportRenderer:
    """Assemble le rapport d'audit complet a partir des composants de session.

    Usage:
        renderer = AuditReportRenderer(
            envelope=envelope,
            tracker=tracker,
            route_decision=route_decision,
            model_config=model_config,
            query=raw_query,
            response=pipeline_response,
        )
        audit_block = renderer.render()  # markdown string or ""
    """

    def __init__(
        self,
        envelope: Optional["SessionEnvelope"] = None,
        tracker: Optional["PipelineTracker"] = None,
        route_decision=None,
        model_config=None,
        query: Optional[str] = None,
        response: Optional[str] = None,
        document: Optional[str] = None,
        source_notes: Optional[dict] = None,
        has_human_review: bool = False,
        has_consensus: bool = False,
    ):
        self.envelope = envelope
        self.tracker = tracker
        self.route_decision = route_decision
        self.model_config = model_config
        self.query = query
        self.response = response
        self.document = document
        self.source_notes = source_notes
        self.has_human_review = has_human_review
        self.has_consensus = has_consensus

    def render(self) -> str:
        """Render the full audit report as a markdown block.

        Returns an empty string if no sections could be rendered.
        The returned string starts with '\\n\\n---\\n\\n' for clean appending.
        """
        if self.envelope is not None and self.response is not None:
            try:
                self.envelope.response_hash = (
                    "sha256:"
                    + hashlib.sha256(self.response.encode("utf-8")).hexdigest()
                )
                self.envelope.complete()
            except Exception as exc:
                logger.warning("SessionEnvelope.complete() failed: %s", exc)

        sections: List[str] = []

        self._add_identity(sections)
        self._add_pipeline(sections)
        self._add_compliance(sections)
        self._add_source_taxonomy(sections)
        self._add_metadata(sections)
        self._add_integrity(sections)
        self._add_footer(sections)

        if not sections:
            return ""

        return (
            "\n\n---\n\n"
            "## Rapport d'audit Evidence\n\n"
            + "\n\n".join(sections)
        )

    def _add_identity(self, sections: List[str]) -> None:
        """Bloc 1: Identite de la session (SessionEnvelope)."""
        if self.envelope is None:
            return
        try:
            sections.append(
                "### Identite de la session\n\n"
                + self.envelope.to_report_table()
            )
        except Exception as exc:
            logger.warning("Identity block failed: %s", exc)

    def _add_pipeline(self, sections: List[str]) -> None:
        """Bloc 2: Pipeline d'execution (PipelineTracker)."""
        if self.tracker is None:
            return
        try:
            activated = self.tracker.get_activated()
            if activated:
                sections.append(
                    "### Pipeline d'execution\n\n"
                    + self.tracker.to_report_table()
                )
        except Exception as exc:
            logger.warning("Pipeline block failed: %s", exc)

    def _add_compliance(self, sections: List[str]) -> None:
        """Bloc 3: Grille de conformite (ComplianceGrid)."""
        try:
            from python.helpers.compliance_grid import ComplianceGrid
            grid = ComplianceGrid.evaluate(
                envelope=self.envelope,
                tracker=self.tracker,
                route_decision=self.route_decision,
                confidence_score=self._resolve_confidence_score(),
                has_human_review=self.has_human_review,
                has_consensus=self.has_consensus,
            )
            grid_table = grid.to_report_table()
            if grid_table:
                sections.append(grid_table)
        except Exception as exc:
            logger.warning("Compliance block failed: %s", exc)

    def _add_source_taxonomy(self, sections: List[str]) -> None:
        """Bloc 4: Taxonomie des sources (SourceTaxonomy)."""
        if not self.source_notes or not isinstance(self.source_notes, dict):
            return
        try:
            rows = []
            for _chunk_id, note in self.source_notes.items():
                title = getattr(note, "title", None) or _chunk_id[:12]
                type_fr = getattr(note, "source_type_fr", None)
                reliability = getattr(note, "reliability_percent", None)
                origin = getattr(note, "source_origin", None)
                if type_fr is None and reliability is None:
                    continue
                rows.append((
                    title,
                    type_fr or "\u2014",
                    f"{reliability}%" if reliability is not None else "\u2014",
                    origin or "\u2014",
                ))
            if not rows:
                return
            lines = [
                "### Taxonomie des sources\n",
                "| Source | Type | Fiabilite | Origine |",
                "|---|---|:---:|---|",
            ]
            for title, type_fr, rel, origin in rows[:20]:
                lines.append(f"| {title} | {type_fr} | {rel} | {origin} |")
            sections.append("\n".join(lines))
        except Exception as exc:
            logger.warning("Source taxonomy block failed: %s", exc)

    def _add_metadata(self, sections: List[str]) -> None:
        """Bloc 5: Metadonnees techniques (ReportMetadata)."""
        try:
            from python.helpers.report_metadata import ReportMetadata
            meta = ReportMetadata.from_session(
                envelope=self.envelope,
                tracker=self.tracker,
                route_decision=self.route_decision,
                model_config=self.model_config,
            )
            sections.append(
                "### Metadonnees techniques\n\n"
                + meta.to_markdown_block()
            )
        except Exception as exc:
            logger.warning("Metadata block failed: %s", exc)

    def _add_integrity(self, sections: List[str]) -> None:
        """Bloc 6: Integrite et securite (IntegrityBlock)."""
        try:
            from python.helpers.integrity_block import IntegrityBlock
            session_id = ""
            if self.envelope is not None:
                session_id = self.envelope.session_id or ""
            block = IntegrityBlock.from_session(
                query=self.query,
                response=self.response,
                document=self.document,
                session_id=session_id,
            )
            sections.append(
                "### Integrite et securite\n\n"
                + block.to_report_table()
            )
        except Exception as exc:
            logger.warning("Integrity block failed: %s", exc)

    def _add_footer(self, sections: List[str]) -> None:
        """Bloc 7: Footer avec avertissement et branding."""
        sections.append(_FOOTER_TEXT)

    def _resolve_confidence_score(self) -> Optional[float]:
        """Extract confidence/routing_strength from RouteDecision."""
        if self.route_decision is not None:
            try:
                return self.route_decision.routing_strength
            except Exception:
                pass
        return None
