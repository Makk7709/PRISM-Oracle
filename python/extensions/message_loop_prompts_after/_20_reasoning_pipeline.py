"""
Extension d'intégration du Reasoning Pipeline dans Korev Evidence.

Cette extension s'exécute après la construction des prompts et avant l'appel LLM.
Elle analyse la requête utilisateur et enrichit le contexte avec:
- Un plan structuré (si tâche complexe)
- Des métadonnées de raisonnement
- Des signaux de metacognition

POINT D'INTÉGRATION:
- Hook: message_loop_prompts_after
- Activé par: settings.reasoning_pipeline_enabled (défaut: False pour rétrocompatibilité)

GARANTIES:
- Aucun CoT exposé dans les réponses
- Fallback safe si le pipeline échoue
- Logs structurés sans PII

Author: Korev AI
License: Proprietary
"""

from typing import Any, Dict, Optional
import logging
import json
from datetime import datetime, timezone

from python.helpers.extension import Extension
from agent import Agent, LoopData

# Import conditionnel pour éviter les erreurs si les modules ne sont pas chargés
try:
    from python.helpers.reasoning_engine import (
        ReasoningPipeline,
        ReasoningConfig,
        ReasoningContext,
        ReasoningResult,
        EscalationType,
    )
    from python.helpers.task_planner import TaskPlanner, PlannerConfig
    from python.helpers.metacognition import Metacognition, MetacognitionConfig
    REASONING_AVAILABLE = True
except ImportError:
    REASONING_AVAILABLE = False


# Logger structuré
logger = logging.getLogger("korev.reasoning")


class ReasoningPipelineExtension(Extension):
    """
    Extension pour intégrer le moteur de raisonnement avancé.
    
    S'active uniquement si:
    1. Les modules de reasoning sont disponibles
    2. Le setting reasoning_pipeline_enabled est True
    3. La requête n'est pas triviale
    """
    
    # Cache des instances (singleton par agent profile)
    _pipelines: Dict[str, "ReasoningPipeline"] = {}
    
    async def execute(
        self,
        loop_data: LoopData,
        **kwargs: Any,
    ):
        """
        Point d'entrée de l'extension.
        
        Enrichit le contexte avec les métadonnées de raisonnement
        si le pipeline est activé et pertinent.
        """
        # Vérifier si disponible
        if not REASONING_AVAILABLE:
            return
        
        # Vérifier si activé dans les settings
        if not self._is_enabled():
            return
        
        # Récupérer la dernière requête utilisateur
        user_query = self._extract_user_query(loop_data)
        if not user_query:
            return
        
        # Ignorer les requêtes triviales
        if self._is_trivial_query(user_query):
            return
        
        try:
            # Exécuter le pipeline
            result = await self._run_pipeline(user_query, loop_data)
            
            if result:
                # Enrichir le contexte avec les métadonnées
                self._enrich_context(loop_data, result)
                
                # Logger l'événement (sans contenu user)
                self._log_reasoning_event(result)
                
        except Exception as e:
            # Fallback silencieux - ne pas casser le flux principal
            logger.warning(f"Reasoning pipeline error (non-blocking): {str(e)[:100]}")
    
    def _is_enabled(self) -> bool:
        """Vérifie si le pipeline est activé dans les settings."""
        try:
            from python.helpers import settings
            current_settings = settings.get_settings()
            return current_settings.get("reasoning_pipeline_enabled", False)
        except Exception:
            return False
    
    def _extract_user_query(self, loop_data: LoopData) -> Optional[str]:
        """Extrait la requête utilisateur du contexte."""
        if loop_data.user_message and hasattr(loop_data.user_message, "content"):
            content = loop_data.user_message.content
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Message multimodal - extraire le texte
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        return part.get("text", "")
                    elif isinstance(part, str):
                        return part
        return None
    
    def _is_trivial_query(self, query: str) -> bool:
        """Détecte les requêtes triviales qui ne nécessitent pas de planning."""
        if len(query) < 20:
            return True
        
        trivial_patterns = [
            "hello", "hi", "hey", "bonjour", "salut",
            "thanks", "thank you", "merci",
            "yes", "no", "oui", "non",
            "ok", "okay", "d'accord",
        ]
        
        query_lower = query.lower().strip()
        return any(query_lower.startswith(p) for p in trivial_patterns)
    
    def _get_pipeline(self) -> ReasoningPipeline:
        """Retourne ou crée le pipeline pour ce profil."""
        profile = self.agent.config.profile or "default"
        
        if profile not in self._pipelines:
            # Créer le pipeline avec configuration
            config = ReasoningConfig(
                max_steps=8,
                max_backtracks=2,
                max_tool_calls=12,
                confidence_threshold=0.65,
                enable_self_reflection=True,
            )
            
            pipeline = ReasoningPipeline(config, logger=logger)
            
            # Configurer le planner
            planner_config = PlannerConfig(
                max_goals=3,
                max_tasks_per_goal=4,
            )
            planner = TaskPlanner(planner_config, logger=logger)
            pipeline.set_planner(planner)
            
            # Configurer la metacognition
            meta_config = MetacognitionConfig(
                enable_learning=True,
                stats_file_path=None,  # In-memory seulement
            )
            meta = Metacognition(meta_config, logger=logger)
            pipeline.set_metacognition(meta)
            
            self._pipelines[profile] = pipeline
        
        return self._pipelines[profile]
    
    async def _run_pipeline(
        self,
        query: str,
        loop_data: LoopData,
    ) -> Optional[ReasoningResult]:
        """Exécute le pipeline de raisonnement."""
        pipeline = self._get_pipeline()
        
        # Construire le contexte de session
        session_ctx = {
            "session_id": self.agent.context.id,
            "tools": list(self.agent.get_data("available_tools", [])),
            "user_role": self.agent.config.profile,
            "history": self._get_safe_history(loop_data),
        }
        
        result = await pipeline.run(query, session_ctx)
        
        return result
    
    def _get_safe_history(self, loop_data: LoopData) -> list:
        """Extrait un historique safe (pas de contenu brut)."""
        # Retourner un résumé minimal, pas l'historique complet
        history_len = len(loop_data.history_output) if loop_data.history_output else 0
        return [{"type": "summary", "messages_count": history_len}]
    
    def _enrich_context(self, loop_data: LoopData, result: ReasoningResult):
        """Enrichit le contexte avec les métadonnées de raisonnement."""
        # Ajouter aux extras temporaires (visible uniquement pour ce tour)
        reasoning_meta = {
            "reasoning_enabled": True,
            "confidence": result.confidence,
            "escalation": result.escalation.value,
            "debug_id": result.debug_id,
            "trace_steps": len(result.trace),
        }
        
        loop_data.extras_temporary["_reasoning_meta"] = reasoning_meta
        
        # Si escalation, ajouter un signal
        if result.escalation == EscalationType.ASK_CLARIFY:
            loop_data.extras_temporary["_reasoning_clarify"] = {
                "questions": result.clarification_questions[:2],
            }
        elif result.escalation == EscalationType.HUMAN_REVIEW:
            loop_data.extras_temporary["_reasoning_review"] = {
                "reason": "Low confidence - human review recommended",
            }
    
    def _log_reasoning_event(self, result: ReasoningResult):
        """Log structuré de l'événement de raisonnement."""
        log_entry = {
            "event": "reasoning_completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "debug_id": result.debug_id,
            "confidence": result.confidence,
            "escalation": result.escalation.value,
            "trace_steps": len(result.trace),
            "flags_count": len(result.flags),
        }
        logger.info(json.dumps(log_entry))
