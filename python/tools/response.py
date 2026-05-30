"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RESPONSE TOOL — Point de sortie des réponses              ║
║                                                                              ║
║  Point de sortie UNIQUE des réponses finales de l'agent (chemin chat).       ║
║                                                                              ║
║  GATE CRITIQUE ACTIF (cf. docs/adr/ADR-010-critical-output-doctrine.md) :    ║
║  `execute()` applique la finalisation consolidée `finalize_critical_output`  ║
║  (python/helpers/critical_output.py) AVANT émission :                        ║
║    1. évalue la criticité de la requête (criticality_router),                ║
║    2. exige un consensus_result valide si requires_consensus=True            ║
║       (fail-closed par défaut, fail-soft seulement si policy explicite),     ║
║    3. signe la sortie (9 champs) — fail-closed si secret absent en prod.     ║
║                                                                              ║
║  La sortie signée est exposée via `Response.additional["signed_output"]` et  ║
║  stockée (`_signed_output`) pour consommation par la couche audit.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging

from python.helpers.tool import Tool, Response
from python.helpers.response_contract import validate_response_envelope

logger = logging.getLogger("response_tool")


def _extract_user_query(agent) -> str:
    """Récupère la requête utilisateur courante de façon robuste (pour le routage)."""
    msg = getattr(agent, "last_user_message", None)
    if msg is None:
        return ""
    output_text = getattr(msg, "output_text", None)
    if callable(output_text):
        try:
            return str(output_text())
        except Exception:
            pass
    content = getattr(msg, "content", None)
    if isinstance(content, dict):
        return str(content.get("message") or content.get("text") or json.dumps(content, ensure_ascii=False))
    if content is not None:
        return str(content)
    return str(msg)


def _resolve_model_name(agent) -> str | None:
    cfg = getattr(agent, "config", None)
    chat_model = getattr(cfg, "chat_model", None) if cfg else None
    if chat_model is None:
        return None
    name = getattr(chat_model, "name", None)
    provider = getattr(chat_model, "provider", None)
    provider = getattr(provider, "value", provider)
    if name and provider:
        return f"{provider}/{name}"
    return name or (str(provider) if provider else None)


def _agent_get(agent, key):
    """Lit une donnée sur l'agent puis sur le context (tolérant aux absences)."""
    value = None
    getter = getattr(agent, "get_data", None)
    if callable(getter):
        try:
            value = getter(key)
        except Exception:
            value = None
    if value is None and hasattr(agent, "context"):
        ctx = agent.context
        cgetter = getattr(ctx, "get_data", None)
        if callable(cgetter):
            try:
                value = cgetter(key)
            except Exception:
                value = None
    return value


class ResponseTool(Tool):

    async def execute(self, **kwargs):
        """Finalise et émet la réponse via le gate critique consolidé (ADR-010)."""
        text = self.args.get("text") or self.args.get("answer") or self.args.get("message", "")
        envelope = validate_response_envelope(
            {"text": text},
            fallback_text="Réponse indisponible (erreur de format).",
        )
        text = envelope.text

        # Bypass: réponse déjà finalisée par un pipeline validé (legal/strategic).
        # Le pipeline a déjà appliqué sa propre doctrine ; on ne re-route pas.
        if self.agent.get_data("_pipeline_validated_response"):
            self.agent.set_data("_pipeline_validated_response", None)
            logger.info("Response: pipeline-validated response, gate bypass")
            return Response(message=text, break_loop=True)

        # `requires_consensus` reste None tant que la criticité n'a PAS pu être
        # déterminée. En cas d'erreur du gate, None ⇒ on ne peut PAS prouver que la
        # sortie est non critique ⇒ fail-closed (ADR-010, pas de fail-open silencieux).
        requires_consensus = None
        try:
            from python.helpers.critical_output import (
                finalize_critical_output,
                OutputPolicy,
            )
            from python.helpers.criticality_router import get_criticality_router

            agent_profile = ""
            cfg = getattr(self.agent, "config", None)
            if cfg is not None and getattr(cfg, "profile", None):
                agent_profile = cfg.profile or ""

            query = _extract_user_query(self.agent)
            assessment = get_criticality_router().assess(query=query, agent_profile=agent_profile)
            requires_consensus = bool(assessment.requires_consensus)  # criticité déterminée
            criticality_level = (
                "LEVEL_3" if assessment.requires_consensus
                else ("LEVEL_2" if assessment.strict_evidence_mode else "LEVEL_1")
            )

            consensus_result = _agent_get(self.agent, "_consensus_result")
            policy = OutputPolicy.from_env_or_data(_agent_get(self.agent, "_output_policy"))

            gate_assessment = _agent_get(self.agent, "_gate_assessment")
            trace_id = gate_assessment.get("correlation_id") if isinstance(gate_assessment, dict) else None
            human_review = _agent_get(self.agent, "_human_review_required")

            result = finalize_critical_output(
                output_text=text,
                requires_consensus=requires_consensus,
                criticality_level=criticality_level,
                consensus_result=consensus_result,
                policy=policy,
                input_text=query or None,
                trace_id=trace_id,
                model=_resolve_model_name(self.agent),
                human_review_required=bool(human_review) if human_review is not None else None,
            )

            logger.info(
                "Response gate: decision=%s can_emit=%s requires_consensus=%s [%s]",
                result.decision.value, result.can_emit, requires_consensus, result.correlation_id,
            )

            # Consommer puis purger le consensus_result pour éviter toute fuite vers le tour suivant.
            self.agent.set_data("_consensus_result", None)
            if result.signed_output is not None:
                self.agent.set_data("_signed_output", result.signed_output)

            return Response(
                message=result.output_text,
                break_loop=True,
                additional={"signed_output": result.signed_output} if result.signed_output else None,
            )

        except Exception as exc:
            # Garde-fou (P0-1) : un échec du gate ne doit JAMAIS laisser sortir une
            # réponse critique non signée. On n'émet le texte brut que si la criticité
            # a été POSITIVEMENT établie comme non critique (requires_consensus is False).
            # Si critique (True) ou indéterminée (None) → fail-closed.
            if requires_consensus is False:
                logger.error("Response gate error on non-critical output (emitting raw): %s", exc, exc_info=True)
                return Response(message=text, break_loop=True)
            logger.critical("Response gate error on critical/undetermined output → FAIL-CLOSED: %s", exc, exc_info=True)
            return Response(
                message=(
                    "⛔ **Sortie bloquée (fail-closed).** Une erreur interne a empêché la "
                    "validation/signature de cette réponse, et sa non-criticité n'a pas pu être "
                    "prouvée. Conformément à la doctrine Evidence (ADR-010), la réponse n'est pas émise."
                ),
                break_loop=True,
            )

    async def before_execution(self, **kwargs):
        # don't log here anymore, we have the live_response extension now
        pass

    async def after_execution(self, response, **kwargs):
        # do not add anything to the history or output
        if self.loop_data and "log_item_response" in self.loop_data.params_temporary:
            log = self.loop_data.params_temporary["log_item_response"]
            log.update(finished=True)  # mark the message as finished
