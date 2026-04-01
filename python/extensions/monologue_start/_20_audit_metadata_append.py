"""
SESSION 6 + 7A — Append audit metadata to pipeline responses.

Runs AFTER strategic (_15) and legal (_10) pipeline hooks in monologue_start.
If _pipeline_final_response was set by a pipeline, this hook appends:

  S6:  SessionEnvelope identity table (session_id, hash, timestamps, user)
  S6:  PipelineTracker execution table (agents, roles, durations)
  7A:  ComplianceGrid conformity table (AI Act articles, statuses, gaps)
  7A:  Source taxonomy table (source_type_fr, reliability_percent — if data available)
  7A:  ReportMetadata technical metadata (model, confidence, timing, AI Act category)

The original response is hashed (SHA-256) BEFORE appending, so the integrity
hash in the SessionEnvelope covers the unmodified pipeline output.

Fail-safe: any error in any section is logged and swallowed — the original
response is delivered unchanged to the user.

IMPORTANT: This hook runs in monologue_start (BEFORE the pipeline short-circuit
at agent.py L415-440). Using message_loop_end would be too late — the response
would already be returned. See CORRECTION ARCHITECTURALE in the roadmap.
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

            envelope = self.agent.get_data("_session_envelope")
            tracker = self._resolve_tracker()
            route_decision = self._resolve_route_decision()
            sections = []

            # ── S6: SessionEnvelope ──────────────────────────────────────────
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

            # ── S6: PipelineTracker ──────────────────────────────────────────
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

            # ── 7A: ComplianceGrid ───────────────────────────────────────────
            try:
                from python.helpers.compliance_grid import ComplianceGrid
                grid = ComplianceGrid.evaluate(
                    envelope=envelope,
                    tracker=tracker,
                    route_decision=route_decision,
                    confidence_score=self._resolve_confidence_score(route_decision),
                    has_human_review=False,
                    has_consensus=False,
                )
                grid_table = grid.to_report_table()
                if grid_table:
                    sections.append(
                        "### Grille de conformite reglementaire\n\n"
                        + grid_table
                    )
            except Exception as exc:
                logger.warning("ComplianceGrid render failed (non-blocking): %s", exc)

            # ── 7A: Source taxonomy (if source notes available) ────────────
            try:
                source_table = self._render_source_taxonomy()
                if source_table:
                    sections.append(
                        "### Taxonomie des sources\n\n"
                        + source_table
                    )
            except Exception as exc:
                logger.warning("Source taxonomy render failed (non-blocking): %s", exc)

            # ── 7A: ReportMetadata ───────────────────────────────────────────
            try:
                from python.helpers.report_metadata import ReportMetadata
                model_config = getattr(self.agent.config, "chat_model", None)
                meta = ReportMetadata.from_session(
                    envelope=envelope,
                    tracker=tracker,
                    route_decision=route_decision,
                    model_config=model_config,
                )
                sections.append(
                    "### Metadonnees techniques\n\n"
                    + meta.to_markdown_block()
                )
            except Exception as exc:
                logger.warning("ReportMetadata render failed (non-blocking): %s", exc)

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

    # ── Resolvers ────────────────────────────────────────────────────────────

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

    def _resolve_confidence_score(self, route_decision=None):
        """Extract confidence/routing_strength from RouteDecision."""
        if route_decision is not None:
            try:
                return route_decision.routing_strength
            except Exception:
                pass
        return None

    def _render_source_taxonomy(self):
        """Render source taxonomy table from SourceNote objects on the agent.

        SourceNote objects are stored by the legal pipeline via
        agent.set_data("_source_notes", {...}) when available.
        Each SourceNote may carry source_type_fr and reliability_percent
        from the source_taxonomy module (S4).

        Returns None if no source notes are available.
        """
        source_notes = self.agent.get_data("_source_notes")
        if not source_notes or not isinstance(source_notes, dict):
            return None

        rows = []
        for _chunk_id, note in source_notes.items():
            title = getattr(note, "title", None) or _chunk_id[:12]
            type_fr = getattr(note, "source_type_fr", None)
            reliability = getattr(note, "reliability_percent", None)
            origin = getattr(note, "source_origin", None)

            if type_fr is None and reliability is None:
                continue

            rows.append((
                title,
                type_fr or "—",
                f"{reliability}%" if reliability is not None else "—",
                origin or "—",
            ))

        if not rows:
            return None

        lines = [
            "| Source | Type | Fiabilite | Origine |",
            "|---|---|:---:|---|",
        ]
        for title, type_fr, rel, origin in rows[:20]:
            lines.append(f"| {title} | {type_fr} | {rel} | {origin} |")

        return "\n".join(lines)
