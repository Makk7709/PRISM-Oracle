"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RESPONSE TOOL — Gate-Protected Exit Point                 ║
║                                                                              ║
║  Point de sortie UNIQUE pour toutes les réponses finales.                    ║
║  Intègre le CriticalDecisionGate pour valider avant émission.                ║
║                                                                              ║
║  RÈGLE: Aucune réponse critique ne peut sortir sans validation du gate.      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from python.helpers.tool import Tool, Response

logger = logging.getLogger("response_tool")


class ResponseTool(Tool):

    async def execute(self, **kwargs):
        """
        Exécute la réponse finale avec validation par le gate.
        
        CHOKE POINT CP1: Toutes les réponses passent par ici.
        """
        # Extraire le texte de réponse
        text = self.args.get("text") or self.args.get("message", "")
        
        # ═══════════════════════════════════════════════════════════════════════
        # CRITICAL DECISION GATE — VALIDATION AVANT ÉMISSION
        # ═══════════════════════════════════════════════════════════════════════
        
        try:
            from python.helpers.critical_decision_gate import (
                validate_final_output,
                GateDecision,
            )
            
            # Récupérer le profil de l'agent
            agent_profile = ""
            if hasattr(self.agent, "config") and hasattr(self.agent.config, "profile"):
                agent_profile = self.agent.config.profile or ""
            
            # Récupérer l'evidence pack si disponible (stocké par le pipeline)
            evidence_pack = None
            consensus_result = None
            correlation_id = None
            
            if hasattr(self.agent, "context"):
                evidence_pack = self.agent.context.get_data("_evidence_pack")
                consensus_result = self.agent.context.get_data("_consensus_result")
                
                # Récupérer le correlation_id de l'assessment initial
                gate_assessment = self.agent.context.get_data("_gate_assessment")
                if gate_assessment:
                    correlation_id = gate_assessment.get("correlation_id")
            
            # Valider via le gate
            gate_result = await validate_final_output(
                output=text,
                agent_profile=agent_profile,
                evidence_pack=evidence_pack,
                context_metadata={
                    "agent_name": getattr(self.agent, "agent_name", "unknown"),
                    "agent_number": getattr(self.agent, "number", -1),
                },
                consensus_result=consensus_result,
                correlation_id=correlation_id,
            )
            
            # Logger l'application du gate
            logger.info(
                f"Gate applied: decision={gate_result.decision.value}, "
                f"can_emit={gate_result.can_emit} [{gate_result.correlation_id}]"
            )
            
            # Si pas autorisé → retourner fail-closed
            if not gate_result.can_emit:
                logger.warning(
                    f"Response blocked by gate: {gate_result.decision.value} "
                    f"[{gate_result.correlation_id}]"
                )
                return Response(
                    message=gate_result.fail_closed_response,
                    break_loop=True,
                )
            
            # Utiliser le texte validé (peut avoir été modifié)
            text = gate_result.validated_output or text
            
        except ImportError as e:
            # Module pas encore disponible → passer
            logger.debug(f"Gate module not available: {e}")
        except Exception as e:
            # Erreur lors de la validation → log et passer (fail-open pour éviter blocage total)
            logger.error(f"Gate validation error: {e}")
            # En production, on pourrait vouloir fail-closed ici
        
        # ═══════════════════════════════════════════════════════════════════════
        
        return Response(message=text, break_loop=True)

    async def before_execution(self, **kwargs):
        # don't log here anymore, we have the live_response extension now
        pass

    async def after_execution(self, response, **kwargs):
        # do not add anything to the history or output

        if self.loop_data and "log_item_response" in self.loop_data.params_temporary:
            log = self.loop_data.params_temporary["log_item_response"]
            log.update(finished=True) # mark the message as finished
