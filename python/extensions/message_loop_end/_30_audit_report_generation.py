"""
SESSION 9 — Generation et stockage du rapport d'audit (fichier).

Genere un rapport d'audit FICHIER (audit_report.md + audit_report.pdf) dans
le dossier du chat a chaque fin d'iteration du message loop.

Ce hook couvre les reponses LLM classiques (flux non-pipeline).
Pour les pipelines, le rapport est genere dans monologue_start/_20.

Le fichier est stocke dans tmp/chats/{ctxid}/ — meme ACL que chat.json,
supprime automatiquement au chat_remove.

Fail-safe : toute exception est absorbee — la reponse est toujours livree.
"""

import logging

from python.helpers.extension import Extension

logger = logging.getLogger("audit_report_generation")


class AuditReportGeneration(Extension):
    """Genere le fichier rapport d'audit pour les reponses classiques."""

    async def execute(self, loop_data=None, **kwargs):
        try:
            if getattr(self.agent, "number", 0) != 0:
                return

            from agent import AgentContextType
            if self.agent.context.type == AgentContextType.BACKGROUND:
                return

            if self.agent.get_data("_pipeline_final_response") is not None:
                return

            response = ""
            if loop_data is not None:
                response = (getattr(loop_data, "last_response", None) or "").strip()
            if not response:
                return

            envelope = self.agent.get_data("_session_envelope")
            model_config = getattr(self.agent.config, "chat_model", None)
            tokens_in = self.agent.get_data("_llm_tokens_input")
            tokens_out = self.agent.get_data("_llm_tokens_output")

            from python.helpers.audit_report_renderer import AuditReportRenderer
            renderer = AuditReportRenderer(
                envelope=envelope,
                tracker=None,
                route_decision=None,
                model_config=model_config,
                query=envelope.query if envelope else None,
                response=response,
                document=None,
                source_notes=None,
                has_human_review=False,
                has_consensus=False,
            )
            renderer.tokens_input = tokens_in
            renderer.tokens_output = tokens_out

            report_md = renderer.render()
            if not report_md:
                return

            from python.helpers.audit_report_storage import store_audit_report
            store_audit_report(self.agent.context.id, report_md)
            logger.info("Audit report file generated (classic LLM path)")

        except Exception as exc:
            logger.error("AuditReportGeneration failed (non-blocking): %s", exc)
