"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DELEGATION TOOL — Consensus-Aware                         ║
║                                                                              ║
║  Outil de délégation vers agents subordonnés.                                ║
║                                                                              ║
║  RÈGLES CONSENSUS:                                                           ║
║  - Profils legal_safe, researcher → consensus OBLIGATOIRE                    ║
║  - Strict evidence mode pour ces profils                                     ║
║  - Résultat validé par PRISM avant retour                                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import uuid
from typing import Optional, Dict, Any

from agent import Agent, UserMessage
from python.helpers.tool import Tool, Response
from initialize import initialize_agent
from python.extensions.hist_add_tool_result import _90_save_tool_call_file as save_tool_call_file

# Import consensus components
from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalityAssessment,
    CONSENSUS_REQUIRED_PROFILES,
    get_criticality_router,
)
from python.helpers.consensus_manager import DecisionType, ConsensusStatus

logger = logging.getLogger("delegation_tool")


class Delegation(Tool):
    """
    Outil de délégation avec consensus automatique pour agents critiques.
    """

    async def execute(self, message="", reset="", **kwargs):
        """
        Exécute une délégation vers un agent subordonné.
        
        Si le profil de l'agent est critique (legal_safe, researcher),
        le consensus PRISM est automatiquement activé sur le résultat.
        """
        # Générer un correlation ID pour traçabilité
        correlation_id = str(uuid.uuid4())
        
        # Récupérer le profil demandé
        agent_profile = kwargs.get("profile", "")
        
        # Évaluer la criticité
        router = get_criticality_router()
        assessment = router.assess(
            query=message,
            agent_profile=agent_profile,
        )
        
        # Logger l'évaluation
        if assessment.requires_consensus:
            logger.info(
                f"🔒 Delegation to '{agent_profile}' requires consensus "
                f"[{correlation_id}] - {assessment.reasons}"
            )
        
        # Créer ou récupérer l'agent subordonné
        if (
            self.agent.get_data(Agent.DATA_NAME_SUBORDINATE) is None
            or str(reset).lower().strip() == "true"
        ):
            config = initialize_agent()

            if agent_profile:
                config.profile = agent_profile
            
            # Injecter les flags de consensus dans la config de l'agent
            if assessment.requires_consensus:
                config.require_consensus = True
                config.strict_evidence_mode = assessment.strict_evidence_mode
                config.decision_type = assessment.decision_type.value
                config.correlation_id = correlation_id

            sub = Agent(self.agent.number + 1, config, self.agent.context)
            sub.set_data(Agent.DATA_NAME_SUPERIOR, self.agent)
            self.agent.set_data(Agent.DATA_NAME_SUBORDINATE, sub)
            
            # Stocker les métadonnées de consensus sur l'agent
            sub.set_data("_consensus_assessment", assessment.to_dict())

        # Récupérer le subordonné
        subordinate: Agent = self.agent.get_data(Agent.DATA_NAME_SUBORDINATE)
        subordinate.hist_add_user_message(UserMessage(message=message, attachments=[]))

        # Exécuter le monologue du subordonné
        result = await subordinate.monologue()

        # ═══════════════════════════════════════════════════════════════════════
        # VALIDATION CONSENSUS SI REQUIS
        # ═══════════════════════════════════════════════════════════════════════
        
        if assessment.requires_consensus:
            result = await self._validate_with_consensus(
                result=result,
                message=message,
                assessment=assessment,
                correlation_id=correlation_id,
            )

        # Hint pour longues réponses
        additional = None
        if len(result) >= save_tool_call_file.LEN_MIN:
            hint = self.agent.read_prompt("fw.hint.call_sub.md")
            if hint:
                additional = {"hint": hint}

        return Response(message=result, break_loop=False, additional=additional)
    
    async def _validate_with_consensus(
        self,
        result: str,
        message: str,
        assessment: CriticalityAssessment,
        correlation_id: str,
    ) -> str:
        """
        Valide le résultat du subordonné via consensus PRISM.
        
        Si le consensus échoue, retourne une réponse fail-closed.
        """
        try:
            from python.helpers.consensus_arbiter import (
                seek_consensus,
                ConsensusResult,
            )
            
            # Préparer le contexte pour les arbitres
            context = {
                "original_query": message[:1000],
                "agent_profile": assessment.agent_profile,
                "domain": assessment.domain.value,
                "subordinate_response": result[:3000],  # Tronquer pour arbitres
                "strict_evidence_mode": assessment.strict_evidence_mode,
            }
            
            # Chercher le consensus
            consensus_result = await seek_consensus(
                action=f"Validate response from {assessment.agent_profile} agent",
                context=context,
                decision_type=DecisionType.RESEARCH_VALIDATION,
                correlation_id=correlation_id,
            )
            
            if consensus_result.approved:
                logger.info(
                    f"✅ Consensus APPROVED for delegation [{correlation_id}]"
                )
                # Ajouter un badge de validation
                return self._add_consensus_badge(result, consensus_result, "APPROVED")
            else:
                logger.warning(
                    f"❌ Consensus REJECTED for delegation [{correlation_id}]"
                )
                return self._create_fail_closed_response(
                    message, assessment, consensus_result, correlation_id
                )
                
        except Exception as e:
            logger.error(f"Consensus validation failed: {e}")
            # En cas d'erreur, fail-closed
            return self._create_error_response(message, assessment, str(e), correlation_id)
    
    def _add_consensus_badge(
        self,
        result: str,
        consensus_result: "ConsensusResult",
        status: str,
    ) -> str:
        """Ajoute un badge de validation consensus au résultat."""
        badge = (
            f"\n\n---\n"
            f"✅ **Consensus Validation**: {status}\n"
            f"- Votes: {consensus_result.vote_count.approvals}/{consensus_result.vote_count.total}\n"
            f"- Decision time: {consensus_result.decision_time_ms}ms\n"
        )
        return result + badge
    
    def _create_fail_closed_response(
        self,
        message: str,
        assessment: CriticalityAssessment,
        consensus_result: "ConsensusResult",
        correlation_id: str,
    ) -> str:
        """Crée une réponse fail-closed quand le consensus échoue."""
        return f"""## ⚠️ Consensus non obtenu — Réponse prudente

**Domaine critique détecté**: {assessment.domain.value}
**Agent subordonné**: {assessment.agent_profile}
**Statut consensus**: {consensus_result.status.value}
**Votes**: {consensus_result.vote_count.approvals} approvals / {consensus_result.vote_count.rejections} rejections

### Ce que cela signifie

La réponse de l'agent subordonné n'a pas obtenu le consensus requis des arbitres.
Par principe de précaution (fail-closed), la réponse originale n'est pas transmise.

### Recommandations

1. **Reformuler la question** de manière plus précise
2. **Fournir plus de contexte** pour permettre une analyse plus fiable
3. **Consulter un expert humain** pour ce type de question critique
4. **Vérifier les sources** si la question implique des faits vérifiables

### Informations de traçabilité

- Correlation ID: `{correlation_id}`
- Decision time: {consensus_result.decision_time_ms}ms

*Ce système applique le principe "fail-closed": en cas de doute, aucune affirmation non validée n'est faite.*
"""
    
    def _create_error_response(
        self,
        message: str,
        assessment: CriticalityAssessment,
        error: str,
        correlation_id: str,
    ) -> str:
        """Crée une réponse en cas d'erreur de consensus."""
        return f"""## ⚠️ Erreur de validation consensus

**Domaine critique détecté**: {assessment.domain.value}
**Agent subordonné**: {assessment.agent_profile}
**Erreur**: {error[:200]}

### Ce que cela signifie

Une erreur s'est produite lors de la validation par consensus.
Par précaution, la réponse de l'agent subordonné n'est pas transmise.

### Actions possibles

1. Réessayer la requête
2. Vérifier la configuration des arbitres consensus
3. Contacter l'administrateur système si le problème persiste

- Correlation ID: `{correlation_id}`
"""

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://communication {self.agent.agent_name}: Calling Subordinate Agent",
            content="",
            kvps=self.args,
        )
