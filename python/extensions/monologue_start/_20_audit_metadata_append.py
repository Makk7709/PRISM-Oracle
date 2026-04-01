"""
SESSION 8 — Append full audit report to pipeline responses.

Runs AFTER strategic (_15) and legal (_10) pipeline hooks in monologue_start.
If _pipeline_final_response was set by a pipeline, this hook delegates to
AuditReportRenderer which assembles the complete audit report:

    1. Identite de la session     (SessionEnvelope)
    2. Pipeline d'execution       (PipelineTracker)
    3. Grille de conformite       (ComplianceGrid)
    4. Taxonomie des sources      (SourceTaxonomy)
    5. Metadonnees techniques     (ReportMetadata)
    6. Integrite et securite      (IntegrityBlock — NEW S8)
    7. Footer                     (avertissement + Evidence branding)

The original response is hashed (SHA-256) BEFORE appending, so the integrity
hash in the SessionEnvelope covers the unmodified pipeline output.

Fail-safe: any error is logged and swallowed — the original response is
delivered unchanged to the user.

IMPORTANT: This hook runs in monologue_start (BEFORE the pipeline short-circuit
at agent.py L415-440). Using message_loop_end would be too late.
"""

import logging

from python.helpers.extension import Extension

logger = logging.getLogger("audit_metadata_append")


class AuditMetadataAppend(Extension):

    async def execute(self, loop_data=None, **kwargs):
        try:
            pipeline_response = self.agent.get_data("_pipeline_final_response")
            if pipeline_response is None:
                return

            envelope = self.agent.get_data("_session_envelope")
            tracker = self._resolve_tracker()
            route_decision = self._resolve_route_decision()
            source_notes = self.agent.get_data("_source_notes")
            model_config = getattr(self.agent.config, "chat_model", None)

            query = None
            if envelope is not None:
                query = envelope.query

            from python.helpers.audit_report_renderer import AuditReportRenderer
            renderer = AuditReportRenderer(
                envelope=envelope,
                tracker=tracker,
                route_decision=route_decision,
                model_config=model_config,
                query=query,
                response=pipeline_response,
                document=None,
                source_notes=source_notes,
                has_human_review=False,
                has_consensus=False,
            )

            audit_block = renderer.render()
            if not audit_block:
                return

            self.agent.set_data(
                "_pipeline_final_response",
                pipeline_response + audit_block,
            )
            logger.info("Audit report appended (renderer v2)")

        except Exception as exc:
            logger.error("AuditMetadataAppend failed (non-blocking): %s", exc)

    def _resolve_tracker(self):
        """Resolve PipelineTracker from strategic result or agent data."""
        try:
            strategic_result = self.agent.get_data("_strategic_result")
            if strategic_result is not None:
                tracker = getattr(strategic_result, "pipeline_tracker", None)
                if tracker is not None:
                    return tracker
            return self.agent.get_data("_pipeline_tracker")
        except Exception:
            return None

    def _resolve_route_decision(self):
        """Resolve RouteDecision from agent data (stored by call_subordinate)."""
        try:
            raw = self.agent.get_data("_route_decision_v2")
            if raw is not None and isinstance(raw, dict):
                from python.helpers.router.routing_contract import RouteDecision
                return RouteDecision.from_dict(raw)
        except Exception as exc:
            logger.debug("RouteDecision resolution failed: %s", exc)
        return None
