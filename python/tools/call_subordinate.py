"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DELEGATION TOOL — Collaborative Consensus                 ║
║                                                                              ║
║  Outil de délégation vers agents subordonnés.                                ║
║                                                                              ║
║  CONSENSUS COLLABORATIF (3 rounds):                                          ║
║  - Round 1: 3 LLMs analysent indépendamment les claims                       ║
║  - Round 2: Débat - LLMs voient les analyses des autres                      ║
║  - Round 3: Synthèse et verdict final                                        ║
║                                                                              ║
║  Focus: Détection d'hallucinations, pas juste "sécurité"                     ║
║  Durée: ~30-40 secondes pour un débat complet                                ║
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
from typing import Optional, Dict, Any, List, TYPE_CHECKING

# Type hints pour éviter import circulaire
if TYPE_CHECKING:
    from python.helpers.collaborative_consensus import CollaborativeConsensusResult
    from python.helpers.consensus_manager import ConsensusResult

from agent import Agent, UserMessage
from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle
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
from python.helpers.execution_budget import (
    BudgetExceededError,
    check_delegation,
    get_or_create_state,
    get_limits,
    propagate_budget,
    format_budget_exceeded_response,
)

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

from python.helpers.pipeline_tracker import PipelineTracker
from python.helpers.progress_feedback import emit_delegation_progress

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
                    # HIGH-STAKES DEFINITION (3 critères, OR):
                    # 1. Board-level explicite (keywords stratégiques déclenchés)
                    # 2. Intent critique (legal/medical) présent
                    # 3. Signal stratégique implicite: routing_strength >= 0.65 + finance/legal
                    
                    has_critical_intent = any(
                        i.name in {IntentName.LEGAL_SAFE, IntentName.MEDICAL} 
                        for i in route_decision.intents
                    )
                    
                    has_strategic_signal = (
                        route_decision.routing_strength >= 0.65 and
                        any(i.name in {IntentName.FINANCE, IntentName.LEGAL_SAFE} 
                            for i in route_decision.intents)
                    )
                    
                    is_high_stakes = (
                        route_decision.is_board_level or
                        has_critical_intent or
                        has_strategic_signal
                    )
                    
                    if is_high_stakes:
                        execution_blocked = True
                        # Log avec raison précise
                        reason = []
                        if route_decision.is_board_level:
                            reason.append("board_level")
                        if has_critical_intent:
                            reason.append("critical_intent")
                        if has_strategic_signal:
                            reason.append("strategic_signal")
                        
                        logger.warning(
                            f"[ROUTER_V2] ENFORCEMENT_SOFT | {route_decision.route_id} | "
                            f"Blocking: {route_decision.verdict.value} | "
                            f"reason={'+'.join(reason)}"
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # DELEGATION GUARD: Check budget before creating/invoking subordinate
        # ═══════════════════════════════════════════════════════════════════════
        try:
            budget_state = get_or_create_state(self.agent)
            budget_limits = get_limits(self.agent)
            source_profile = self.agent.config.profile or "default"
            target_profile = agent_profile or "default"
            check_delegation(budget_state, budget_limits, source_profile, target_profile)
        except BudgetExceededError as e:
            logger.warning(
                f"DELEGATION_BLOCKED [{correlation_id}] | {e.reason.value} | {e.detail}"
            )
            return Response(
                message=format_budget_exceeded_response(e),
                break_loop=True,
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
            
            # BUDGET PROPAGATION: share the same budget state with subordinate
            propagate_budget(self.agent, sub)
            
            # Stocker les métadonnées de consensus sur l'agent
            sub.set_data("_consensus_assessment", assessment.to_dict())
            
            # Stocker la décision du router v2 si disponible
            if route_decision is not None:
                sub.set_data("_route_decision_v2", route_decision.to_dict())

        # Récupérer le subordonné
        subordinate: Agent = self.agent.get_data(Agent.DATA_NAME_SUBORDINATE)
        # Ensure budget is always propagated (including when subordinate was reused)
        propagate_budget(self.agent, subordinate)
        subordinate.hist_add_user_message(UserMessage(message=message, attachments=[]))

        # Observer : tracker d'execution de l'agent subordonne
        _tracker = self.agent.get_data("_pipeline_tracker")
        if _tracker is None:
            _tracker = PipelineTracker()
            self.agent.set_data("_pipeline_tracker", _tracker)
        _tracker.start_step(agent_profile or "default")

        _profile_label = agent_profile or "default"
        _step_no = len(_tracker.get_activated())
        emit_delegation_progress(self.agent, _profile_label, _step_no)

        # Exécuter le monologue du subordonné (BudgetExceededError propagates naturally)
        _sub_success = True
        _sub_error: Optional[str] = None
        try:
            result = await subordinate.monologue()
        except Exception as _sub_exc:
            _sub_success = False
            _sub_error = str(_sub_exc)
            _tracker.complete_step(agent_profile or "default", success=False, error=_sub_error)
            raise
        else:
            _tracker.complete_step(agent_profile or "default", success=True)
        
        PrintStyle(font_color="yellow").print(
            f"🔍 AUDIT: subordinate.monologue() returned result (len={len(result) if result else 0}): "
            f"'{str(result)[:200]}...'" if result else "EMPTY/NONE"
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK IF SUBORDINATE USED PIPELINE SHORT-CIRCUIT
        # Si le subordonné a utilisé le pipeline, la réponse est finale.
        # On signal à l'agent principal de terminer (break_loop=True)
        # ═══════════════════════════════════════════════════════════════════════
        pipeline_was_used = subordinate.get_data("_pipeline_was_used")
        adversarial_dossier_id = subordinate.get_data("_adversarial_dossier_id")
        
        if pipeline_was_used:
            PrintStyle(font_color="cyan", bold=True).print(
                f"🔒 SUBORDINATE: Pipeline response - signaling main agent to break loop (result_len={len(result) if result else 0})"
            )
            
            # If adversarial pipeline was used, it already includes PRISM consensus
            # Skip the legacy Collaborative Debate to avoid double-validation
            if adversarial_dossier_id:
                PrintStyle(font_color="green", bold=True).print(
                    f"✅ ADVERSARIAL PIPELINE detected (dossier={adversarial_dossier_id[:8]}) - "
                    f"Skipping legacy Collaborative Debate (consensus already done in pipeline)"
                )
                # Mark as validated and skip consensus check
                self.agent.set_data("_pipeline_validated_response", True)
                self.agent.set_data("_consensus_result", {
                    "approved": True,
                    "source": "adversarial_pipeline",
                    "dossier_id": adversarial_dossier_id,
                    "correlation_id": correlation_id,
                })
                
                return Response(message=result, break_loop=True, additional=None)

        # ═══════════════════════════════════════════════════════════════════════
        # VALIDATION CONSENSUS SI REQUIS (LEGACY - only if not adversarial)
        # ═══════════════════════════════════════════════════════════════════════
        
        if assessment.requires_consensus:
            result = await self._validate_with_consensus(
                result=result,
                message=message,
                assessment=assessment,
                correlation_id=correlation_id,
            )

        # ═══════════════════════════════════════════════════════════════════════
        # CONTRADICTOR AGENT (consume RouteDecision.requires_contradictor)
        # ═══════════════════════════════════════════════════════════════════════
        # The router DECIDES (requires_contradictor=True/False); we EXECUTE.
        # See python/helpers/contradictor/orchestration.py.
        if route_decision is not None:
            try:
                from python.helpers.contradictor.orchestration import (
                    process_contradictor_for_response,
                )

                (
                    contradictor_review,
                    human_review_required,
                    contradictor_audit,
                ) = await process_contradictor_for_response(
                    route_decision=route_decision,
                    user_question=message,
                    agent_response=result,
                    correlation_id=correlation_id,
                )

                # Expose the structured review and human-review flag to the
                # parent agent / envelope consumers.
                self.agent.set_data("_contradictor_review", contradictor_review.to_dict())
                self.agent.set_data("_contradictor_audit", contradictor_audit)
                if human_review_required:
                    self.agent.set_data("_human_review_required", True)
            except Exception as _contradictor_exc:
                # The contradictor pipeline is fail-safe: never break the
                # main response, but always trace the error.
                logger.error(
                    f"[CONTRADICTOR] orchestration error [{correlation_id}]: "
                    f"{_contradictor_exc}"
                )

        # Hint pour longues réponses
        additional = None
        if len(result) >= save_tool_call_file.LEN_MIN:
            hint = self.agent.read_prompt("fw.hint.call_sub.md")
            if hint:
                additional = {"hint": hint}

        # Si le pipeline a été utilisé, on termine le loop principal
        # pour éviter que l'agent principal génère du contenu LLM supplémentaire
        should_break = pipeline_was_used is True
        
        # CRITICAL: Si le pipeline a été utilisé et validé par consensus,
        # on doit le signaler à l'agent principal pour bypasser le gate
        if pipeline_was_used:
            # Marquer que la réponse vient d'un pipeline déjà validé
            self.agent.set_data("_pipeline_validated_response", True)
            # Stocker un résultat de consensus "virtuel" pour le gate
            self.agent.set_data("_consensus_result", {
                "approved": True,
                "source": "subordinate_pipeline",
                "correlation_id": correlation_id,
            })
            PrintStyle(font_color="green", bold=True).print(
                f"🔒 Setting _pipeline_validated_response=True for main agent gate bypass"
            )
        
        return Response(message=result, break_loop=should_break, additional=additional)
    
    async def _validate_with_consensus(
        self,
        result: str,
        message: str,
        assessment: CriticalityAssessment,
        correlation_id: str,
    ) -> str:
        """
        Valide le résultat du subordonné via DÉBAT COLLABORATIF.
        
        Nouveau système (remplace l'ancien vote simple):
        - Round 1: 3 LLMs analysent indépendamment les claims
        - Round 2: Les LLMs débattent en voyant les analyses des autres
        - Round 3: Synthèse et verdict final
        
        Focus: Détection d'hallucinations, pas juste "sécurité"
        
        Si le consensus échoue, retourne une réponse fail-closed.
        """
        try:
            from python.helpers.collaborative_consensus import (
                run_collaborative_consensus,
                DebateVerdict,
            )
            
            logger.info(
                f"🎭 Starting COLLABORATIVE DEBATE for [{correlation_id}]"
            )
            
            # Lancer le débat collaboratif (3 rounds, ~30-40s)
            debate_result = await run_collaborative_consensus(
                response=result,
                question=message,
                correlation_id=correlation_id,
            )
            
            if debate_result.approved:
                logger.info(
                    f"✅ Collaborative Debate APPROVED [{correlation_id}] "
                    f"(verdict={debate_result.verdict.value}, confidence={debate_result.confidence:.0%})"
                )
                # Ajouter un badge de validation détaillé
                return self._add_collaborative_badge(result, debate_result)
            else:
                logger.warning(
                    f"❌ Collaborative Debate REJECTED [{correlation_id}] "
                    f"(verdict={debate_result.verdict.value}, flagged_claims={debate_result.flagged_claims})"
                )
                return self._create_debate_fail_response(
                    message, assessment, debate_result, correlation_id
                )
                
        except Exception as e:
            logger.error(f"Collaborative debate failed: {e}")
            import traceback
            traceback.print_exc()
            # En cas d'erreur, fail-closed
            return self._create_error_response(message, assessment, str(e), correlation_id)
    
    def _add_consensus_badge(
        self,
        result: str,
        consensus_result: "ConsensusResult",
        status: str,
    ) -> str:
        """Ajoute un badge de validation consensus au résultat (legacy)."""
        badge = (
            f"\n\n---\n"
            f"✅ **Consensus Validation**: {status}\n"
            f"- Votes: {consensus_result.vote_count.approvals}/{consensus_result.vote_count.total}\n"
            f"- Decision time: {consensus_result.decision_time_ms}ms\n"
        )
        return result + badge
    
    def _add_collaborative_badge(
        self,
        result: str,
        debate_result: "CollaborativeConsensusResult",
    ) -> str:
        """Ajoute un badge de validation du débat collaboratif."""
        # Construire le badge détaillé
        badge_lines = [
            "\n\n---",
            f"✅ **Débat Collaboratif**: {debate_result.verdict.value.upper()}",
            f"- Confiance: {debate_result.confidence:.0%}",
            f"- Claims analysés: {debate_result.total_claims}",
            f"- Claims vérifiés: {debate_result.verified_claims}",
            f"- Durée: {debate_result.total_duration_ms}ms (3 rounds)",
        ]
        
        # Ajouter les points de consensus si présents
        if debate_result.round3_synthesis.consensus_points:
            badge_lines.append("\n**Points de consensus:**")
            for point in debate_result.round3_synthesis.consensus_points[:3]:
                badge_lines.append(f"  ✓ {point}")
        
        # Ajouter les réserves si verdict avec caveats
        if debate_result.verdict.value == "approved_with_caveats":
            badge_lines.append("\n**Réserves:**")
            if debate_result.round3_synthesis.disagreement_points:
                for point in debate_result.round3_synthesis.disagreement_points[:2]:
                    badge_lines.append(f"  ⚠ {point}")
            badge_lines.append(f"\n*{debate_result.round3_synthesis.recommended_action}*")
        
        return result + "\n".join(badge_lines)
    
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

    def _create_debate_fail_response(
        self,
        message: str,
        assessment: CriticalityAssessment,
        debate_result: "CollaborativeConsensusResult",
        correlation_id: str,
    ) -> str:
        """Crée une réponse fail-closed quand le débat collaboratif détecte des hallucinations."""
        
        # Construire la liste des claims flaggés
        flagged_claims_text = ""
        if debate_result.round3_synthesis.flagged_claims:
            flagged_claims_text = "\n### Claims flaggés (potentielles hallucinations)\n"
            for claim_id, reason in debate_result.round3_synthesis.flagged_claims:
                flagged_claims_text += f"- **{claim_id}**: {reason}\n"
        
        # Construire les points de désaccord
        disagreements_text = ""
        if debate_result.round3_synthesis.disagreement_points:
            disagreements_text = "\n### Points de désaccord entre les experts\n"
            for point in debate_result.round3_synthesis.disagreement_points:
                disagreements_text += f"- {point}\n"
        
        return f"""## ⚠️ Débat Collaboratif — Hallucinations Potentielles Détectées

**Verdict**: {debate_result.verdict.value.upper()}
**Confiance**: {debate_result.confidence:.0%}
**Domaine**: {assessment.domain.value}
**Agent**: {assessment.agent_profile}

### Ce que cela signifie

Trois experts IA ont analysé et débattu la réponse proposée.
Le débat a identifié des **problèmes de fiabilité** qui empêchent la validation.

### Analyse du débat

- **Claims analysés**: {debate_result.total_claims}
- **Claims vérifiés**: {debate_result.verified_claims}
- **Claims flaggés**: {debate_result.flagged_claims}
- **Durée du débat**: {debate_result.total_duration_ms}ms (3 rounds)
{flagged_claims_text}{disagreements_text}
### Recommandation

{debate_result.round3_synthesis.recommended_action}

### Raisonnement

{debate_result.round3_synthesis.reasoning}

### Informations de traçabilité

- Correlation ID: `{correlation_id}`
- Debate ID: `{debate_result.debate_id}`

*Ce système applique le principe "fail-closed": les réponses contenant des hallucinations potentielles ne sont pas transmises.*
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
        
        # Mapper les noms d'intent vers les profils d'agent.
        # CRITIQUE: "contradictor" DOIT mapper sur "contradictor" et JAMAIS
        # sur "default". Le mapping de divergence (router/metrics.py) mappe
        # encore sur "default" mais uniquement pour le calcul de divergence
        # d'audit, pas pour l'orchestration applicative.
        # Source de verite canonique:
        # python/helpers/contradictor/profile_mapping.py
        intent_to_profile = {
            "finance": "finance",
            "sales": "sales",
            "legal_safe": "legal_safe",
            "medical": "medical",
            "developer": "developer",
            "researcher": "researcher",
            "marketing": "marketing",
            "multitask": "default",
            "contradictor": "contradictor",
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
