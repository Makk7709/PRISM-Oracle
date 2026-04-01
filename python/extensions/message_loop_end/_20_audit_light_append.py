"""
SESSION 7B — Audit leger sur reponses LLM classiques.

MECANISME (decision 7B.1, voir FEUILLE_DE_ROUTE SESSION 7B) :
  Hook `message_loop_end` (agent.py L572-576) : execute apres chaque iteration du message loop,
  uniquement lorsque le tool `response` a cree un `log_item_response` via
  `response_stream/_20_live_response.py`. On append un bloc markdown leger
  sur le LogItem UI — sans modifier l'history (evite pollution du prompt LLM).

Pourquoi pas les autres options :
  (a) Hook dans le tool `response` seul : pas d'acces fiable au LogItem final
      et doublon avec le streaming.
  (b) Re-emission streaming : complexe, risque de desync UI.
  (c) Extension message_loop_end : idiomatique, un seul endroit, fail-safe.
  (d) Buffer streaming : invasif sur le chemin critique latence.

Regression pipeline S6+7A :
  Le short-circuit `return pipeline_final_response` sort AVANT la boucle
  message loop : `message_loop_end` n'est jamais appele — comportement identique.

Fail-safe : toute exception est absorbee (reponse deja livree / stream termine).
"""

import logging

from python.helpers.extension import Extension
from python.helpers import audit_light

logger = logging.getLogger("audit_light_append")


class AuditLightAppend(Extension):
    """Append un bloc audit synthetique au log de reponse (flux classique)."""

    async def execute(self, loop_data=None, **kwargs):
        try:
            if getattr(self.agent, "number", 0) != 0:
                return

            log_item = None
            if loop_data and getattr(loop_data, "params_temporary", None):
                log_item = loop_data.params_temporary.get("log_item_response")

            if log_item is None:
                return

            body = (getattr(loop_data, "last_response", None) or "").strip()
            if not body:
                return

            min_words = audit_light.audit_light_min_words()
            if audit_light.count_words(body) < min_words:
                return

            envelope = self.agent.get_data("_session_envelope")
            session_id = ""
            evidence_version = "unknown"
            if envelope is not None:
                session_id = getattr(envelope, "session_id", "") or ""
                evidence_version = getattr(envelope, "evidence_version", "unknown") or "unknown"

            model_label = audit_light.resolve_model_label(
                getattr(self.agent.config, "chat_model", None)
            )
            block = audit_light.build_audit_light_markdown(
                session_id=session_id,
                model_label=model_label,
                completed_at_iso=audit_light.utc_now_iso(),
                evidence_version=evidence_version,
            )
            log_item.update(content=body + block)
            logger.debug(
                "Audit light appended (words=%s, min=%s)",
                audit_light.count_words(body),
                min_words,
            )
        except Exception as exc:
            logger.warning("AuditLightAppend failed (non-blocking): %s", exc)
