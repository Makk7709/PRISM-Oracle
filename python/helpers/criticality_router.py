"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CRITICALITY ROUTER — Zero Hallucination Mode              ║
║                                                                              ║
║  Point de contrôle UNIQUE pour décider si consensus PRISM est requis.        ║
║                                                                              ║
║  Règles:                                                                     ║
║  1. Agent legal_safe ou researcher → TOUJOURS consensus                      ║
║  2. Domaine LEGAL/MEDICAL/SCIENTIFIC détecté → TOUJOURS consensus            ║
║  3. Action critique (publish, recommend, diagnose) → TOUJOURS consensus      ║
║  4. Mode STRICT_EVIDENCE pour domaines critiques (fail-closed)               ║
║                                                                              ║
║  AUCUNE EXCEPTION en production.                                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("criticality_router")


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAINS
# ═══════════════════════════════════════════════════════════════════════════════

class CriticalDomain(str, Enum):
    """Domaines critiques nécessitant consensus."""
    LEGAL = "legal"
    MEDICAL = "medical"
    SCIENTIFIC = "scientific"
    FINANCE_HIGH_RISK = "finance_high_risk"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    DEFAULT = "default"


class DecisionTypeForDomain(str, Enum):
    """Types de décision PRISM par domaine."""
    LEGAL_DECISION = "legal_decision"
    MEDICAL_DECISION = "medical_decision"
    SCIENTIFIC_VALIDATION = "scientific_validation"
    FINANCIAL_DECISION = "financial_decision"
    SECURITY_DECISION = "security_decision"
    RESEARCH_VALIDATION = "research_validation"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT PROFILES REQUIRING CONSENSUS
# ═══════════════════════════════════════════════════════════════════════════════

# Ces profils OBLIGENT le consensus - AUCUNE EXCEPTION
CONSENSUS_REQUIRED_PROFILES: Set[str] = {
    "legal_safe",
    "researcher",
    "medical",  # Agent médical spécialisé - PRISM obligatoire
    # Ajouter ici les futurs profils critiques
    # "scientific",
}

# Profils qui peuvent bypasser le consensus (dev/test uniquement)
DEBUG_BYPASS_PROFILES: Set[str] = {
    "developer",
    "hacker",  # Pour tests uniquement
}


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORD PATTERNS (FR/EN)
# ═══════════════════════════════════════════════════════════════════════════════

DOMAIN_PATTERNS: Dict[CriticalDomain, List[str]] = {
    CriticalDomain.LEGAL: [
        # English
        r"\b(legal|law|lawsuit|litigation|attorney|lawyer|court|judge|verdict)\b",
        r"\b(contract|liability|compliance|regulation|statute|ordinance)\b",
        r"\b(copyright|trademark|patent|intellectual property|ip rights)\b",
        r"\b(employment law|labor law|termination|wrongful dismissal)\b",
        r"\b(gdpr|rgpd|privacy law|data protection)\b",
        # French - Expanded for realistic coverage
        r"\b(juridique|loi|procès|litige|avocat|tribunal|juge|verdict)\b",
        r"\b(contrat|responsabilité|conformité|réglementation|statut)\b",
        r"\b(droit d'auteur|marque|brevet|propriété intellectuelle)\b",
        r"\b(droit du travail|licenciement|rupture conventionnelle)\b",
        r"\b(code civil|code pénal|code du travail|code de commerce)\b",
        # French additions - Pièges réalistes
        r"\b(clause|clauses)\b",
        r"\b(prud'?hommes?|prud'?homme)\b",
        r"\b(CGV|CGU|conditions générales)\b",
        r"\b(RGPD|protection des données)\b",
        r"\b(mise en demeure|injonction|sommation)\b",
        r"\b(jurisprudence|arrêt|décision de justice)\b",
        r"\b(recours|appel|cassation)\b",
        r"\b(préjudice|dommages et intérêts|indemnisation)\b",
        r"\b(nullité|résiliation|résolution)\b",
        r"\b(servitude|usufruit|hypothèque)\b",
    ],
    
    CriticalDomain.MEDICAL: [
        # English
        r"\b(medical|diagnosis|treatment|prescription|medication|drug)\b",
        r"\b(symptoms?|disease|illness|condition|disorder|syndrome)\b",
        r"\b(doctor|physician|nurse|healthcare|hospital|clinic)\b",
        r"\b(dosage|side effects?|contraindication|interaction)\b",
        r"\b(surgery|procedure|therapy|intervention)\b",
        # French
        r"\b(médical|diagnostic|traitement|prescription|médicament)\b",
        r"\b(symptômes?|maladie|pathologie|trouble|syndrome)\b",
        r"\b(médecin|docteur|infirmier|santé|hôpital|clinique)\b",
        r"\b(posologie|effets secondaires|contre.?indications?)\b",
        r"\b(chirurgie|intervention|thérapie)\b",
        # French additions - Pièges réalistes
        r"\b(ordonnance)\b",
        r"\b(bilan sanguin|analyse|prise de sang)\b",
        r"\b(diagnostic différentiel)\b",
        r"\b(interactions? médicamenteuses?)\b",
        r"\b(AMM|autorisation de mise sur le marché)\b",
        r"\b(EI|effet indésirable|événement indésirable)\b",
        r"\b(pronostic|évolution|chronicité)\b",
        r"\b(antécédents?|ATCD|historique médical)\b",
        r"\b(BMI|IMC|indice de masse corporelle)\b",
        r"\b(glycémie|tension artérielle|TA|PA)\b",
        r"\b(IRM|scanner|radiographie|échographie)\b",
    ],
    
    CriticalDomain.SCIENTIFIC: [
        # English
        r"\b(scientific|research|study|experiment|hypothesis)\b",
        r"\b(peer.?review|published|journal|citation)\b",
        r"\b(statistical|significance|p.?value|confidence interval)\b",
        r"\b(clinical trial|meta.?analysis|systematic review)\b",
        # French
        r"\b(scientifique|recherche|étude|expérience|hypothèse)\b",
        r"\b(revue par les pairs|publié|journal|citation)\b",
        r"\b(statistique|significatif|intervalle de confiance)\b",
        r"\b(essai clinique|méta.?analyse|revue systématique)\b",
        # French additions - Pièges réalistes
        r"\b(méthodologie|protocole expérimental)\b",
        r"\b(p-?value|valeur-?p|seuil de significativité)\b",
        r"\b(reproductibilité|réplicabilité)\b",
        r"\b(biais|facteur confondant)\b",
        r"\b(preprint|prépublication)\b",
        r"\b(échantillon|cohorte|groupe témoin|groupe contrôle)\b",
        r"\b(randomisé|double aveugle|placebo)\b",
        r"\b(corrélation|causalité)\b",
        r"\b(odds ratio|risque relatif|RR|OR)\b",
        r"\b(IC95|intervalle de confiance à 95)\b",
    ],
    
    CriticalDomain.FINANCE_HIGH_RISK: [
        # High-risk financial actions
        r"\b(invest|investment advice|portfolio|stocks?|bonds?|securities)\b",
        r"\b(trading|forex|cryptocurrency|bitcoin|ethereum)\b",
        r"\b(loan|mortgage|debt|credit|bankruptcy)\b",
        r"\b(tax advice|fiscal|impôts|déclaration fiscale)\b",
        r"\b(retirement|pension|401k|ira)\b",
        # French
        r"\b(investir|conseil en investissement|portefeuille|actions?|obligations?)\b",
        r"\b(trading|cryptomonnaie|bitcoin)\b",
        r"\b(prêt|hypothèque|dette|crédit|faillite)\b",
        r"\b(retraite|pension|épargne)\b",
    ],
    
    CriticalDomain.SECURITY: [
        r"\b(security|vulnerability|exploit|breach|hack|attack)\b",
        r"\b(password|credential|authentication|authorization)\b",
        r"\b(encryption|decrypt|cipher|key management)\b",
        r"\b(sécurité|vulnérabilité|faille|attaque|piratage)\b",
    ],
    
    CriticalDomain.COMPLIANCE: [
        r"\b(compliance|audit|certification|standard|iso|soc2)\b",
        r"\b(hipaa|pci.?dss|sox|ferpa)\b",
        r"\b(conformité|audit|certification|norme)\b",
    ],
}

# Actions critiques qui déclenchent le consensus même sans domaine détecté
CRITICAL_ACTION_PATTERNS: List[str] = [
    # Publication / Décision finale
    r"\b(publish|publier|release|diffuser)\b",
    r"\b(recommend|recommander|advise|conseiller)\b",
    r"\b(conclude|conclure|final.?answer|réponse définitive)\b",
    r"\b(approve|approuver|validate|valider)\b",
    r"\b(certify|certifier|guarantee|garantir)\b",
    
    # Actions médicales
    r"\b(diagnose|diagnostiquer|prescribe|prescrire)\b",
    r"\b(treat|traiter|cure|guérir)\b",
    
    # Actions légales
    r"\b(contract|contracter|sign|signer)\b",
    r"\b(sue|poursuivre|file.?complaint|porter plainte)\b",
    
    # Actions financières à risque
    r"\b(buy|acheter|sell|vendre|trade|échanger)\b",
    r"\b(transfer|transférer|wire|virement)\b",
]


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CriticalityAssessment:
    """Résultat de l'évaluation de criticité."""
    
    # Décision principale
    requires_consensus: bool
    strict_evidence_mode: bool
    
    # Détails
    domain: CriticalDomain
    decision_type: DecisionTypeForDomain
    confidence: float  # 0.0-1.0
    
    # Raisons
    reasons: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    
    # Contexte
    agent_profile: str = ""
    query_hash: str = ""
    
    # Flags
    can_bypass: bool = False  # True uniquement en dev/test
    bypass_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise pour audit."""
        return {
            "requires_consensus": self.requires_consensus,
            "strict_evidence_mode": self.strict_evidence_mode,
            "domain": self.domain.value,
            "decision_type": self.decision_type.value,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "matched_patterns": self.matched_patterns[:5],  # Limiter pour logs
            "agent_profile": self.agent_profile,
            "can_bypass": self.can_bypass,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICALITY ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class CriticalityRouter:
    """
    Router de criticité — Point de contrôle UNIQUE pour le consensus.
    
    Utilisation:
        router = CriticalityRouter()
        assessment = router.assess(query, agent_profile)
        
        if assessment.requires_consensus:
            # Activer consensus PRISM
            # Activer STRICT_EVIDENCE_MODE si assessment.strict_evidence_mode
    """
    
    def __init__(
        self,
        custom_patterns: Optional[Dict[CriticalDomain, List[str]]] = None,
        custom_action_patterns: Optional[List[str]] = None,
        is_production: bool = None,
    ):
        """
        Initialise le router.
        
        Args:
            custom_patterns: Patterns personnalisés par domaine
            custom_action_patterns: Patterns d'action critique personnalisés
            is_production: Mode production (auto-détecté si None)
        """
        # Patterns
        self.domain_patterns = {**DOMAIN_PATTERNS}
        if custom_patterns:
            for domain, patterns in custom_patterns.items():
                self.domain_patterns.setdefault(domain, []).extend(patterns)
        
        self.action_patterns = list(CRITICAL_ACTION_PATTERNS)
        if custom_action_patterns:
            self.action_patterns.extend(custom_action_patterns)
        
        # Compiler les regex pour performance
        self._compiled_domain_patterns: Dict[CriticalDomain, List[re.Pattern]] = {}
        for domain, patterns in self.domain_patterns.items():
            self._compiled_domain_patterns[domain] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_action_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.action_patterns
        ]
        
        # Mode
        if is_production is None:
            env = os.environ.get("EVIDENCE_ENV", "production").lower()
            self._is_production = env == "production"
        else:
            self._is_production = is_production
        
        logger.info(f"CriticalityRouter initialized (production={self._is_production})")
    
    # ─────────────────────────────────────────────────────────────────────────
    # MAIN ASSESSMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    def assess(
        self,
        query: str,
        agent_profile: str = "",
        task_metadata: Optional[Dict[str, Any]] = None,
        force_consensus: Optional[bool] = None,
    ) -> CriticalityAssessment:
        """
        Évalue si une requête nécessite consensus.
        
        Args:
            query: Texte de la requête
            agent_profile: Profil de l'agent (legal_safe, researcher, etc.)
            task_metadata: Métadonnées additionnelles
            force_consensus: Forcer consensus (True) ou bypass (False si debug)
            
        Returns:
            CriticalityAssessment avec la décision
        """
        task_metadata = task_metadata or {}
        reasons = []
        matched_patterns = []
        
        # ─────────────────────────────────────────────────────────────────────
        # RÈGLE 1: Profil agent critique → TOUJOURS consensus
        # ─────────────────────────────────────────────────────────────────────
        
        profile_lower = agent_profile.lower().strip()
        if profile_lower in CONSENSUS_REQUIRED_PROFILES:
            reasons.append(f"Agent profile '{profile_lower}' requires mandatory consensus")
            
            # Déterminer le domaine basé sur le profil
            if "legal" in profile_lower:
                domain = CriticalDomain.LEGAL
                decision_type = DecisionTypeForDomain.LEGAL_DECISION
            elif "research" in profile_lower:
                domain = CriticalDomain.SCIENTIFIC
                decision_type = DecisionTypeForDomain.RESEARCH_VALIDATION
            else:
                domain = CriticalDomain.DEFAULT
                decision_type = DecisionTypeForDomain.CRITICAL
            
            return CriticalityAssessment(
                requires_consensus=True,
                strict_evidence_mode=True,
                domain=domain,
                decision_type=decision_type,
                confidence=1.0,
                reasons=reasons,
                matched_patterns=[],
                agent_profile=agent_profile,
                can_bypass=False,  # JAMAIS de bypass pour ces profils
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # RÈGLE 2: Détection de domaine critique
        # ─────────────────────────────────────────────────────────────────────
        
        detected_domain, domain_confidence, domain_matches = self._detect_domain(query)
        matched_patterns.extend(domain_matches)
        
        if detected_domain != CriticalDomain.DEFAULT:
            reasons.append(f"Critical domain detected: {detected_domain.value}")
        
        # ─────────────────────────────────────────────────────────────────────
        # RÈGLE 3: Détection d'action critique
        # ─────────────────────────────────────────────────────────────────────
        
        has_critical_action, action_matches = self._detect_critical_action(query)
        matched_patterns.extend(action_matches)
        
        if has_critical_action:
            reasons.append("Critical action pattern detected")
        
        # ─────────────────────────────────────────────────────────────────────
        # RÈGLE 4: Force consensus si demandé explicitement
        # ─────────────────────────────────────────────────────────────────────
        
        if force_consensus is True:
            reasons.append("Consensus forced by caller")
        
        # ─────────────────────────────────────────────────────────────────────
        # DÉCISION FINALE
        # ─────────────────────────────────────────────────────────────────────
        
        requires_consensus = (
            force_consensus is True or
            detected_domain != CriticalDomain.DEFAULT or
            has_critical_action
        )
        
        # Strict evidence mode pour domaines critiques
        strict_evidence = detected_domain in {
            CriticalDomain.LEGAL,
            CriticalDomain.MEDICAL,
            CriticalDomain.SCIENTIFIC,
        }
        
        # Decision type
        decision_type = self._get_decision_type(detected_domain, has_critical_action)
        
        # Calcul de confiance
        confidence = domain_confidence if detected_domain != CriticalDomain.DEFAULT else 0.5
        if has_critical_action:
            confidence = max(confidence, 0.7)
        
        # Bypass possible ?
        can_bypass = (
            not self._is_production and
            profile_lower in DEBUG_BYPASS_PROFILES and
            force_consensus is not True
        )
        
        if can_bypass and not requires_consensus:
            can_bypass = False  # Pas besoin de bypass si pas de consensus requis
        
        return CriticalityAssessment(
            requires_consensus=requires_consensus,
            strict_evidence_mode=strict_evidence,
            domain=detected_domain,
            decision_type=decision_type,
            confidence=confidence,
            reasons=reasons,
            matched_patterns=matched_patterns,
            agent_profile=agent_profile,
            can_bypass=can_bypass,
            bypass_reason="Debug profile in non-production" if can_bypass else None,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONVENIENCE METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    def should_require_consensus(
        self,
        query: str,
        agent_profile: str = "",
        action: str = "",
        require_consensus_flag: Optional[bool] = None,
    ) -> bool:
        """
        Vérifie simplement si consensus est requis.
        
        Returns:
            True si consensus requis
        """
        # Si flag explicite et en prod → respecter
        if require_consensus_flag is True:
            return True
        
        full_text = f"{query} {action}".strip()
        assessment = self.assess(full_text, agent_profile, force_consensus=require_consensus_flag)
        
        return assessment.requires_consensus
    
    def detect_domain(
        self,
        query: str,
        agent_profile: str = "",
        task_metadata: Optional[Dict[str, Any]] = None,
    ) -> CriticalDomain:
        """
        Détecte le domaine principal d'une requête.
        
        Returns:
            CriticalDomain détecté
        """
        assessment = self.assess(query, agent_profile, task_metadata)
        return assessment.domain
    
    def decision_type_for(
        self,
        domain: CriticalDomain,
        action: str = "",
    ) -> DecisionTypeForDomain:
        """
        Retourne le DecisionType approprié pour un domaine.
        """
        return self._get_decision_type(domain, bool(action))
    
    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _detect_domain(
        self,
        text: str,
    ) -> Tuple[CriticalDomain, float, List[str]]:
        """
        Détecte le domaine critique dans le texte.
        
        Returns:
            (domain, confidence, matched_patterns)
        """
        scores: Dict[CriticalDomain, int] = {}
        matches: Dict[CriticalDomain, List[str]] = {}
        
        text_lower = text.lower()
        
        for domain, patterns in self._compiled_domain_patterns.items():
            scores[domain] = 0
            matches[domain] = []
            
            for pattern in patterns:
                found = pattern.findall(text_lower)
                if found:
                    scores[domain] += len(found)
                    matches[domain].extend(found[:3])  # Limiter
        
        # Trouver le domaine avec le plus haut score
        max_score = 0
        best_domain = CriticalDomain.DEFAULT
        
        for domain, score in scores.items():
            if score > max_score:
                max_score = score
                best_domain = domain
        
        # Calculer la confiance
        if max_score == 0:
            confidence = 0.0
            matched = []
        elif max_score == 1:
            confidence = 0.6
            matched = matches[best_domain]
        elif max_score <= 3:
            confidence = 0.8
            matched = matches[best_domain]
        else:
            confidence = 0.95
            matched = matches[best_domain]
        
        return best_domain, confidence, matched
    
    def _detect_critical_action(
        self,
        text: str,
    ) -> Tuple[bool, List[str]]:
        """
        Détecte si une action critique est mentionnée.
        
        Returns:
            (has_critical, matched_patterns)
        """
        matched = []
        text_lower = text.lower()
        
        for pattern in self._compiled_action_patterns:
            found = pattern.findall(text_lower)
            if found:
                matched.extend(found[:2])
        
        return len(matched) > 0, matched
    
    def _get_decision_type(
        self,
        domain: CriticalDomain,
        has_critical_action: bool,
    ) -> DecisionTypeForDomain:
        """Map domain to decision type."""
        mapping = {
            CriticalDomain.LEGAL: DecisionTypeForDomain.LEGAL_DECISION,
            CriticalDomain.MEDICAL: DecisionTypeForDomain.MEDICAL_DECISION,
            CriticalDomain.SCIENTIFIC: DecisionTypeForDomain.SCIENTIFIC_VALIDATION,
            CriticalDomain.FINANCE_HIGH_RISK: DecisionTypeForDomain.FINANCIAL_DECISION,
            CriticalDomain.SECURITY: DecisionTypeForDomain.SECURITY_DECISION,
            CriticalDomain.COMPLIANCE: DecisionTypeForDomain.CRITICAL,
            CriticalDomain.DEFAULT: DecisionTypeForDomain.RESEARCH_VALIDATION,
        }
        
        if domain == CriticalDomain.DEFAULT and has_critical_action:
            return DecisionTypeForDomain.CRITICAL
        
        return mapping.get(domain, DecisionTypeForDomain.RESEARCH_VALIDATION)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_router_instance: Optional[CriticalityRouter] = None


def get_criticality_router() -> CriticalityRouter:
    """Retourne l'instance singleton du router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = CriticalityRouter()
    return _router_instance


def assess_criticality(
    query: str,
    agent_profile: str = "",
    task_metadata: Optional[Dict[str, Any]] = None,
    force_consensus: Optional[bool] = None,
) -> CriticalityAssessment:
    """
    Fonction raccourci pour évaluer la criticité.
    
    Usage:
        from python.helpers.criticality_router import assess_criticality
        
        assessment = assess_criticality(user_query, agent_profile="legal_safe")
        if assessment.requires_consensus:
            # ...
    """
    return get_criticality_router().assess(
        query, agent_profile, task_metadata, force_consensus
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "CriticalDomain",
    "DecisionTypeForDomain",
    # Constants
    "CONSENSUS_REQUIRED_PROFILES",
    "DEBUG_BYPASS_PROFILES",
    # Classes
    "CriticalityAssessment",
    "CriticalityRouter",
    # Functions
    "get_criticality_router",
    "assess_criticality",
]
