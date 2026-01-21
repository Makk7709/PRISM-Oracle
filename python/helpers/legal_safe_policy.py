"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — ESCALATION POLICY                      ║
║                                                                              ║
║  Fonctions pures et testables pour l'évaluation des règles d'escalade.      ║
║  Aucun effet de bord, aucune dépendance externe.                            ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .legal_safe_schema import (
    Complexity,
    Jurisdiction,
    LegalBasis,
    LegalDomain,
    LegalSafeResponse,
    Reliability,
    ReviewTrigger,
    RiskLevel,
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES — Résultats d'évaluation
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PolicyEvaluation:
    """Résultat d'évaluation de la policy."""
    requires_human_review: bool
    triggers: tuple[ReviewTrigger, ...]
    risk_level: RiskLevel
    explanation: str
    blocking: bool = False  # Si True, la réponse ne doit pas être envoyée du tout


@dataclass(frozen=True)
class InputAnalysis:
    """Analyse de l'input utilisateur."""
    contains_certainty_request: bool
    detected_domain: Optional[LegalDomain]
    detected_jurisdiction: Optional[Jurisdiction]
    is_restricted_activity: bool
    restriction_type: Optional[str]
    potential_parties: list[str]
    sensitive_keywords: list[str]


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES — Seuils et patterns
# ═══════════════════════════════════════════════════════════════════════════════

# Seuil de confiance minimum pour éviter l'escalade
CONFIDENCE_THRESHOLD = 0.75

# Seuil de queries similaires par 24h avant alerte abus
ABUSE_QUERY_THRESHOLD = 10

# Patterns de demande de certitude (déclenchent escalade)
CERTAINTY_PATTERNS = [
    r"\bcertifie[rz]?\b",
    r"\bgaranti[rse]?\b",
    r"\bvalide[rz]?\s+légalement\b",
    r"\bassure[rz]?\s+(?:moi|nous)\s+que\b",
    r"\bconfirme[rz]?\s+(?:que|légalement)\b",
    r"\bdonne[rz]?\s+(?:moi|nous)\s+une?\s+certitude\b",
    r"\best[- ]ce\s+(?:légal|valide|conforme)\s*\?\s*$",
    r"\bpeux[- ]tu\s+(?:certifier|garantir|valider)\b",
]

# Patterns d'actes réservés aux avocats/notaires
RESTRICTED_ACTIVITY_PATTERNS = {
    "representation": [
        r"\breprésente[rz]?\s+(?:moi|nous|mon\s+client)\b",
        r"\bagir\s+en\s+(?:mon|notre)\s+nom\b",
        r"\bplaider\s+(?:pour|devant)\b",
        r"\ben\s+mon\s+nom\b",
    ],
    "drafting_legal_act": [
        r"\brédige[rz]?(?:-moi)?\s+(?:un|une|le|la|moi\s+un)?\s*(?:contrat|acte|statuts|testament)\b",
        r"\bprépare[rz]?\s+(?:les|un|une)\s+(?:actes?|documents?\s+juridiques?)\b",
        r"\bétabli[rsz]?\s+(?:un|une)\s+(?:acte\s+authentique|procuration)\b",
        r"\brédige-moi\b",
    ],
    "court_filing": [
        r"\bdépose[rz]?\s+(?:une|la)\s+(?:plainte|assignation|requête)\b",
        r"\bsaisi[rsz]?\s+(?:le|un)\s+(?:tribunal|juge|conseil)\b",
    ],
}

# Mots-clés sensibles par domaine
DOMAIN_KEYWORDS = {
    LegalDomain.DROIT_TRAVAIL: [
        "licenciement", "licencier", "rupture conventionnelle", "prud'hommes", "harcèlement",
        "discrimination", "contrat de travail", "démission", "faute grave",
        "indemnités", "préavis", "clause de non-concurrence", "heures supplémentaires",
        "employeur", "salarié", "embauche", "embaucher", "cdi", "cdd",
    ],
    LegalDomain.PENAL: [
        "pénal", "délit", "crime", "infraction", "prison", "amende pénale",
        "garde à vue", "mise en examen", "casier judiciaire", "plainte pénale",
        "vol", "escroquerie", "abus de confiance", "violence", "menace",
    ],
    LegalDomain.FISCAL: [
        "impôts", "impot", "fiscal", "TVA", "IS", "IR", "redressement", "contrôle fiscal",
        "optimisation fiscale", "évasion", "fraude fiscale", "déclaration",
        "payer mes impôts", "taxes",
    ],
    LegalDomain.RGPD_DONNEES: [
        "RGPD", "données personnelles", "CNIL", "DPO", "violation de données",
        "consentement", "droit à l'oubli", "portabilité", "registre de traitement",
        "données", "protection des données", "data", "gdpr",
    ],
    LegalDomain.IMMIGRATION: [
        "titre de séjour", "visa", "naturalisation", "expulsion", "OQTF",
        "regroupement familial", "asile", "réfugié", "carte de résident",
    ],
    LegalDomain.CONTRATS: [
        "contrat", "clause", "résiliation", "inexécution", "pénalités",
        "conditions générales", "force majeure", "vice du consentement",
    ],
}

# Juridictions supportées
SUPPORTED_JURISDICTIONS = {Jurisdiction.FR, Jurisdiction.EU}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS PURES — Analyse d'input
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_input(text: str) -> InputAnalysis:
    """
    Analyse l'input utilisateur pour détecter les éléments sensibles.
    
    Fonction pure : aucun effet de bord.
    
    Args:
        text: Texte de la question utilisateur
        
    Returns:
        InputAnalysis avec tous les éléments détectés
    """
    text_lower = text.lower()
    
    # Détection de demande de certitude
    contains_certainty = any(
        re.search(pattern, text_lower)
        for pattern in CERTAINTY_PATTERNS
    )
    
    # Détection de domaine
    detected_domain = _detect_domain(text_lower)
    
    # Détection de juridiction
    detected_jurisdiction = _detect_jurisdiction(text_lower)
    
    # Détection d'acte réservé
    is_restricted, restriction_type = _detect_restricted_activity(text_lower)
    
    # Détection de parties (pour conflit d'intérêts)
    parties = _detect_parties(text_lower)
    
    # Extraction des mots-clés sensibles
    sensitive_kw = _extract_sensitive_keywords(text_lower)
    
    return InputAnalysis(
        contains_certainty_request=contains_certainty,
        detected_domain=detected_domain,
        detected_jurisdiction=detected_jurisdiction,
        is_restricted_activity=is_restricted,
        restriction_type=restriction_type,
        potential_parties=parties,
        sensitive_keywords=sensitive_kw,
    )


def _detect_domain(text: str) -> Optional[LegalDomain]:
    """Détecte le domaine juridique probable."""
    scores: dict[LegalDomain, int] = {}
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[domain] = score
    
    if not scores:
        return None
    
    return max(scores, key=lambda d: scores[d])


def _detect_jurisdiction(text: str) -> Optional[Jurisdiction]:
    """Détecte la juridiction probable."""
    fr_markers = ["france", "français", "code du travail", "code civil", "cnil", "prud'hommes"]
    eu_markers = ["europe", "européen", "rgpd", "directive", "règlement ue"]
    
    has_fr = any(m in text for m in fr_markers)
    has_eu = any(m in text for m in eu_markers)
    
    if has_fr and not has_eu:
        return Jurisdiction.FR
    if has_eu:
        return Jurisdiction.EU
    return None


def _detect_restricted_activity(text: str) -> tuple[bool, Optional[str]]:
    """Détecte si la demande concerne un acte réservé."""
    for activity_type, patterns in RESTRICTED_ACTIVITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return True, activity_type
    return False, None


def _detect_parties(text: str) -> list[str]:
    """Détecte les parties potentielles mentionnées."""
    parties = []
    
    party_patterns = [
        (r"\bemployeur\b", "employeur"),
        (r"\bsalarié\b", "salarié"),
        (r"\blocataire\b", "locataire"),
        (r"\bpropriétaire\b", "propriétaire"),
        (r"\bacheteur\b", "acheteur"),
        (r"\bvendeur\b", "vendeur"),
        (r"\bcréancier\b", "créancier"),
        (r"\bdébiteur\b", "débiteur"),
        (r"\bplaignant\b", "plaignant"),
        (r"\bprévenu\b", "prévenu"),
    ]
    
    for pattern, party in party_patterns:
        if re.search(pattern, text):
            parties.append(party)
    
    return parties


def _extract_sensitive_keywords(text: str) -> list[str]:
    """Extrait les mots-clés sensibles présents."""
    sensitive = []
    
    all_keywords = []
    for keywords in DOMAIN_KEYWORDS.values():
        all_keywords.extend(keywords)
    
    for kw in all_keywords:
        if kw in text:
            sensitive.append(kw)
    
    return sensitive


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS PURES — Évaluation de réponse
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_response(response: LegalSafeResponse) -> PolicyEvaluation:
    """
    Évalue une réponse selon les règles de la policy.
    
    Fonction pure : aucun effet de bord.
    
    Args:
        response: Réponse LegalSafeResponse à évaluer
        
    Returns:
        PolicyEvaluation avec les résultats
    """
    triggers: list[ReviewTrigger] = []
    explanations: list[str] = []
    blocking = False
    
    # Règle 1: Confiance trop basse
    if response.conclusion.confidence < CONFIDENCE_THRESHOLD:
        triggers.append(ReviewTrigger.LOW_CONFIDENCE)
        explanations.append(
            f"Confiance ({response.conclusion.confidence:.2f}) < seuil ({CONFIDENCE_THRESHOLD})"
        )
    
    # Règle 2: Juridiction inconnue
    if response.scope.jurisdiction_requested == Jurisdiction.UNKNOWN:
        triggers.append(ReviewTrigger.JURISDICTION_UNKNOWN)
        explanations.append("Juridiction non identifiée")
    
    # Règle 3: Juridiction non supportée
    if response.scope.out_of_scope:
        triggers.append(ReviewTrigger.OUT_OF_SCOPE)
        explanations.append(f"Hors périmètre: {response.scope.out_of_scope_reason}")
        blocking = True  # Hors périmètre = blocage total
    
    # Règle 4: Pas de base légale fiable
    if not _has_reliable_legal_basis(response.legal_basis):
        triggers.append(ReviewTrigger.NO_RELIABLE_SOURCE)
        explanations.append("Aucune source juridique fiable")
    
    # Règle 5: Pas de citation du tout
    if not response.legal_basis:
        triggers.append(ReviewTrigger.MISSING_CITATIONS)
        explanations.append("Aucune citation juridique")
    
    # Règle 6: Domaine pénal
    if response.classification.domain == LegalDomain.PENAL:
        triggers.append(ReviewTrigger.DOMAIN_PENAL)
        explanations.append("Domaine pénal = escalade obligatoire")
    
    # Règle 7: Complexité expert
    if response.classification.complexity == Complexity.EXPERT_ONLY:
        triggers.append(ReviewTrigger.COMPLEXITY_EXPERT)
        explanations.append("Complexité nécessitant un expert")
    
    # Règle 8: Acte réservé
    if response.classification.requires_professional:
        triggers.append(ReviewTrigger.RESTRICTED_ACTIVITY)
        explanations.append("Acte réservé aux professionnels du droit")
        blocking = True  # Acte réservé = blocage total
    
    # Règle 9: Conflit d'intérêts
    if response.safety.conflict_of_interest:
        triggers.append(ReviewTrigger.CONFLICT_OF_INTEREST)
        explanations.append(f"Conflit d'intérêts potentiel: {response.safety.parties_involved}")
    
    # Règle 10: Domaines sensibles
    sensitive_domain_triggers = _check_sensitive_domains(response.classification.domain)
    triggers.extend(sensitive_domain_triggers)
    
    # Règle 11: Risque d'hallucination élevé
    if response.safety.hallucination_risk == RiskLevel.HIGH:
        triggers.append(ReviewTrigger.HIGH_IMPACT)
        explanations.append("Risque d'hallucination élevé")
    
    # Calcul du niveau de risque global
    risk_level = _compute_risk_level(triggers)
    
    # Déterminer si escalade requise
    requires_review = len(triggers) > 0
    
    return PolicyEvaluation(
        requires_human_review=requires_review,
        triggers=tuple(triggers),
        risk_level=risk_level,
        explanation="; ".join(explanations) if explanations else "Aucun problème détecté",
        blocking=blocking,
    )


def _has_reliable_legal_basis(legal_basis: list[LegalBasis]) -> bool:
    """Vérifie s'il y a au moins une base légale fiable."""
    return any(
        lb.reliability in [Reliability.HIGH, Reliability.MEDIUM]
        for lb in legal_basis
    )


def _check_sensitive_domains(domain: LegalDomain) -> list[ReviewTrigger]:
    """Vérifie les domaines sensibles."""
    mapping = {
        LegalDomain.DROIT_TRAVAIL: ReviewTrigger.EMPLOYMENT_LAW_SENSITIVE,
        LegalDomain.FISCAL: ReviewTrigger.TAX_HEAVY,
        LegalDomain.IMMIGRATION: ReviewTrigger.IMMIGRATION_CASE,
        LegalDomain.RGPD_DONNEES: ReviewTrigger.RGPD_INCIDENT,
    }
    
    if domain in mapping:
        return [mapping[domain]]
    return []


def _compute_risk_level(triggers: list[ReviewTrigger]) -> RiskLevel:
    """Calcule le niveau de risque global."""
    high_risk_triggers = {
        ReviewTrigger.DOMAIN_PENAL,
        ReviewTrigger.RESTRICTED_ACTIVITY,
        ReviewTrigger.CONFLICT_OF_INTEREST,
        ReviewTrigger.OUT_OF_SCOPE,
        ReviewTrigger.CRIMINAL_LIABILITY,
    }
    
    medium_risk_triggers = {
        ReviewTrigger.LOW_CONFIDENCE,
        ReviewTrigger.NO_RELIABLE_SOURCE,
        ReviewTrigger.MISSING_CITATIONS,
        ReviewTrigger.COMPLEXITY_EXPERT,
        ReviewTrigger.EMPLOYMENT_LAW_SENSITIVE,
        ReviewTrigger.TAX_HEAVY,
    }
    
    if any(t in high_risk_triggers for t in triggers):
        return RiskLevel.HIGH
    if any(t in medium_risk_triggers for t in triggers):
        return RiskLevel.MEDIUM
    if triggers:
        return RiskLevel.LOW
    return RiskLevel.LOW


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS PURES — Validation stricte
# ═══════════════════════════════════════════════════════════════════════════════

def validate_citations(legal_basis: list[LegalBasis]) -> tuple[bool, list[str]]:
    """
    Valide que les citations ne sont pas inventées.
    
    Args:
        legal_basis: Liste des bases légales
        
    Returns:
        Tuple (is_valid, list_of_issues)
    """
    issues: list[str] = []
    
    # Patterns de citations valides (non exhaustif mais indicatif)
    valid_patterns = [
        r"Code\s+(?:du\s+travail|civil|pénal|commerce|consommation)",
        r"[Aa]rt(?:icle)?\.?\s*[LRDA]?\d+",
        r"(?:RGPD|GDPR)\s+art",
        r"[Dd]irective\s+\d{4}/\d+",
        r"[Rr]èglement\s+(?:UE|CE)\s+\d{4}/\d+",
        r"Cass\.\s+(?:soc|civ|com|crim)",
        r"CE,?\s+\d",
        r"CEDH",
        r"CJUE",
        r"UNKNOWN",  # Valide car explicitement incertain
    ]
    
    for lb in legal_basis:
        citation = lb.citation
        
        # Vérifier que la citation correspond à un pattern connu ou est UNKNOWN
        matches_pattern = any(re.search(p, citation) for p in valid_patterns)
        
        if not matches_pattern and lb.reliability != Reliability.UNKNOWN:
            issues.append(f"Citation suspecte: '{citation}' - format non reconnu")
        
        # Vérifier cohérence citation/reliability
        if "UNKNOWN" in citation.upper() and lb.reliability != Reliability.UNKNOWN:
            issues.append(f"Citation '{citation}' marquée UNKNOWN mais reliability={lb.reliability}")
    
    return len(issues) == 0, issues


def check_abuse_pattern(
    similar_queries_24h: int,
    escalation_rate: float,
) -> tuple[bool, Optional[str]]:
    """
    Détecte les patterns d'abus.
    
    Args:
        similar_queries_24h: Nombre de queries similaires en 24h
        escalation_rate: Taux d'escalade sur les dernières queries
        
    Returns:
        Tuple (is_abuse, abuse_type)
    """
    if similar_queries_24h > ABUSE_QUERY_THRESHOLD:
        return True, "bulk_legal_advice"
    
    if escalation_rate > 0.8 and similar_queries_24h > 5:
        return True, "systematic_probing"
    
    return False, None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Data classes
    "PolicyEvaluation",
    "InputAnalysis",
    # Constants
    "CONFIDENCE_THRESHOLD",
    "ABUSE_QUERY_THRESHOLD",
    "CERTAINTY_PATTERNS",
    "RESTRICTED_ACTIVITY_PATTERNS",
    "DOMAIN_KEYWORDS",
    "SUPPORTED_JURISDICTIONS",
    # Functions
    "analyze_input",
    "evaluate_response",
    "validate_citations",
    "check_abuse_pattern",
]
