"""
SESSION 6 — Append audit metadata to pipeline responses.

Runs AFTER strategic (_15) and legal (_10) pipeline hooks in monologue_start.
If _pipeline_final_response was set by a pipeline, this hook appends:
  - SessionEnvelope identity table (session_id, hash, timestamps, user)
  - PipelineTracker execution table (agents, roles, durations)

The original response is hashed (SHA-256) BEFORE appending, so the integrity
hash in the SessionEnvelope covers the unmodified pipeline output.

Fail-safe: any error is logged and swallowed — the original response is
delivered unchanged to the user.
"""

import hashlib
import logging

from python.helpers.extension import Extension

logger = logging.getLogger("audit_metadata_append")


class AuditMetadataAppend(Extension):

    async def execute(self, loop_data=None, **kwargs):
        try:
            pipeline_response = self.agent.get_data("_pipeline_final_response")
            if pipeline_response is None:
                return

            sections = []

            # ── SessionEnvelope ──────────────────────────────────────────────
            envelope = self.agent.get_data("_session_envelope")
            if envelope is not None:
                try:
                    envelope.response_hash = (
                        "sha256:"
                        + hashlib.sha256(
                            pipeline_response.encode("utf-8")
                        ).hexdigest()
                    )
                    envelope.complete()
                    sections.append(
                        "### Identite de la session\n\n"
                        + envelope.to_report_table()
                    )
                except Exception as exc:
                    logger.warning("SessionEnvelope.complete() failed: %s", exc)

            # ── PipelineTracker ──────────────────────────────────────────────
            tracker = self._resolve_tracker()
            if tracker is not None:
                try:
                    activated = tracker.get_activated()
                    if activated:
                        sections.append(
                            "### Pipeline d'execution\n\n"
                            + tracker.to_report_table()
                        )
                        non_activated = tracker.get_non_activated()
                        if non_activated:
                            sections.append(
                                "**Agents non actives** : "
                                + ", ".join(sorted(non_activated))
                            )
                except Exception as exc:
                    logger.warning("PipelineTracker render failed: %s", exc)

            if not sections:
                return

            audit_block = (
                "\n\n---\n\n"
                "## Metadonnees d'audit Evidence\n\n"
                + "\n\n".join(sections)
            )

            self.agent.set_data(
                "_pipeline_final_response",
                pipeline_response + audit_block,
            )
            logger.info("Audit metadata appended (%d sections)", len(sections))

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
