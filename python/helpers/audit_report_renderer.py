"""
SESSION 8 / SESSION 14 — AuditReportRenderer: assemblage centralise du rapport d'audit.

Assemble tous les blocs du rapport d'audit Evidence dans l'ordre canonique :

    1. Identite de la session     (SessionEnvelope)
    2. Pipeline d'execution       (PipelineTracker)
    3. Grille de conformite       (ComplianceGrid)
    4. Transparence du raisonnement (SESSION 14 — Art. 13)
    5. Taxonomie des sources      (SourceTaxonomy — quand disponible)
    6. Metadonnees techniques     (ReportMetadata)
    7. Integrite et securite      (IntegrityBlock)
    8. Footer                     (avertissement + Evidence branding)

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

    _AGENT_NARRATIVE_LABELS = {
        "researcher": "Recherche documentaire et veille sectorielle",
        "finance": "Analyse financiere et previsionnelle",
        "marketing": "Analyse marketing et positionnement strategique",
        "sales": "Analyse commerciale et go-to-market",
        "legal_drafting_guarded": "Redaction et analyse juridique",
        "legal_safe": "Verification de conformite reglementaire",
        "developer": "Analyse technique et architecture",
        "medical": "Analyse medicale et reglementaire",
        "hacker": "Tests de robustesse et securite",
        "multitask": "Traitement polyvalent de la requete",
        "default": "Traitement generaliste de la requete",
    }

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
        reasoning_narrative: Optional[str] = None,
        meta_narrative: Optional[str] = None,
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
        self.reasoning_narrative = reasoning_narrative
        self.meta_narrative = meta_narrative
        self.tokens_input: Optional[int] = None
        self.tokens_output: Optional[int] = None

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
        self._add_transparency_narrative(sections)
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
                has_narrative=self.has_narrative,
            )
            grid_table = grid.to_report_table()
            if grid_table:
                sections.append(grid_table)
        except Exception as exc:
            logger.warning("Compliance block failed: %s", exc)

    def _add_transparency_narrative(self, sections: List[str]) -> None:
        """Bloc 4 (SESSION 14): Transparence du raisonnement — Art. 13.

        Produces a non-technical, plain-language explanation of how the system
        reached its result.  No CoT, no prompts, no model names.
        """
        try:
            parts: list[str] = []

            pipeline_narrative = self._build_pipeline_narrative()
            if pipeline_narrative:
                parts.append(pipeline_narrative)

            validation_narrative = self._build_validation_narrative()
            if validation_narrative:
                parts.append(validation_narrative)

            confidence_narrative = self._build_confidence_narrative()
            if confidence_narrative:
                parts.append(confidence_narrative)

            if self.reasoning_narrative:
                parts.append(
                    "**Raisonnement interne**\n\n" + self.reasoning_narrative
                )

            if self.meta_narrative:
                parts.append(
                    "**Evaluation metacognitive**\n\n" + self.meta_narrative
                )

            if not parts:
                return

            sections.append(
                "### Transparence du raisonnement\n\n"
                "> *Cette section explique, en langage non technique, "
                "comment le systeme a produit sa reponse. "
                "Elle repond a l'exigence de transparence de l'Art. 13 "
                "du Reglement AI Act (UE) 2024/1689.*\n\n"
                + "\n\n".join(parts)
            )
        except Exception as exc:
            logger.warning("Transparency narrative block failed: %s", exc)

    def _build_pipeline_narrative(self) -> str:
        """Build a human-readable description of agents consulted."""
        if self.tracker is None:
            return ""
        activated = self.tracker.get_activated()
        if not activated:
            return ""

        lines = ["**Agents specialises consultes**\n"]

        for step in activated:
            label = self._AGENT_NARRATIVE_LABELS.get(
                step.agent_name, step.role_description or "Analyse specialisee"
            )
            status_label = {
                "completed": "termine avec succes",
                "failed": "termine avec erreur",
                "running": "en cours",
            }.get(step.status.value, step.status.value)

            duration_str = ""
            if step.duration_seconds is not None:
                if step.duration_seconds >= 60:
                    minutes = int(step.duration_seconds // 60)
                    secs = int(step.duration_seconds % 60)
                    duration_str = f" ({minutes} min {secs} s)"
                else:
                    duration_str = f" ({step.duration_seconds:.0f} s)"

            lines.append(
                f"- **{step.agent_name.capitalize()}** — "
                f"{label} — {status_label}{duration_str}"
            )

        total_duration = self.tracker.total_duration_ms()
        if total_duration and total_duration > 0:
            total_sec = total_duration / 1000
            if total_sec >= 60:
                m = int(total_sec // 60)
                s = int(total_sec % 60)
                lines.append(f"\nDuree totale de l'analyse : {m} min {s} s.")
            else:
                lines.append(
                    f"\nDuree totale de l'analyse : {total_sec:.0f} secondes."
                )

        return "\n".join(lines)

    def _build_validation_narrative(self) -> str:
        """Build a human-readable description of the validation outcome."""
        strategic_context = []

        if self.document is not None:
            strategic_context.append(
                "Le systeme a produit un document strategique consolide "
                "a partir des analyses des agents specialises."
            )

        if self.has_human_review:
            strategic_context.append(
                "Une revue humaine a ete declenchee pour ce traitement "
                "(mecanisme de supervision Art. 14 AI Act)."
            )

        if self.has_consensus:
            strategic_context.append(
                "Un mecanisme de consensus multi-agents (PRISM) a ete "
                "utilise pour renforcer la fiabilite du resultat."
            )

        if not strategic_context:
            return ""

        return "**Validation et gouvernance**\n\n" + " ".join(strategic_context)

    def _build_confidence_narrative(self) -> str:
        """Build a human-readable description of the confidence assessment."""
        if self.route_decision is None:
            return ""

        parts = []
        try:
            strength = getattr(self.route_decision, "routing_strength", None)
            if strength is not None:
                if strength >= 0.8:
                    level = "elevee"
                elif strength >= 0.6:
                    level = "bonne"
                elif strength >= 0.3:
                    level = "moderee"
                else:
                    level = "faible"
                parts.append(
                    f"Le niveau de confiance du systeme pour ce traitement "
                    f"est **{level}** ({strength:.0%})."
                )

            cat = getattr(self.route_decision, "ai_act_category", None)
            if cat is not None:
                cat_labels = {
                    "MINIMAL_RISK": "risque minimal",
                    "LIMITED_RISK": "risque limite",
                    "HIGH_RISK": "risque eleve",
                    "UNACCEPTABLE": "risque inacceptable",
                }
                cat_name = getattr(cat, "name", str(cat))
                cat_label = cat_labels.get(cat_name, cat_name)
                parts.append(
                    f"Classification AI Act : **{cat_label}**."
                )

            reasons = getattr(self.route_decision, "reasons", None)
            if reasons and isinstance(reasons, list):
                safe_reasons = [str(r)[:100] for r in reasons[:3]]
                parts.append(
                    "Justifications :\n"
                    + "\n".join(f"  - {r}" for r in safe_reasons)
                )
        except Exception:
            pass

        if not parts:
            return ""

        return "**Evaluation de confiance**\n\n" + "\n".join(parts)

    @property
    def has_narrative(self) -> bool:
        """True if the transparency narrative section will be non-empty."""
        if self.reasoning_narrative or self.meta_narrative:
            return True
        if self.tracker is not None and len(self.tracker.get_activated()) > 0:
            return True
        if self.route_decision is not None:
            return True
        if self.document is not None:
            return True
        if self.has_human_review or self.has_consensus:
            return True
        return False

    def _add_source_taxonomy(self, sections: List[str]) -> None:
        """Bloc 5: Taxonomie des sources (SourceTaxonomy)."""
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
        """Bloc 6: Metadonnees techniques (ReportMetadata)."""
        try:
            from python.helpers.report_metadata import ReportMetadata
            meta = ReportMetadata.from_session(
                envelope=self.envelope,
                tracker=self.tracker,
                route_decision=self.route_decision,
                model_config=self.model_config,
                tokens_input=self.tokens_input,
                tokens_output=self.tokens_output,
            )
            sections.append(
                "### Metadonnees techniques\n\n"
                + meta.to_markdown_block()
            )
        except Exception as exc:
            logger.warning("Metadata block failed: %s", exc)

    def _add_integrity(self, sections: List[str]) -> None:
        """Bloc 7: Integrite et securite (IntegrityBlock)."""
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
        """Bloc 8: Footer avec avertissement et branding."""
        sections.append(_FOOTER_TEXT)

    def _resolve_confidence_score(self) -> Optional[float]:
        """Extract confidence/routing_strength from RouteDecision."""
        if self.route_decision is not None:
            try:
                return self.route_decision.routing_strength
            except Exception:
                pass
        return None
