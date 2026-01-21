"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — AGENT EXTENSION                        ║
║                                                                              ║
║  Extension pour intégrer le mode Legal-Safe dans le flux principal.         ║
║  - Détection automatique du profil "legal_safe"                             ║
║  - Injection de kwargs (temperature=0)                                      ║
║  - Post-processing des réponses                                             ║
║  - Logging audit                                                             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from python.helpers.extension import Extension

if TYPE_CHECKING:
    from agent import Agent, LoopData


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENSION CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeModeExtension(Extension):
    """
    Extension pour le mode Legal-Safe.
    
    Hooks utilisés:
    - agent_init: Initialisation du mode
    - monologue_start: Préprocessing de la question
    - system_prompt: Injection du prompt additionnel
    - before_main_llm_call: Force les kwargs
    - response_stream_end: Post-processing de la réponse
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    
    LEGAL_SAFE_PROFILE = "legal_safe"
    FORCED_TEMPERATURE = 0.0
    CORRELATION_ID_KEY = "_legal_safe_correlation_id"
    START_TIME_KEY = "_legal_safe_start_time"
    PRE_TRIGGERS_KEY = "_legal_safe_pre_triggers"
    
    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    
    def is_legal_safe_mode(self, agent: "Agent") -> bool:
        """Vérifie si le mode Legal-Safe est actif."""
        # Vérifier le profil de l'agent
        if agent.config.profile == self.LEGAL_SAFE_PROFILE:
            return True
        
        # Vérifier la variable d'environnement
        env_value = os.environ.get("KOREV_LEGAL_SAFE_MODE", "").lower()
        if env_value in ("true", "1", "yes", "on"):
            return True
        
        return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: agent_init
    # ─────────────────────────────────────────────────────────────────────────
    
    async def execute(self, agent: "Agent", **kwargs):
        """Hook d'initialisation de l'agent."""
        if not self.is_legal_safe_mode(agent):
            return
        
        from python.helpers.print_style import PrintStyle
        
        PrintStyle(
            font_color="yellow",
            background_color="black",
            padding=True,
            bold=True
        ).print("⚖️ LEGAL-SAFE MODE ACTIVATED")
        
        # Forcer temperature=0 dans la config du modèle
        if hasattr(agent.config.chat_model, 'kwargs'):
            agent.config.chat_model.kwargs["temperature"] = self.FORCED_TEMPERATURE
        
        # Logger l'activation
        agent.context.log.log(
            type="info",
            heading="Legal-Safe Mode",
            content="Mode juridique sécurisé activé. Temperature forcée à 0.",
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: monologue_start
    # ─────────────────────────────────────────────────────────────────────────
    
    async def monologue_start(self, agent: "Agent", loop_data: "LoopData", **kwargs):
        """Hook au début du monologue - preprocessing."""
        if not self.is_legal_safe_mode(agent):
            return
        
        # Générer un correlation_id pour cette session
        correlation_id = str(uuid4())
        agent.set_data(self.CORRELATION_ID_KEY, correlation_id)
        agent.set_data(self.START_TIME_KEY, time.time())
        
        # Si on a un message utilisateur, l'analyser
        if loop_data.user_message:
            try:
                from python.helpers.legal_safe_policy import analyze_input
                from python.helpers.legal_safe_schema import ReviewTrigger
                
                # Extraire le texte du message
                msg_content = loop_data.user_message.content
                if isinstance(msg_content, dict):
                    user_text = msg_content.get("message", "")
                elif isinstance(msg_content, str):
                    user_text = msg_content
                else:
                    user_text = str(msg_content)
                
                # Analyser l'input
                analysis = analyze_input(user_text)
                pre_triggers = []
                
                # Collecter les triggers pré-détectés
                if analysis.contains_certainty_request:
                    pre_triggers.append(ReviewTrigger.CERTAINTY_REQUEST)
                    agent.context.log.log(
                        type="warning",
                        heading="Legal-Safe",
                        content="Demande de certitude détectée - escalade probable",
                    )
                
                if analysis.is_restricted_activity:
                    pre_triggers.append(ReviewTrigger.RESTRICTED_ACTIVITY)
                    agent.context.log.log(
                        type="warning",
                        heading="Legal-Safe",
                        content=f"Acte réservé détecté: {analysis.restriction_type}",
                    )
                
                # Stocker pour le post-processing
                agent.set_data(self.PRE_TRIGGERS_KEY, pre_triggers)
                
            except Exception as e:
                from python.helpers.print_style import PrintStyle
                PrintStyle(font_color="red").print(f"Legal-Safe preprocessing error: {e}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: system_prompt
    # ─────────────────────────────────────────────────────────────────────────
    
    async def system_prompt(self, agent: "Agent", system_prompt: list[str], **kwargs):
        """Hook pour injecter le prompt système Legal-Safe."""
        if not self.is_legal_safe_mode(agent):
            return
        
        # Ajouter le rappel des contraintes en tête du prompt
        legal_safe_reminder = """
═══════════════════════════════════════════════════════════════════════════════
⚖️ MODE LEGAL-SAFE ACTIF — CONTRAINTES CRITIQUES
═══════════════════════════════════════════════════════════════════════════════

VOUS DEVEZ:
1. Répondre UNIQUEMENT en JSON conforme au schéma LegalSafeResponse
2. NE JAMAIS affirmer sans source vérifiable
3. Utiliser temperature=0 (déterministe)
4. Déclencher une escalade (requires_human_review=true) si:
   - Confiance < 0.75
   - Aucune citation fiable
   - Domaine pénal
   - Demande de certitude
   - Acte réservé (rédaction, représentation)
5. Inclure TOUJOURS un disclaimer

INTERDICTIONS ABSOLUES:
❌ Inventer des références légales
❌ Donner une certitude absolue
❌ Répondre hors format JSON
❌ Rédiger des actes juridiques

═══════════════════════════════════════════════════════════════════════════════
"""
        
        # Insérer en position 0 pour être prioritaire
        system_prompt.insert(0, legal_safe_reminder)
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: before_main_llm_call
    # ─────────────────────────────────────────────────────────────────────────
    
    async def before_main_llm_call(self, agent: "Agent", loop_data: "LoopData", **kwargs):
        """Hook avant l'appel LLM - forcer les kwargs."""
        if not self.is_legal_safe_mode(agent):
            return
        
        # S'assurer que temperature=0 est forcée
        if hasattr(agent.config.chat_model, 'kwargs'):
            agent.config.chat_model.kwargs["temperature"] = self.FORCED_TEMPERATURE
            agent.config.chat_model.kwargs["top_p"] = 1.0
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: response_stream_end
    # ─────────────────────────────────────────────────────────────────────────
    
    async def response_stream_end(self, agent: "Agent", loop_data: "LoopData", **kwargs):
        """Hook après la réponse - post-processing et logging."""
        if not self.is_legal_safe_mode(agent):
            return
        
        try:
            from python.helpers.legal_safe_runtime import LegalSafeResponseParser
            from python.helpers.legal_safe_logger import log_legal_safe_response, log_legal_safe_error
            from python.helpers.legal_safe_schema import ReviewTrigger
            
            # Récupérer la réponse
            response_text = loop_data.last_response
            if not response_text:
                return
            
            # Récupérer le correlation_id
            correlation_id = agent.get_data(self.CORRELATION_ID_KEY) or str(uuid4())
            start_time = agent.get_data(self.START_TIME_KEY) or time.time()
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Parser la réponse
            parsed, is_valid, error = LegalSafeResponseParser.parse_response(
                response_text,
                correlation_id=correlation_id,
                provider=agent.config.chat_model.provider,
                model=agent.config.chat_model.name,
                latency_ms=latency_ms,
            )
            
            # Ajouter les pre-triggers
            pre_triggers = agent.get_data(self.PRE_TRIGGERS_KEY) or []
            if pre_triggers:
                existing = set(parsed.safety.review_triggers)
                for t in pre_triggers:
                    existing.add(t)
                parsed.safety.review_triggers = list(existing)
                if existing:
                    parsed.safety.requires_human_review = True
            
            # Logger
            if is_valid:
                log_legal_safe_response(parsed)
            else:
                log_legal_safe_error(correlation_id, error or "Unknown error")
            
            # Notifier si escalade requise
            if parsed.safety.requires_human_review:
                triggers_str = ", ".join([t.value for t in parsed.safety.review_triggers])
                agent.context.log.log(
                    type="warning",
                    heading="⚖️ ESCALADE REQUISE",
                    content=f"Validation humaine nécessaire. Triggers: {triggers_str}",
                    kvps={
                        "requires_human_review": True,
                        "review_triggers": [t.value for t in parsed.safety.review_triggers],
                        "confidence": parsed.conclusion.confidence,
                        "correlation_id": correlation_id,
                    }
                )
            
        except Exception as e:
            from python.helpers.print_style import PrintStyle
            PrintStyle(font_color="red").print(f"Legal-Safe post-processing error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

# L'extension est chargée automatiquement par le système d'extensions
