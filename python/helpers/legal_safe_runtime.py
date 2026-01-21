"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — RUNTIME INTEGRATION                    ║
║                                                                              ║
║  Intégration du mode Legal-Safe dans le runtime Oracle.                     ║
║  Gestion du parsing, validation et post-processing des réponses.            ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Optional
from uuid import uuid4

from pydantic import ValidationError

from .legal_safe_logger import LegalSafeLogger, log_legal_safe_error, log_legal_safe_response
from .legal_safe_policy import (
    InputAnalysis,
    PolicyEvaluation,
    analyze_input,
    check_abuse_pattern,
    evaluate_response,
    validate_citations,
)
from .legal_safe_renderer import render_response, render_quick_summary
from .legal_safe_schema import (
    LegalSafeResponse,
    LegalSafeResponseFactory,
    ReviewTrigger,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Variable d'environnement pour activer le mode Legal-Safe
LEGAL_SAFE_MODE_ENV = "KOREV_LEGAL_SAFE_MODE"

# Température forcée (0 = déterministe)
FORCED_TEMPERATURE = 0.0

# Timeout pour le parsing (secondes)
PARSE_TIMEOUT = 30


# ═══════════════════════════════════════════════════════════════════════════════
# MODE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def is_legal_safe_mode_enabled() -> bool:
    """
    Vérifie si le mode Legal-Safe est activé.
    
    Activation via :
    - Variable d'environnement KOREV_LEGAL_SAFE_MODE=true
    - Profile "legal_safe" dans la configuration
    
    Returns:
        True si le mode est activé
    """
    env_value = os.environ.get(LEGAL_SAFE_MODE_ENV, "").lower()
    return env_value in ("true", "1", "yes", "on")


def get_legal_safe_model_kwargs() -> dict[str, Any]:
    """
    Retourne les kwargs à forcer pour les appels LLM en mode Legal-Safe.
    
    Returns:
        Dict avec temperature=0 et autres paramètres
    """
    return {
        "temperature": FORCED_TEMPERATURE,
        # Pas de sampling aléatoire
        "top_p": 1.0,
        # Réponses déterministes
        "seed": 42,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT PREPROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeInputProcessor:
    """Préprocesseur pour les inputs en mode Legal-Safe."""
    
    def __init__(self):
        self._abuse_tracker: dict[str, list[float]] = {}  # user_id -> list of timestamps
    
    def preprocess(
        self,
        user_input: str,
        user_id: Optional[str] = None,
    ) -> tuple[InputAnalysis, list[ReviewTrigger]]:
        """
        Prétraite l'input utilisateur.
        
        Args:
            user_input: Question de l'utilisateur
            user_id: ID utilisateur (optionnel, pour tracking abuse)
            
        Returns:
            Tuple (analyse, triggers pré-détectés)
        """
        # Analyser l'input
        analysis = analyze_input(user_input)
        
        triggers: list[ReviewTrigger] = []
        
        # Détecter demande de certitude
        if analysis.contains_certainty_request:
            triggers.append(ReviewTrigger.CERTAINTY_REQUEST)
        
        # Détecter acte réservé
        if analysis.is_restricted_activity:
            triggers.append(ReviewTrigger.RESTRICTED_ACTIVITY)
        
        # Détecter conflit d'intérêts potentiel
        if len(analysis.potential_parties) >= 2:
            # Vérifier si les parties sont adverses
            adverse_pairs = [
                ("employeur", "salarié"),
                ("locataire", "propriétaire"),
                ("acheteur", "vendeur"),
                ("créancier", "débiteur"),
                ("plaignant", "prévenu"),
            ]
            for p1, p2 in adverse_pairs:
                if p1 in analysis.potential_parties and p2 in analysis.potential_parties:
                    triggers.append(ReviewTrigger.CONFLICT_OF_INTEREST)
                    break
        
        # Tracking d'abus (si user_id fourni)
        if user_id:
            is_abuse, abuse_type = self._check_abuse(user_id)
            if is_abuse:
                triggers.append(ReviewTrigger.ABUSE_DETECTED)
        
        return analysis, triggers
    
    def _check_abuse(self, user_id: str) -> tuple[bool, Optional[str]]:
        """Vérifie les patterns d'abus pour un utilisateur."""
        now = time.time()
        window = 24 * 60 * 60  # 24h
        
        # Nettoyer les anciennes entrées
        if user_id in self._abuse_tracker:
            self._abuse_tracker[user_id] = [
                ts for ts in self._abuse_tracker[user_id]
                if now - ts < window
            ]
        else:
            self._abuse_tracker[user_id] = []
        
        # Ajouter la requête actuelle
        self._abuse_tracker[user_id].append(now)
        
        # Vérifier le seuil
        query_count = len(self._abuse_tracker[user_id])
        return check_abuse_pattern(query_count, 0.0)  # escalation_rate non calculable ici


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE PARSING
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeResponseParser:
    """Parseur pour les réponses LLM en mode Legal-Safe."""
    
    @staticmethod
    def extract_json_from_response(llm_response: str) -> Optional[dict[str, Any]]:
        """
        Extrait le JSON d'une réponse LLM.
        
        Le JSON peut être :
        - La réponse entière
        - Encapsulé dans des blocs ```json ... ```
        - Encapsulé dans des balises <json> ... </json>
        
        Args:
            llm_response: Réponse brute du LLM
            
        Returns:
            Dict parsé ou None si échec
        """
        # Nettoyer la réponse
        response = llm_response.strip()
        
        # Essayer le parsing direct
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Chercher un bloc ```json
        json_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Chercher des balises <json>
        xml_match = re.search(r'<json>(.*?)</json>', response, re.DOTALL)
        if xml_match:
            try:
                return json.loads(xml_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Chercher le premier { ... } valide
        brace_match = re.search(r'\{.*\}', response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def parse_response(
        llm_response: str,
        correlation_id: Optional[str] = None,
        provider: str = "unknown",
        model: str = "unknown",
        latency_ms: int = 0,
    ) -> tuple[LegalSafeResponse, bool, Optional[str]]:
        """
        Parse et valide une réponse LLM.
        
        Args:
            llm_response: Réponse brute
            correlation_id: ID de corrélation
            provider: Provider LLM
            model: Modèle utilisé
            latency_ms: Latence de l'appel
            
        Returns:
            Tuple (response, is_valid, error_message)
        """
        corr_id = correlation_id or str(uuid4())
        
        # Extraire le JSON
        json_data = LegalSafeResponseParser.extract_json_from_response(llm_response)
        
        if json_data is None:
            # Fallback : JSON non extrait
            error_msg = "Impossible d'extraire un JSON valide de la réponse"
            fallback = LegalSafeResponseFactory.create_fallback_response(
                reason=error_msg,
                provider=provider,
                model=model,
                correlation_id=corr_id,
            )
            return fallback, False, error_msg
        
        # Enrichir avec les métadonnées
        if "meta" not in json_data:
            json_data["meta"] = {}
        json_data["meta"]["correlation_id"] = corr_id
        json_data["meta"]["provider"] = provider
        json_data["meta"]["model"] = model
        json_data["meta"]["latency_ms"] = latency_ms
        json_data["meta"]["temperature"] = FORCED_TEMPERATURE
        
        # Valider avec Pydantic
        try:
            response = LegalSafeResponse.model_validate(json_data)
            return response, True, None
        except ValidationError as e:
            # Fallback : validation échouée
            error_msg = f"Validation du schéma échouée: {e.error_count()} erreurs"
            fallback = LegalSafeResponseFactory.create_fallback_response(
                reason=error_msg,
                provider=provider,
                model=model,
                correlation_id=corr_id,
            )
            return fallback, False, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# POST-PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafePostProcessor:
    """Post-processeur pour les réponses validées."""
    
    @staticmethod
    def process(
        response: LegalSafeResponse,
        input_text: Optional[str] = None,
        pre_triggers: Optional[list[ReviewTrigger]] = None,
    ) -> tuple[LegalSafeResponse, str, PolicyEvaluation]:
        """
        Post-traite une réponse validée.
        
        Args:
            response: Réponse validée
            input_text: Question originale (pour hashing)
            pre_triggers: Triggers détectés en pré-processing
            
        Returns:
            Tuple (response_enrichie, markdown, evaluation)
        """
        # Ajouter les triggers pré-détectés
        if pre_triggers:
            existing = set(response.safety.review_triggers)
            for t in pre_triggers:
                existing.add(t)
            response.safety.review_triggers = list(existing)
            if existing:
                response.safety.requires_human_review = True
        
        # Valider les citations
        citations_valid, citation_issues = validate_citations(response.legal_basis)
        if not citations_valid:
            response.safety.review_triggers.append(ReviewTrigger.MISSING_CITATIONS)
            response.safety.requires_human_review = True
        
        # Calculer les hashes
        if input_text:
            response.compute_hashes(input_text)
        
        # Évaluer avec la policy
        evaluation = evaluate_response(response)
        
        # Synchroniser requires_human_review
        if evaluation.requires_human_review:
            response.safety.requires_human_review = True
        
        # Générer le markdown
        markdown = render_response(response)
        
        # Mettre à jour le champ output
        response.output.user_facing_markdown = markdown
        
        # Logger
        log_legal_safe_response(response, input_text)
        
        return response, markdown, evaluation


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeHandler:
    """
    Handler principal pour le mode Legal-Safe.
    
    Orchestre le preprocessing, parsing et postprocessing.
    """
    
    def __init__(self):
        self.input_processor = LegalSafeInputProcessor()
        self.logger = LegalSafeLogger.get_instance()
    
    def preprocess_input(
        self,
        user_input: str,
        user_id: Optional[str] = None,
    ) -> tuple[InputAnalysis, list[ReviewTrigger]]:
        """Prétraite l'input."""
        return self.input_processor.preprocess(user_input, user_id)
    
    def process_response(
        self,
        llm_response: str,
        user_input: str,
        pre_triggers: list[ReviewTrigger],
        correlation_id: Optional[str] = None,
        provider: str = "unknown",
        model: str = "unknown",
        latency_ms: int = 0,
    ) -> tuple[LegalSafeResponse, str, bool]:
        """
        Traite une réponse LLM complète.
        
        Args:
            llm_response: Réponse brute du LLM
            user_input: Question originale
            pre_triggers: Triggers du preprocessing
            correlation_id: ID de corrélation
            provider: Provider LLM
            model: Modèle
            latency_ms: Latence
            
        Returns:
            Tuple (response, markdown, is_valid)
        """
        corr_id = correlation_id or str(uuid4())
        
        # Parser la réponse
        response, is_valid, error = LegalSafeResponseParser.parse_response(
            llm_response,
            correlation_id=corr_id,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
        )
        
        if not is_valid:
            # Log l'erreur
            log_legal_safe_error(corr_id, error or "Unknown parsing error", user_input)
        
        # Post-traiter
        response, markdown, evaluation = LegalSafePostProcessor.process(
            response,
            input_text=user_input,
            pre_triggers=pre_triggers,
        )
        
        return response, markdown, is_valid
    
    def get_model_kwargs(self) -> dict[str, Any]:
        """Retourne les kwargs à injecter dans l'appel LLM."""
        return get_legal_safe_model_kwargs()
    
    def get_system_prompt_additions(self) -> str:
        """Retourne les ajouts au prompt système."""
        return """
IMPORTANT: Vous êtes en MODE LEGAL-SAFE. Toutes vos réponses DOIVENT être au format JSON conforme au schéma LegalSafeResponse.
- Temperature forcée à 0
- Aucune affirmation sans source
- Escalade automatique si incertitude
- Disclaimers obligatoires
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_handler_instance: Optional[LegalSafeHandler] = None


def get_legal_safe_handler() -> LegalSafeHandler:
    """Retourne l'instance singleton du handler."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = LegalSafeHandler()
    return _handler_instance


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Configuration
    "LEGAL_SAFE_MODE_ENV",
    "FORCED_TEMPERATURE",
    # Detection
    "is_legal_safe_mode_enabled",
    "get_legal_safe_model_kwargs",
    # Classes
    "LegalSafeInputProcessor",
    "LegalSafeResponseParser",
    "LegalSafePostProcessor",
    "LegalSafeHandler",
    # Singleton
    "get_legal_safe_handler",
]
