"""
SESSION 8 / SESSION 12 / SESSION 14 — Append full audit report to pipeline responses.

Runs AFTER strategic (_15) and legal (_10) pipeline hooks in monologue_start.
If _pipeline_final_response was set by a pipeline, this hook delegates to
AuditReportRenderer which assembles the complete audit report:

    1. Identite de la session     (SessionEnvelope)
    2. Pipeline d'execution       (PipelineTracker)
    3. Grille de conformite       (ComplianceGrid)
    4. Transparence du raisonnement (SESSION 14 — Art. 13)
    5. Taxonomie des sources      (SourceTaxonomy)
    6. Metadonnees techniques     (ReportMetadata)
    7. Integrite et securite      (IntegrityBlock)
    8. Footer                     (avertissement + Evidence branding)

The original response is hashed (SHA-256) BEFORE appending, so the integrity
hash in the SessionEnvelope covers the unmodified pipeline output.

SESSION 12 additions:
  - Backfill envelope.query when _03 extraction missed the raw message
  - Resolve has_human_review dynamically from legal/metacognition signals
  - Resolve has_consensus dynamically from PRISM/pipeline consensus signals

SESSION 14 additions:
  - Resolve reasoning/metacognition narratives from agent data
  - Pass narratives to AuditReportRenderer for Art. 13 transparency section

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

            self._backfill_envelope_query(envelope, loop_data)

            query = None
            if envelope is not None:
                query = envelope.query

            has_human_review = self._resolve_human_review_flag()
            has_consensus = self._resolve_consensus_flag()

            document = self._resolve_document(pipeline_response)

            reasoning_narrative = self._resolve_reasoning_narrative()
            meta_narrative = self._resolve_meta_narrative()

            from python.helpers.audit_report_renderer import AuditReportRenderer
            renderer = AuditReportRenderer(
                envelope=envelope,
                tracker=tracker,
                route_decision=route_decision,
                model_config=model_config,
                query=query,
                response=pipeline_response,
                document=document,
                source_notes=source_notes,
                has_human_review=has_human_review,
                has_consensus=has_consensus,
                reasoning_narrative=reasoning_narrative,
                meta_narrative=meta_narrative,
            )

            tokens_in = self.agent.get_data("_llm_tokens_input")
            tokens_out = self.agent.get_data("_llm_tokens_output")
            renderer.tokens_input = tokens_in
            renderer.tokens_output = tokens_out

            audit_block = renderer.render()
            if not audit_block:
                return

            self.agent.set_data(
                "_pipeline_final_response",
                pipeline_response + audit_block,
            )
            logger.info(
                "Audit report appended (renderer v2, "
                "human_review=%s, consensus=%s)",
                has_human_review, has_consensus,
            )

            self._store_report_file(audit_block)

        except Exception as exc:
            logger.error("AuditMetadataAppend failed (non-blocking): %s", exc)

    def _backfill_envelope_query(self, envelope, loop_data) -> None:
        """SESSION 12.1 — Guarantee envelope.query is non-None.

        _03_session_envelope_init extracts query from loop_data but only
        handles simple string content.  If it missed (dict/list/JSON content),
        the strategic hook's richer extractor may have succeeded.  As last
        resort, re-extract here using the same fallback chain.
        """
        if envelope is None:
            return
        if envelope.query:
            return

        try:
            if loop_data and loop_data.user_message:
                content = getattr(loop_data.user_message, "content", None)
                if isinstance(content, str) and content.strip():
                    envelope.query = content.strip()[:2000]
                    logger.info("Backfill envelope.query from string content")
                    return
                if isinstance(content, dict):
                    raw = (
                        content.get("raw_content")
                        or content.get("user_message")
                        or content.get("message")
                        or content.get("text")
                        or content.get("preview")
                    )
                    if raw and isinstance(raw, str):
                        envelope.query = raw.strip()[:2000]
                        logger.info("Backfill envelope.query from dict content")
                        return
                    if isinstance(raw, dict):
                        text = (
                            raw.get("user_message")
                            or raw.get("message")
                            or raw.get("text")
                        )
                        if text and isinstance(text, str):
                            envelope.query = text.strip()[:2000]
                            logger.info("Backfill envelope.query from nested dict")
                            return
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, str):
                            parts.append(item)
                        elif isinstance(item, dict):
                            parts.append(
                                item.get("text") or item.get("message") or ""
                            )
                    joined = " ".join(filter(None, parts)).strip()
                    if joined:
                        envelope.query = joined[:2000]
                        logger.info("Backfill envelope.query from list content")
                        return

            msg = getattr(self.agent, "last_user_message", None)
            if msg:
                content = getattr(msg, "content", None)
                if isinstance(content, str) and content.strip():
                    envelope.query = content.strip()[:2000]
                    logger.info("Backfill envelope.query from last_user_message")
        except Exception as exc:
            logger.debug("Backfill envelope.query failed: %s", exc)

    def _resolve_human_review_flag(self) -> bool:
        """SESSION 12.2 — Detect if human review was triggered this session.

        Checks three signal sources:
          1. Legal pipeline: parsed output with safety.requires_human_review
          2. Metacognition: escalation to human review via threshold
          3. Explicit agent data flag set by any extension
        """
        try:
            legal_output = self.agent.get_data("_legal_pipeline_output")
            if legal_output is not None:
                safety = getattr(legal_output, "safety", None)
                if safety and getattr(safety, "requires_human_review", False):
                    return True

            if self.agent.get_data("_metacognition_escalation"):
                return True
            if self.agent.get_data("_requires_human_review"):
                return True
        except Exception as exc:
            logger.debug("_resolve_human_review_flag failed: %s", exc)
        return False

    def _resolve_consensus_flag(self) -> bool:
        """SESSION 12.3 — Detect if PRISM consensus was used this session.

        Checks:
          1. _consensus_result dict (set by call_subordinate)
          2. _prism_consensus_used explicit flag
          3. _consensus_assessment from the criticality router
        """
        try:
            cr = self.agent.get_data("_consensus_result")
            if cr is not None and isinstance(cr, dict):
                return True

            if self.agent.get_data("_prism_consensus_used"):
                return True

            assessment = self.agent.get_data("_consensus_assessment")
            if assessment is not None and isinstance(assessment, dict):
                if assessment.get("requires_consensus"):
                    return True
        except Exception as exc:
            logger.debug("_resolve_consensus_flag failed: %s", exc)
        return False

    def _resolve_reasoning_narrative(self):
        """SESSION 14 — Extract reasoning narrative if ReasoningOutcome was persisted."""
        try:
            raw = self.agent.get_data("_reasoning_outcome_safe")
            if raw is not None and isinstance(raw, dict):
                return raw.get("narrative")
        except Exception as exc:
            logger.debug("_resolve_reasoning_narrative failed: %s", exc)
        return None

    def _resolve_meta_narrative(self):
        """SESSION 14 — Extract metacognition narrative if MetaDecision was persisted."""
        try:
            raw = self.agent.get_data("_meta_decision_safe")
            if raw is not None and isinstance(raw, dict):
                return raw.get("narrative")
        except Exception as exc:
            logger.debug("_resolve_meta_narrative failed: %s", exc)
        return None

    def _resolve_document(self, pipeline_response: str):
        """SESSION 13.1 — Resolve the document to hash in the integrity block.

        For strategic pipelines the consolidated response IS the document.
        For other pipelines (legal, etc.) no standalone document exists yet.
        Returns the document string or None.
        """
        try:
            if self.agent.get_data("_strategic_result") is not None:
                return pipeline_response
        except Exception:
            pass
        return None

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

    def _store_report_file(self, audit_block: str) -> None:
        """Best-effort: persist audit report to disk (SESSION 9.1-9.2)."""
        try:
            from python.helpers.audit_report_storage import store_audit_report
            store_audit_report(self.agent.context.id, audit_block)
            logger.info("Audit report file stored (pipeline path)")
        except Exception as exc:
            logger.warning("Report file storage failed (non-blocking): %s", exc)

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
