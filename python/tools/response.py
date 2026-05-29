"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RESPONSE TOOL — Point de sortie des réponses              ║
║                                                                              ║
║  Point de sortie UNIQUE pour toutes les réponses finales de l'agent.         ║
║                                                                              ║
║  ⚠️ ÉTAT ACTUEL (cf. docs/adr/ADR-009-response-gate-disabled.md):            ║
║     L'intégration du CriticalDecisionGate est DÉSACTIVÉE. `execute()`        ║
║     retourne la réponse directement, SANS validation par consensus, gate,    ║
║     ni evidence stricte. Le bloc gate présent plus bas dans `execute()` est  ║
║     CODE MORT (inatteignable après le `return` anticipé), conservé comme     ║
║     implémentation de référence fail-soft pour une réactivation future       ║
║     (Tranche B — voir ADR-009 pour les critères de réactivation).            ║
║                                                                              ║
║  ⚠️ Tant que le gate n'est pas réactivé et alimenté, AUCUNE garantie de      ║
║     validation des réponses critiques n'est fournie par ce module.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from python.helpers.tool import Tool, Response
from python.helpers.response_contract import validate_response_envelope

logger = logging.getLogger("response_tool")


class ResponseTool(Tool):

    async def execute(self, **kwargs):
        """
        Exécute la réponse finale.

        ⚠️ GATE DÉSACTIVÉ (cf. ADR-009) : retourne la réponse directement, sans
        validation par le CriticalDecisionGate. Le bloc de validation plus bas
        est inatteignable (code mort) et conservé comme référence pour Tranche B.
        """
        # Extraire le texte de réponse
        text = self.args.get("text") or self.args.get("answer") or self.args.get("message", "")
        envelope = validate_response_envelope(
            {"text": text},
            fallback_text="Réponse indisponible (erreur de format).",
        )

        # ═══════════════════════════════════════════════════════════════════════
        # GATE DE SORTIE DÉSACTIVÉ — return direct (cf. ADR-009)
        # ═══════════════════════════════════════════════════════════════════════
        # Historique : la version active du gate déclenchait une bannière
        # « Non validé par consensus » sur quasiment toutes les réponses
        # (consensus_result presque toujours None hors pipeline de recherche),
        # perçue comme un dysfonctionnement. Le gate a alors été court-circuité.
        # Réactivation conditionnée aux critères d'ADR-009 (Tranche B) :
        # bannière limitée au LEVEL 3, consensus_result réellement alimenté,
        # tests end-to-end entrée→sortie.

        logger.info(f"Response tool: returning message directly (length={len(envelope.text)})")
        return Response(message=envelope.text, break_loop=True)

        # ═══════════════════════════════════════════════════════════════════════
        # CODE MORT CI-DESSOUS — inatteignable après le `return` ci-dessus.
        # Implémentation de référence fail-soft conservée pour Tranche B (ADR-009).
        # Ne PAS supposer qu'il s'exécute : il ne s'exécute pas.
        # ═══════════════════════════════════════════════════════════════════════
        
        # ═══════════════════════════════════════════════════════════════════════
        # CRITICAL DECISION GATE — VALIDATION AVANT ÉMISSION
        # ═══════════════════════════════════════════════════════════════════════
        
        try:
            from python.helpers.critical_decision_gate import (
                validate_final_output,
                GateDecision,
            )
            
            # ═══════════════════════════════════════════════════════════════════
            # PIPELINE BYPASS: Si la réponse vient d'un pipeline déjà validé,
            # on bypass le gate pour éviter double validation
            # ═══════════════════════════════════════════════════════════════════
            pipeline_validated = self.agent.get_data("_pipeline_validated_response")
            if pipeline_validated:
                logger.info("Gate bypassed: response from validated pipeline")
                # Clear the flag
                self.agent.set_data("_pipeline_validated_response", None)
                # Return the response directly without gate check
                return Response(message=text, break_loop=True)
            
            # Récupérer le profil de l'agent
            agent_profile = ""
            if hasattr(self.agent, "config") and hasattr(self.agent.config, "profile"):
                agent_profile = self.agent.config.profile or ""
            
            # Récupérer l'evidence pack si disponible (stocké par le pipeline)
            evidence_pack = None
            consensus_result = None
            correlation_id = None
            
            # Check agent.data first (from call_subordinate)
            consensus_result = self.agent.get_data("_consensus_result")
            
            if hasattr(self.agent, "context"):
                if not consensus_result:
                    consensus_result = self.agent.context.get_data("_consensus_result")
                evidence_pack = self.agent.context.get_data("_evidence_pack")
                
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
            
            # ═══════════════════════════════════════════════════════════════════
            # FAIL-SOFT: Ne jamais bloquer complètement, ajouter avertissement
            # ═══════════════════════════════════════════════════════════════════
            if not gate_result.can_emit:
                logger.warning(
                    f"Gate flagged response (fail-soft mode): {gate_result.decision.value} "
                    f"[{gate_result.correlation_id}]"
                )
                # Au lieu de bloquer, on ajoute un avertissement au texte
                warning_banner = self._create_reliability_warning(gate_result)
                text = f"{text}\n\n{warning_banner}"
            elif gate_result.validated_output:
                # Utiliser le texte validé (peut avoir été modifié)
                text = gate_result.validated_output
            
        except ImportError as e:
            # Module pas encore disponible → passer
            logger.debug(f"Gate module not available: {e}")
        except Exception as e:
            # Erreur lors de la validation → log et passer (fail-open pour éviter blocage total)
            logger.error(f"Gate validation error: {e}")
            # En production, on pourrait vouloir fail-closed ici
        
        # ═══════════════════════════════════════════════════════════════════════
        
        return Response(message=text, break_loop=True)
    
    def _create_reliability_warning(self, gate_result) -> str:
        """
        Crée un avertissement de fiabilité au lieu de bloquer.
        
        Approche fail-soft: on informe l'utilisateur du niveau de confiance
        plutôt que de refuser de répondre.
        """
        domain = "général"
        if gate_result.assessment:
            domain = gate_result.assessment.domain.value if hasattr(gate_result.assessment.domain, 'value') else str(gate_result.assessment.domain)
        
        reasons = []
        if gate_result.assessment and gate_result.assessment.reasons:
            reasons = gate_result.assessment.reasons[:3]
        
        warning = f"""
---

⚠️ **Avertissement de fiabilité**

| Domaine | Niveau de confiance | Statut validation |
|---------|---------------------|-------------------|
| {domain.upper()} | À vérifier | Non validé par consensus |

**Recommandations:**
- Cette réponse n'a pas été validée par le système de consensus
- Pour les sujets critiques ({domain}), vérifiez les informations avec des sources officielles
- En cas de doute, consultez un professionnel qualifié

*Correlation ID: {gate_result.correlation_id[:12]}...*
"""
        return warning.strip()

    async def before_execution(self, **kwargs):
        # don't log here anymore, we have the live_response extension now
        pass

    async def after_execution(self, response, **kwargs):
        # do not add anything to the history or output

        if self.loop_data and "log_item_response" in self.loop_data.params_temporary:
            log = self.loop_data.params_temporary["log_item_response"]
            log.update(finished=True) # mark the message as finished
