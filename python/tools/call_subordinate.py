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
║  FEATURE FLAG: DETERMINISTIC_ROUTER_V2=1                                     ║
║  - Active le routage déterministe (policy-driven)                            ║
║  - Logging des décisions de routage pour audit                               ║
║  - Fallback sur comportement existant si désactivé                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import os
import uuid
from typing import Optional, Dict, Any, List

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

# Import deterministic router (feature flag controlled)
try:
    from python.helpers.router import (
        decide_route,
        RouteDecision,
        RouteVerdict,
        IntentName,
        is_deterministic_router_enabled,
        get_enforcement_level,
        _canonicalize_text,  # Shared canonicalization
        RouterMetrics,
    )
    DETERMINISTIC_ROUTER_AVAILABLE = True
except ImportError:
    DETERMINISTIC_ROUTER_AVAILABLE = False
    
    def is_deterministic_router_enabled():
        return False
    
    def get_enforcement_level():
        return 0
    
    def _canonicalize_text(text: str) -> str:
        return text.lower().strip()

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
        
        Feature Flag: DETERMINISTIC_ROUTER_V2=1
        - Active le routage déterministe en parallèle pour audit
        - Log les décisions de routage sans modifier le comportement existant
        """
        # Générer un correlation ID pour traçabilité
        correlation_id = str(uuid.uuid4())
        
        # Récupérer le profil demandé
        agent_profile = kwargs.get("profile", "")
        
        # ═══════════════════════════════════════════════════════════════════════
        # DETERMINISTIC ROUTER (Feature Flag: DETERMINISTIC_ROUTER_V2=1)
        # ═══════════════════════════════════════════════════════════════════════
        # 
        # CANONICALIZATION: _canonicalize_text() est appelée ICI et passée au router.
        # Le même texte canonicalisé doit être utilisé pour criticality.
        # 
        # MODES:
        #   - Audit (actuel): Log + métriques, exécution LLM inchangée
        #   - Enforcement soft (DETERMINISTIC_ROUTER_V2=2): Bloque si router dit REFUSE/CLARIFY sur high-stakes
        #   - Enforcement hard (DETERMINISTIC_ROUTER_V2=3): Remplace entièrement le routing LLM
        # ═══════════════════════════════════════════════════════════════════════
        
        route_decision: Optional["RouteDecision"] = None
        canonical_message = _canonicalize_text(message) if DETERMINISTIC_ROUTER_AVAILABLE else message
        
        if DETERMINISTIC_ROUTER_AVAILABLE and is_deterministic_router_enabled():
            import time
            router_start = time.perf_counter()
            
            try:
                # INVARIANT: canonical_message est la seule source de vérité
                # Router, metrics, logs, criticality voient TOUS le même texte
                route_decision = decide_route(canonical_message)
                
                router_latency_ms = (time.perf_counter() - router_start) * 1000
                
                # Log la décision pour audit (avec input_hash pour traçabilité)
                logger.info(
                    f"[ROUTER_V2] {route_decision.route_id} | "
                    f"hash={route_decision.input_hash} | "
                    f"Verdict: {route_decision.verdict.value} | "
                    f"Intents: {route_decision.intent_names} | "
                    f"BoardLevel: {route_decision.is_board_level} | "
                    f"Strength: {route_decision.routing_strength:.2f} | "
                    f"LLM profile: {agent_profile} | "
                    f"Latency: {router_latency_ms:.2f}ms"
                )
                
                # ─────────────────────────────────────────────────────────────────
                # MÉTRIQUES (exploitables pour audit)
                # ─────────────────────────────────────────────────────────────────
                metrics = RouterMetrics.get_instance()
                
                # Déterminer si l'exécution sera bloquée (enforcement mode)
                enforcement_level = get_enforcement_level()
                router_would_block = route_decision.verdict in (
                    RouteVerdict.NEEDS_CLARIFICATION, 
                    RouteVerdict.REFUSE
                )
                
                # Enforcement soft (level 2): bloquer si high-stakes
                execution_blocked = False
                if enforcement_level >= 2 and router_would_block:
                    is_high_stakes = (
                        route_decision.is_board_level or
                        any(i.name in {IntentName.LEGAL_SAFE, IntentName.MEDICAL} 
                            for i in route_decision.intents)
                    )
                    if is_high_stakes:
                        execution_blocked = True
                        logger.warning(
                            f"[ROUTER_V2] ENFORCEMENT_SOFT | {route_decision.route_id} | "
                            f"Blocking execution: {route_decision.verdict.value}"
                        )
                
                # Enregistrer métriques
                metrics.record_decision(
                    route_id=route_decision.route_id,
                    input_hash=route_decision.input_hash,
                    router_verdict=route_decision.verdict.value,
                    router_intents=route_decision.intent_names,
                    is_board_level=route_decision.is_board_level,
                    llm_profile=agent_profile,
                    latency_ms=router_latency_ms,
                    execution_blocked=execution_blocked,
                )
                
                # Si injection détectée, logger un warning
                if route_decision.injection_blocked:
                    logger.warning(
                        f"[ROUTER_V2] {route_decision.route_id} | "
                        f"INJECTION DETECTED: {route_decision.injection_attempt[:50]}"
                    )
                
                # ─────────────────────────────────────────────────────────────────
                # ENFORCEMENT SOFT: Bloquer et retourner clarification
                # ─────────────────────────────────────────────────────────────────
                if execution_blocked:
                    # Log explicite pour debug futur: "pourquoi l'agent n'a pas répondu"
                    logger.warning(
                        f"[ROUTER_V2] EXECUTION_ABORTED_BY_ROUTER | "
                        f"route_id={route_decision.route_id} | "
                        f"hash={route_decision.input_hash} | "
                        f"verdict={route_decision.verdict.value} | "
                        f"llm_profile={agent_profile} | "
                        f"reason=high_stakes_enforcement"
                    )
                    return Response(
                        message=route_decision.clarification_prompt or 
                            "Votre demande nécessite une clarification avant traitement.",
                        break_loop=False,
                    )
                    
            except Exception as e:
                # Erreur avec rate-limiting (pas de spam)
                if DETERMINISTIC_ROUTER_AVAILABLE:
                    metrics = RouterMetrics.get_instance()
                    input_hash = route_decision.input_hash if route_decision else "unknown"
                    metrics.record_error(e, input_hash)
                else:
                    logger.error(f"[ROUTER_V2] Error: {e}")
                # Continue avec le comportement existant (fallback déterministe)
        
        # ═══════════════════════════════════════════════════════════════════════
        # CRITICALITY ASSESSMENT (Comportement existant)
        # ═══════════════════════════════════════════════════════════════════════
        
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
            
            # Stocker la décision du router v2 si disponible
            if route_decision is not None:
                sub.set_data("_route_decision_v2", route_decision.to_dict())

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

    def _audit_profile_consistency(
        self,
        llm_profile: str,
        route_decision: "RouteDecision",
        correlation_id: str,
    ) -> None:
        """
        Audit de cohérence entre le profil choisi par le LLM et la décision du router.
        
        Cette fonction est pour l'observabilité uniquement - elle ne modifie pas
        le comportement existant. Les divergences sont loggées pour analyse.
        """
        if not llm_profile or not route_decision.intents:
            return
        
        # Mapper les noms d'intent vers les profils d'agent
        intent_to_profile = {
            "finance": "finance",
            "sales": "sales",
            "legal_safe": "legal_safe",
            "medical": "medical",
            "developer": "developer",
            "researcher": "researcher",
            "marketing": "marketing",
            "multitask": "default",
        }
        
        # Vérifier si le profil LLM est dans les intents détectés
        router_profiles = [
            intent_to_profile.get(i.name.value, i.name.value)
            for i in route_decision.intents
        ]
        
        if llm_profile not in router_profiles:
            # Divergence détectée
            logger.warning(
                f"[ROUTER_V2_AUDIT] {correlation_id} | "
                f"DIVERGENCE: LLM chose '{llm_profile}', "
                f"Router detected {router_profiles} | "
                f"BoardLevel: {route_decision.is_board_level}"
            )
        else:
            logger.debug(
                f"[ROUTER_V2_AUDIT] {correlation_id} | "
                f"CONSISTENT: LLM '{llm_profile}' matches router"
            )

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://communication {self.agent.agent_name}: Calling Subordinate Agent",
            content="",
            kvps=self.args,
        )
