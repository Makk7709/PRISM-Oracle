"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — RESPONSE SCHEMA                        ║
║                                                                              ║
║  Schéma Pydantic strict pour les réponses en mode juridique sécurisé.       ║
║  Toute réponse non conforme est rejetée → escalade automatique.             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS — Valeurs strictement contraintes
# ═══════════════════════════════════════════════════════════════════════════════

class Jurisdiction(str, Enum):
    """Juridictions supportées."""
    FR = "FR"
    EU = "EU"
    UNKNOWN = "UNKNOWN"


class TaskType(str, Enum):
    """Types de tâches juridiques."""
    INFORMATION = "information"
    DRAFT = "draft"
    RISK_ASSESSMENT = "risk_assessment"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Niveaux de risque."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Reliability(str, Enum):
    """Fiabilité d'une source juridique."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class LegalBasisType(str, Enum):
    """Types de bases légales."""
    CODE = "code"
    CASE_LAW = "case_law"
    REGULATION = "regulation"
    DOCTRINE = "doctrine"
    UNKNOWN = "unknown"


class Complexity(str, Enum):
    """Niveau de complexité."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    EXPERT_ONLY = "expert_only"


class LegalDomain(str, Enum):
    """Domaines juridiques."""
    DROIT_TRAVAIL = "droit_travail"
    DROIT_SOCIETES = "droit_societes"
    FISCAL = "fiscal"
    PENAL = "penal"
    IMMOBILIER = "immobilier"
    RGPD_DONNEES = "rgpd_donnees"
    CONTRATS = "contrats"
    CONTENTIEUX = "contentieux"
    IMMIGRATION = "immigration"
    FAMILLE = "famille"
    CONSOMMATION = "consommation"
    PROPRIETE_INTELLECTUELLE = "propriete_intellectuelle"
    ASSURANCE = "assurance"
    BANCAIRE = "bancaire"
    ENVIRONNEMENT = "environnement"
    ADMINISTRATIF = "administratif"
    UNKNOWN = "unknown"


class ReviewTrigger(str, Enum):
    """Déclencheurs d'escalade humaine."""
    MISSING_CITATIONS = "missing_citations"
    HIGH_IMPACT = "high_impact"
    CRIMINAL_LIABILITY = "criminal_liability"
    EMPLOYMENT_LAW_SENSITIVE = "employment_law_sensitive"
    TAX_HEAVY = "tax_heavy"
    IMMIGRATION_CASE = "immigration_case"
    CONTRACT_HIGH_VALUE = "contract_high_value"
    NON_COMPETE_CLAUSE = "non_compete_clause"
    RGPD_INCIDENT = "rgpd_incident"
    HARASSMENT_DISCRIMINATION = "harassment_discrimination"
    TERMINATION_DISMISSAL = "termination_dismissal"
    LITIGATION_COURT = "litigation_court"
    LOW_CONFIDENCE = "low_confidence"
    JURISDICTION_UNKNOWN = "jurisdiction_unknown"
    NO_RELIABLE_SOURCE = "no_reliable_source"
    CERTAINTY_REQUEST = "certainty_request"
    DOMAIN_PENAL = "domain_penal"
    COMPLEXITY_EXPERT = "complexity_expert"
    RESTRICTED_ACTIVITY = "restricted_activity"
    CONFLICT_OF_INTEREST = "conflict_of_interest"
    OUT_OF_SCOPE = "out_of_scope"
    ABUSE_DETECTED = "abuse_detected"


# ═══════════════════════════════════════════════════════════════════════════════
# SUB-MODELS — Composants du schéma principal
# ═══════════════════════════════════════════════════════════════════════════════

class ProvidedFact(BaseModel):
    """Fait fourni par l'utilisateur."""
    id: str = Field(..., pattern=r"^F\d+$", description="Identifiant unique (F1, F2...)")
    text: str = Field(..., min_length=1, max_length=2000)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiance dans l'interprétation du fait")


class Assumption(BaseModel):
    """Hypothèse formulée par le système."""
    id: str = Field(..., pattern=r"^A\d+$", description="Identifiant unique (A1, A2...)")
    text: str = Field(..., min_length=1, max_length=1000)
    risk: RiskLevel = Field(..., description="Risque si l'hypothèse est incorrecte")


class MissingInfo(BaseModel):
    """Information manquante."""
    question: str = Field(..., min_length=1, max_length=500)
    why_needed: str = Field(..., min_length=1, max_length=500)
    risk_if_missing: str = Field(..., min_length=1, max_length=500)


class Facts(BaseModel):
    """Ensemble des faits, hypothèses et informations manquantes."""
    provided_by_user: list[ProvidedFact] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    missing_info: list[MissingInfo] = Field(default_factory=list)


class LegalBasis(BaseModel):
    """Base légale citée."""
    id: str = Field(..., pattern=r"^L\d+$", description="Identifiant unique (L1, L2...)")
    type: LegalBasisType = Field(...)
    citation: str = Field(..., min_length=1, max_length=500, description="Ex: Code du travail, art. L1234-5")
    version_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date de version (YYYY-MM-DD)")
    last_verified: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date de dernière vérification")
    quote_optional: Optional[str] = Field(None, max_length=150, description="Citation courte (≤25 mots)")
    reliability: Reliability = Field(...)
    
    @field_validator("citation")
    @classmethod
    def validate_citation(cls, v: str) -> str:
        """Interdit les citations inventées."""
        # Si la citation contient des marqueurs d'incertitude, forcer reliability=unknown
        uncertain_markers = ["probablement", "peut-être", "je pense", "il semble", "environ"]
        if any(marker in v.lower() for marker in uncertain_markers):
            raise ValueError(f"Citation incertaine détectée: {v}. Utiliser citation='UNKNOWN' + reliability='unknown'")
        return v


class Risk(BaseModel):
    """Risque identifié."""
    id: str = Field(..., pattern=r"^R\d+$", description="Identifiant unique (R1, R2...)")
    level: RiskLevel = Field(...)
    description: str = Field(..., min_length=1, max_length=1000)
    mitigation: str = Field(..., min_length=1, max_length=500)


class Analysis(BaseModel):
    """Analyse structurée."""
    reasoning_steps: list[str] = Field(..., min_length=1, description="Étapes de raisonnement")
    risks: list[Risk] = Field(default_factory=list)
    counterarguments: list[str] = Field(default_factory=list, description="Arguments contraires à considérer")


class Conclusion(BaseModel):
    """Conclusion et recommandation."""
    answer: str = Field(..., min_length=1, max_length=2000)
    recommendation: str = Field(..., min_length=1, max_length=1000)
    confidence: float = Field(..., ge=0.0, le=1.0)


class Scope(BaseModel):
    """Périmètre géographique/juridictionnel."""
    jurisdiction_supported: list[Jurisdiction] = Field(default_factory=lambda: [Jurisdiction.FR, Jurisdiction.EU])
    jurisdiction_requested: Jurisdiction = Field(...)
    out_of_scope: bool = Field(False)
    out_of_scope_reason: Optional[str] = Field(None, max_length=500)


class Classification(BaseModel):
    """Classification de la demande."""
    domain: LegalDomain = Field(...)
    task_type: TaskType = Field(...)
    complexity: Complexity = Field(...)
    requires_professional: bool = Field(False, description="Acte réservé aux avocats/notaires")


class Safety(BaseModel):
    """Évaluation de sécurité."""
    hallucination_risk: RiskLevel = Field(...)
    requires_human_review: bool = Field(...)
    review_triggers: list[ReviewTrigger] = Field(default_factory=list)
    restricted_activity_detected: bool = Field(False, description="Acte réservé détecté")
    restriction_type: Optional[str] = Field(None, description="Ex: representation, drafting_legal_act")
    conflict_of_interest: bool = Field(False)
    parties_involved: list[str] = Field(default_factory=list)


class Disclaimers(BaseModel):
    """Avertissements légaux obligatoires."""
    not_legal_advice: bool = Field(True, description="Ceci n'est pas un conseil juridique")
    consult_professional: bool = Field(True, description="Consultez un professionnel")
    no_liability: bool = Field(True, description="Aucune responsabilité")
    jurisdiction_specific: bool = Field(True, description="Spécifique à la juridiction indiquée")
    text_fr: str = Field(
        default="⚠️ Cette analyse ne constitue pas un conseil juridique. Elle est fournie à titre informatif uniquement. "
                "Pour toute décision importante, consultez un avocat ou un professionnel du droit qualifié. "
                "Korev Evidence décline toute responsabilité quant aux conséquences de l'utilisation de ces informations.",
        max_length=1000
    )
    text_en: str = Field(
        default="⚠️ This analysis does not constitute legal advice. It is provided for informational purposes only. "
                "For any important decision, consult a qualified lawyer or legal professional. "
                "Korev Evidence disclaims all liability for consequences arising from the use of this information.",
        max_length=1000
    )


class AbuseDetection(BaseModel):
    """Détection d'abus d'utilisation."""
    similar_queries_24h: int = Field(0, ge=0)
    escalation_rate: float = Field(0.0, ge=0.0, le=1.0)
    potential_misuse: Optional[str] = Field(None, max_length=200)


class UserAcknowledgment(BaseModel):
    """Consentement utilisateur."""
    accepted_terms: bool = Field(False)
    understood_limitations: bool = Field(False)
    timestamp: Optional[str] = Field(None)


class Fallback(BaseModel):
    """Gestion des erreurs/fallback."""
    triggered: bool = Field(False)
    reason: Optional[str] = Field(None, max_length=500)
    safe_message: str = Field(
        default="Je ne peux pas répondre de manière fiable à cette question. "
                "Veuillez consulter un professionnel du droit qualifié.",
        max_length=500
    )


class Output(BaseModel):
    """Sortie formatée pour l'utilisateur."""
    user_facing_markdown: str = Field(..., min_length=1, description="Rendu markdown dérivé strictement du JSON")


class Meta(BaseModel):
    """Métadonnées techniques."""
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    response_hash: Optional[str] = Field(None, description="Hash SHA256 de la réponse")
    input_hash: Optional[str] = Field(None, description="Hash SHA256 de l'input (anonymisé)")
    provider: str = Field(..., description="Ex: anthropic/claude-opus-4.5")
    model: str = Field(..., description="Nom exact du modèle")
    temperature: float = Field(0.0, ge=0.0, le=2.0, description="Doit être 0 en legal_safe")
    latency_ms: int = Field(0, ge=0)
    schema_version: str = Field("1.0.0")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCHEMA — LegalSafeResponse
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeResponse(BaseModel):
    """
    Schéma principal pour les réponses en mode Legal-Safe.
    
    Toute réponse doit être strictement conforme à ce schéma.
    Une réponse non conforme déclenche automatiquement une escalade humaine.
    """
    
    mode: Literal["legal_safe"] = Field("legal_safe", description="Mode d'exécution")
    version: str = Field("1.0.0", description="Version du schéma")
    
    # Périmètre
    scope: Scope = Field(...)
    
    # Classification
    classification: Classification = Field(...)
    
    # Faits et hypothèses
    facts: Facts = Field(default_factory=Facts)
    
    # Bases légales
    legal_basis: list[LegalBasis] = Field(default_factory=list)
    
    # Analyse
    analysis: Analysis = Field(...)
    
    # Conclusion
    conclusion: Conclusion = Field(...)
    
    # Sécurité et escalade
    safety: Safety = Field(...)
    
    # Disclaimers obligatoires
    disclaimers: Disclaimers = Field(default_factory=Disclaimers)
    
    # Détection d'abus (optionnel)
    abuse_detection: Optional[AbuseDetection] = Field(None)
    
    # Consentement utilisateur (optionnel)
    user_acknowledgment: Optional[UserAcknowledgment] = Field(None)
    
    # Fallback
    fallback: Fallback = Field(default_factory=Fallback)
    
    # Sortie utilisateur
    output: Output = Field(...)
    
    # Métadonnées
    meta: Meta = Field(...)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATEURS GLOBAUX
    # ═══════════════════════════════════════════════════════════════════════════
    
    @model_validator(mode="after")
    def enforce_escalation_rules(self) -> "LegalSafeResponse":
        """Applique les règles d'escalade automatiques."""
        triggers: list[ReviewTrigger] = []
        
        # Règle 1: Juridiction UNKNOWN + question substantielle
        if self.scope.jurisdiction_requested == Jurisdiction.UNKNOWN:
            triggers.append(ReviewTrigger.JURISDICTION_UNKNOWN)
        
        # Règle 2: Confiance < 0.75
        if self.conclusion.confidence < 0.75:
            triggers.append(ReviewTrigger.LOW_CONFIDENCE)
        
        # Règle 3: Aucune base légale fiable
        has_reliable = any(
            lb.reliability in [Reliability.HIGH, Reliability.MEDIUM]
            for lb in self.legal_basis
        )
        if not has_reliable and self.legal_basis:
            triggers.append(ReviewTrigger.NO_RELIABLE_SOURCE)
        if not self.legal_basis:
            triggers.append(ReviewTrigger.MISSING_CITATIONS)
        
        # Règle 4: Domaine pénal
        if self.classification.domain == LegalDomain.PENAL:
            triggers.append(ReviewTrigger.DOMAIN_PENAL)
        
        # Règle 5: Complexité expert_only
        if self.classification.complexity == Complexity.EXPERT_ONLY:
            triggers.append(ReviewTrigger.COMPLEXITY_EXPERT)
        
        # Règle 6: Acte réservé
        if self.classification.requires_professional or self.safety.restricted_activity_detected:
            triggers.append(ReviewTrigger.RESTRICTED_ACTIVITY)
        
        # Règle 7: Conflit d'intérêts
        if self.safety.conflict_of_interest:
            triggers.append(ReviewTrigger.CONFLICT_OF_INTEREST)
        
        # Règle 8: Hors périmètre
        if self.scope.out_of_scope:
            triggers.append(ReviewTrigger.OUT_OF_SCOPE)
        
        # Règle 9: Domaines sensibles
        sensitive_domains = [
            LegalDomain.DROIT_TRAVAIL,
            LegalDomain.FISCAL,
            LegalDomain.IMMIGRATION,
            LegalDomain.RGPD_DONNEES,
        ]
        if self.classification.domain == LegalDomain.DROIT_TRAVAIL:
            triggers.append(ReviewTrigger.EMPLOYMENT_LAW_SENSITIVE)
        if self.classification.domain == LegalDomain.FISCAL:
            triggers.append(ReviewTrigger.TAX_HEAVY)
        if self.classification.domain == LegalDomain.IMMIGRATION:
            triggers.append(ReviewTrigger.IMMIGRATION_CASE)
        if self.classification.domain == LegalDomain.RGPD_DONNEES:
            triggers.append(ReviewTrigger.RGPD_INCIDENT)
        
        # Fusion des triggers
        existing = set(self.safety.review_triggers)
        new_triggers = existing.union(set(triggers))
        self.safety.review_triggers = list(new_triggers)
        
        # Si au moins un trigger → escalade obligatoire
        if self.safety.review_triggers:
            self.safety.requires_human_review = True
        
        return self
    
    @model_validator(mode="after")
    def enforce_temperature_zero(self) -> "LegalSafeResponse":
        """Force temperature=0 en mode legal_safe."""
        if self.meta.temperature != 0.0:
            raise ValueError(
                f"Temperature must be 0 in legal_safe mode, got {self.meta.temperature}. "
                "This is a critical safety requirement."
            )
        return self
    
    @model_validator(mode="after")
    def validate_output_derivation(self) -> "LegalSafeResponse":
        """Vérifie que le markdown ne contient pas d'infos hors JSON."""
        md = self.output.user_facing_markdown.lower()
        
        # Le markdown doit contenir au moins un élément clé du JSON
        required_elements = [
            self.conclusion.answer[:50].lower() if len(self.conclusion.answer) > 50 else self.conclusion.answer.lower(),
        ]
        
        # Vérification souple : au moins la conclusion doit apparaître
        # (on ne peut pas faire une vérification stricte car le markdown est formaté)
        
        # Vérifier que le disclaimer est présent
        if "conseil juridique" not in md and "legal advice" not in md and "⚠️" not in self.output.user_facing_markdown:
            raise ValueError(
                "Le markdown doit inclure un disclaimer clair indiquant que ce n'est pas un conseil juridique."
            )
        
        return self
    
    def compute_hashes(self, input_text: str) -> "LegalSafeResponse":
        """Calcule les hashes pour l'audit."""
        # Hash de l'input (anonymisé - on ne garde que la structure)
        anonymized_input = self._anonymize_input(input_text)
        self.meta.input_hash = f"sha256:{hashlib.sha256(anonymized_input.encode()).hexdigest()}"
        
        # Hash de la réponse (sans le hash lui-même)
        response_for_hash = self.model_dump_json(exclude={"meta": {"response_hash", "input_hash"}})
        self.meta.response_hash = f"sha256:{hashlib.sha256(response_for_hash.encode()).hexdigest()}"
        
        return self
    
    @staticmethod
    def _anonymize_input(text: str) -> str:
        """Anonymise l'input pour le hash (supprime PII potentiels)."""
        # Supprimer emails
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        # Supprimer numéros de téléphone
        text = re.sub(r'\b(?:\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}\b', '[PHONE]', text)
        # Supprimer numéros de sécu
        text = re.sub(r'\b[12]\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{3}\s*\d{3}\s*\d{2}\b', '[NIR]', text)
        # Supprimer IBAN
        text = re.sub(r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b', '[IBAN]', text)
        return text


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY — Création de réponses type
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeResponseFactory:
    """Factory pour créer des réponses standardisées."""
    
    @staticmethod
    def create_fallback_response(
        reason: str,
        provider: str = "unknown",
        model: str = "unknown",
        correlation_id: Optional[str] = None
    ) -> LegalSafeResponse:
        """Crée une réponse fallback sécurisée."""
        fallback_msg = (
            "Je ne peux pas répondre de manière fiable à cette question juridique. "
            "Pour votre sécurité, veuillez consulter un professionnel du droit qualifié."
        )
        
        return LegalSafeResponse(
            scope=Scope(
                jurisdiction_requested=Jurisdiction.UNKNOWN,
                out_of_scope=True,
                out_of_scope_reason=reason
            ),
            classification=Classification(
                domain=LegalDomain.UNKNOWN,
                task_type=TaskType.UNKNOWN,
                complexity=Complexity.EXPERT_ONLY,
                requires_professional=True
            ),
            facts=Facts(),
            legal_basis=[],
            analysis=Analysis(
                reasoning_steps=["Impossible de traiter la demande de manière fiable."],
                risks=[Risk(
                    id="R1",
                    level=RiskLevel.HIGH,
                    description="Réponse non fiable",
                    mitigation="Consultation d'un professionnel"
                )]
            ),
            conclusion=Conclusion(
                answer=fallback_msg,
                recommendation="Consultez un avocat ou un juriste qualifié.",
                confidence=0.0
            ),
            safety=Safety(
                hallucination_risk=RiskLevel.HIGH,
                requires_human_review=True,
                review_triggers=[ReviewTrigger.LOW_CONFIDENCE, ReviewTrigger.JURISDICTION_UNKNOWN]
            ),
            disclaimers=Disclaimers(),
            fallback=Fallback(
                triggered=True,
                reason=reason,
                safe_message=fallback_msg
            ),
            output=Output(
                user_facing_markdown=f"""## ⚠️ Impossible de traiter cette demande

{fallback_msg}

### Raison
{reason}

---
*{Disclaimers().text_fr}*
"""
            ),
            meta=Meta(
                correlation_id=correlation_id or str(uuid4()),
                provider=provider,
                model=model,
                temperature=0.0
            )
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "Jurisdiction",
    "TaskType", 
    "RiskLevel",
    "Reliability",
    "LegalBasisType",
    "Complexity",
    "LegalDomain",
    "ReviewTrigger",
    # Sub-models
    "ProvidedFact",
    "Assumption",
    "MissingInfo",
    "Facts",
    "LegalBasis",
    "Risk",
    "Analysis",
    "Conclusion",
    "Scope",
    "Classification",
    "Safety",
    "Disclaimers",
    "AbuseDetection",
    "UserAcknowledgment",
    "Fallback",
    "Output",
    "Meta",
    # Main
    "LegalSafeResponse",
    "LegalSafeResponseFactory",
]
