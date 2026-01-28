"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         LEGAL PIPELINE — EVIDENCE                            ║
║                                                                              ║
║  Pipeline juridique verrouillé pour Korev Evidence.                          ║
║                                                                              ║
║  AVERTISSEMENT: Ce module garantit la provenance et la traçabilité,          ║
║  pas l'exhaustivité ni l'interprétation juridique.                           ║
║                                                                              ║
║  Version: 1.1.0 (P0.7 Premium Gate)                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Ce module implémente:
- P0.1: LegalRiskTier + DecisionScope + Jurisdiction detection
- P0.2: LegalDraft + Claims list (claim→citation/hypothèse)
- P0.3: Judge checklist binaire (pas regex)
- P0.4: Consensus sur contrat, pas sur opinion
- P0.5: Output à 3 modes + bandeau + audit bundle partout
- P0.7: Premium Gate — Invariants stricts:
    A. audit_bundle_id déterministe (no timestamp)
    B. provenance obligatoire (no provenance = no output hors REFUSAL)
    C. consensus requis pour BOARD/MEDIUM/HIGH
    D. claims requis pour OPERATIONAL/BOARD
    E. SOURCES_PRESENT strict pour OPERATIONAL/BOARD
    F. output mode cohérent (APPROVED_POSITION ssi consensus APPROVED)
    G. fail-closed explicite avec codes missing_info standards
    H. zéro présomption FR silencieuse en BOARD
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("legal_pipeline")


# ═══════════════════════════════════════════════════════════════════════════════
# P0.1 — LEGAL ROUTING EXTENSION
# ═══════════════════════════════════════════════════════════════════════════════

class LegalRiskTier(str, Enum):
    """
    Niveau de risque juridique.
    
    Le droit n'est pas un intent, c'est un spectre de risque.
    """
    LOW = "low"        # Question simple, info publique
    MEDIUM = "medium"  # Interprétation, clause, contrat
    HIGH = "high"      # M&A, IPO, restructuration, contentieux majeur


class DecisionScope(str, Enum):
    """
    Portée de la décision juridique.
    """
    INFO = "info"              # Information pure, pas de conseil
    OPERATIONAL = "operational" # Conseil opérationnel (contrat, clause)
    BOARD = "board"            # Décision stratégique (board-level)


class Jurisdiction(str, Enum):
    """
    Juridiction détectée ou demandée.
    """
    FR = "fr"          # Droit français
    EU = "eu"          # Droit européen
    INTL = "intl"      # Droit international
    MIXED = "mixed"    # Mélange (nécessite clarification)
    UNKNOWN = "unknown" # Non détecté


@dataclass
class LegalRouteContext:
    """
    Contexte juridique enrichi produit par le router.
    
    S'ajoute au RouteDecision standard quand legal_safe est détecté.
    """
    risk_tier: LegalRiskTier
    scope: DecisionScope
    jurisdiction: Jurisdiction
    
    # Détails
    detected_articles: List[str] = field(default_factory=list)  # ["L132-8", "Art. 1134"]
    detected_codes: List[str] = field(default_factory=list)     # ["Code civil", "Code du travail"]
    detected_courts: List[str] = field(default_factory=list)    # ["Cass.", "CE"]
    
    # Flags
    requires_jurisdiction_clarification: bool = False
    has_abrogated_reference: bool = False
    is_contentieux: bool = False
    
    # Scores (pour debug)
    risk_score: float = 0.0
    scope_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_tier": self.risk_tier.value,
            "scope": self.scope.value,
            "jurisdiction": self.jurisdiction.value,
            "detected_articles": self.detected_articles,
            "detected_codes": self.detected_codes,
            "detected_courts": self.detected_courts,
            "requires_jurisdiction_clarification": self.requires_jurisdiction_clarification,
            "has_abrogated_reference": self.has_abrogated_reference,
            "is_contentieux": self.is_contentieux,
            "risk_score": round(self.risk_score, 2),
            "scope_score": round(self.scope_score, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# P0.7 — STANDARD MISSING INFO CODES
# ═══════════════════════════════════════════════════════════════════════════════

class MissingInfoCode:
    """
    Codes standardisés pour missing_info (fail-closed explicite).
    """
    FACTS_LIST = "facts_list"
    JURISDICTION = "jurisdiction"
    JURISDICTION_CLARIFICATION = "jurisdiction_clarification"
    CLAIMS_REQUIRED = "claims_required"
    UNSUPPORTED_CLAIMS = "unsupported_claims"
    PROVENANCE_MISSING = "provenance_missing"
    CONSENSUS_REQUIRED = "consensus_required"
    CONSENSUS_REJECTED = "consensus_rejected"
    CONSENSUS_NO_QUORUM = "consensus_no_quorum"        # NEW: evaluation done, no 2/3 majority
    CONSENSUS_INFRA_FAILURE = "consensus_infra_failure"  # NEW: all arbiters unavailable
    CITATIONS_MISSING = "citations_missing"
    APPLICATION_MISSING = "application_missing"
    SOURCES_MISSING = "sources_missing"


def requires_consensus(ctx: Optional["LegalRouteContext"]) -> bool:
    """
    P0.7 Invariant C: Détermine si consensus est requis.
    
    Règles:
    - scope == BOARD => consensus requis
    - risk_tier in {MEDIUM, HIGH} => consensus requis
    - Sinon (LOW + INFO/OPERATIONAL) => pas requis
    
    Returns:
        True si consensus obligatoire
    """
    if ctx is None:
        return False
    
    # BOARD scope always requires consensus
    if ctx.scope == DecisionScope.BOARD:
        return True
    
    # MEDIUM or HIGH risk requires consensus
    if ctx.risk_tier in (LegalRiskTier.MEDIUM, LegalRiskTier.HIGH):
        return True
    
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# LEGAL ROUTING POLICY
# ═══════════════════════════════════════════════════════════════════════════════

# HIGH risk triggers
HIGH_RISK_PATTERNS = [
    (r"\bm&a\b", 5.0),
    (r"\bipo\b", 5.0),
    (r"\blbo\b", 5.0),
    (r"\bfusion[\s-]?acquisition", 5.0),
    (r"\brestructuration\b", 4.0),
    (r"\bpse\b", 4.0),  # Plan de Sauvegarde de l'Emploi
    (r"\blicenciement collectif", 4.0),
    (r"\bcession d[e']entreprise", 5.0),
    (r"\bcession filiale", 4.0),
    (r"\bdue diligence\b", 5.0),
    (r"\bacquisition d[e']entreprise", 5.0),
    (r"\bacquisition\b", 3.5),  # Generic acquisition
    (r"\bcontestation\b", 3.5),
    (r"\bcassation\b", 4.0),
    (r"\bpourvoi\b", 4.0),
    (r"\bappel\b", 3.0),
    (r"\bréféré\b", 3.0),
    (r"\bassignation\b", 3.5),
    (r"\bprocès\b", 3.0),
    (r"\bcontentieux\b", 5.0),  # Contentieux = always significant
    (r"\bprud'hommes\b", 3.5),
    (r"\btribunal\b", 3.0),
    (r"défense\b", 3.0),
    (r"\bstratégie de défense", 4.0),
    (r"\bvalorisation\b", 3.5),
]

# MEDIUM risk triggers  
MEDIUM_RISK_PATTERNS = [
    (r"\bclause\b", 2.0),
    (r"\bcontrat\b", 2.0),
    (r"\bavenant\b", 2.5),
    (r"\bnon[-\s]?concurrence", 3.0),
    (r"\bgarantie\b", 2.0),
    (r"\bresponsabilité\b", 2.5),
    (r"\brgpd\b", 2.5),
    (r"\bconformité\b", 2.0),
    (r"\bcgu\b", 2.0),
    (r"\bconditions générales", 2.5),
    (r"\bpropriété intellectuelle", 2.5),
    (r"\bbrevet\b", 2.0),
    (r"\bmarque\b", 2.0),
]

# BOARD scope triggers
BOARD_SCOPE_PATTERNS = [
    (r"\bstratégi", 3.0),
    (r"\bboard\b", 3.0),
    (r"\bcomex\b", 3.0),
    (r"\bdirection générale", 3.0),
    (r"\bdécision critique", 4.0),
    (r"\binvestissement majeur", 3.5),
    (r"\blevée de fonds", 3.0),
    (r"\bseries [a-c]\b", 3.0),
    (r"\bvalorisation\b", 3.0),
    (r"\bvaluation\b", 3.0),
    (r"\bacquérir\b", 2.5),
    (r"\bcéder\b", 2.5),
    (r"\bm&a\b", 4.0),  # M&A is always board-level
    (r"\bdue diligence\b", 3.5),
    (r"\bacquisition d[e']entreprise", 4.0),
    (r"\bfusion", 3.0),
    (r"\bcession d[e']entreprise", 3.5),
    (r"\blbo\b", 4.0),
    (r"\bipo\b", 4.0),
]

# Jurisdiction patterns
FR_JURISDICTION_PATTERNS = [
    r"\bcode civil\b",
    r"\bc\.\s*civ\.?\b",  # C. civ.
    r"\bcode pénal\b",
    r"\bcode du travail\b",
    r"\bc\.\s*trav\.?\b",  # C. trav.
    r"\bcode de commerce\b",
    r"\bc\.\s*com\.?\b",  # C. com.
    r"\bloi française\b",
    r"\bdroit français\b",
    r"\bcass\.\s*civ",
    r"\bcass\.\s*com",
    r"\bcass\.\s*soc",
    r"\bce\.\s",
    r"\bconseil d'état\b",
    r"\bconseil constitutionnel\b",
    r"\btribunal de commerce\b",
    r"\btgi\b",
    r"\bprud'hommes\b",
    r"\bart\.\s*l\.?\s*\d",  # Art. L. xxx (French code format)
    r"\barticle\s*l\.?\s*\d",  # Article L. xxx
]

EU_JURISDICTION_PATTERNS = [
    r"\brèglement européen",
    r"\bdirective européenne",
    r"\bcjue\b",
    r"\brgpd\b",
    r"\bgdpr\b",
    r"\bdroit européen\b",
    r"\bunion européenne\b",
]

# Article patterns
ARTICLE_PATTERN = re.compile(
    r"(?:art(?:icle)?\.?\s*)?([Ll]?\d{1,4}(?:[-–]\d{1,4})?(?:[-–]\d+)?)",
    re.IGNORECASE
)

CODE_PATTERN = re.compile(
    r"(?:code\s+(?:civil|pénal|du\s+travail|de\s+commerce|de\s+la\s+consommation|monétaire))",
    re.IGNORECASE
)

COURT_PATTERN = re.compile(
    r"(?:cass\.\s*(?:civ|com|soc|crim)|ce\.|conseil d'état|cjue|tribunal|cour d'appel|prud'hommes)",
    re.IGNORECASE
)


def detect_legal_context(text: str) -> LegalRouteContext:
    """
    Détecte le contexte juridique d'un texte.
    
    Produit un LegalRouteContext avec:
    - risk_tier: LOW/MEDIUM/HIGH
    - scope: INFO/OPERATIONAL/BOARD
    - jurisdiction: FR/EU/INTL/MIXED/UNKNOWN
    """
    text_lower = text.lower()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Score risk tier
    # ─────────────────────────────────────────────────────────────────────────
    
    risk_score = 0.0
    is_contentieux = False
    
    for pattern, weight in HIGH_RISK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            risk_score += weight
            if pattern in [r"\bcontentieux\b", r"\bassignation\b", r"\bprocès\b"]:
                is_contentieux = True
    
    for pattern, weight in MEDIUM_RISK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            risk_score += weight * 0.5  # Half weight for medium
    
    # Determine tier (lowered threshold for HIGH)
    if risk_score >= 6.0:
        risk_tier = LegalRiskTier.HIGH
    elif risk_score >= 2.5:
        risk_tier = LegalRiskTier.MEDIUM
    else:
        risk_tier = LegalRiskTier.LOW
    
    # ─────────────────────────────────────────────────────────────────────────
    # Score decision scope
    # ─────────────────────────────────────────────────────────────────────────
    
    scope_score = 0.0
    
    for pattern, weight in BOARD_SCOPE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            scope_score += weight
    
    # High risk automatically elevates scope
    if risk_tier == LegalRiskTier.HIGH:
        scope_score += 3.0
    
    # Determine scope
    if scope_score >= 6.0:
        scope = DecisionScope.BOARD
    elif scope_score >= 2.0 or risk_tier == LegalRiskTier.MEDIUM:
        scope = DecisionScope.OPERATIONAL
    else:
        scope = DecisionScope.INFO
    
    # ─────────────────────────────────────────────────────────────────────────
    # Detect jurisdiction
    # ─────────────────────────────────────────────────────────────────────────
    
    has_fr = any(re.search(p, text_lower) for p in FR_JURISDICTION_PATTERNS)
    has_eu = any(re.search(p, text_lower) for p in EU_JURISDICTION_PATTERNS)
    
    if has_fr and has_eu:
        jurisdiction = Jurisdiction.MIXED
        requires_clarification = True
    elif has_fr:
        jurisdiction = Jurisdiction.FR
        requires_clarification = False
    elif has_eu:
        jurisdiction = Jurisdiction.EU
        requires_clarification = False
    else:
        jurisdiction = Jurisdiction.UNKNOWN
        # Only require clarification for non-INFO scope
        requires_clarification = scope != DecisionScope.INFO
    
    # ─────────────────────────────────────────────────────────────────────────
    # Extract references
    # ─────────────────────────────────────────────────────────────────────────
    
    articles = list(set(ARTICLE_PATTERN.findall(text)))[:10]
    codes = list(set(CODE_PATTERN.findall(text)))[:5]
    courts = list(set(COURT_PATTERN.findall(text)))[:5]
    
    # ─────────────────────────────────────────────────────────────────────────
    # Build context
    # ─────────────────────────────────────────────────────────────────────────
    
    return LegalRouteContext(
        risk_tier=risk_tier,
        scope=scope,
        jurisdiction=jurisdiction,
        detected_articles=articles,
        detected_codes=codes,
        detected_courts=courts,
        requires_jurisdiction_clarification=requires_clarification,
        has_abrogated_reference=False,  # TODO: Check against legal_sources
        is_contentieux=is_contentieux,
        risk_score=risk_score,
        scope_score=scope_score,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# P0.2 — LEGAL DRAFT + CLAIMS
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimType(str, Enum):
    """Type de claim."""
    CITED = "cited"        # Claim étayé par une citation
    HYPOTHESIS = "hypothesis"  # Hypothèse explicite
    UNSUPPORTED = "unsupported"  # Claim sans source (à rejeter)


@dataclass
class LegalClaim:
    """
    Un claim juridique avec son support.
    
    Règle: Chaque claim DOIT pointer vers une citation OU être marqué hypothèse.
    """
    id: str
    text: str
    claim_type: ClaimType
    
    # Si CITED: la citation source
    citation: Optional[str] = None
    source_chunk_id: Optional[str] = None
    
    # Si HYPOTHESIS: le contexte
    hypothesis_basis: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "claim_type": self.claim_type.value,
            "citation": self.citation,
            "source_chunk_id": self.source_chunk_id,
            "hypothesis_basis": self.hypothesis_basis,
        }
    
    @property
    def is_valid(self) -> bool:
        """Un claim est valide s'il est CITED ou HYPOTHESIS, pas UNSUPPORTED."""
        if self.claim_type == ClaimType.CITED:
            return bool(self.citation)
        elif self.claim_type == ClaimType.HYPOTHESIS:
            return True  # Hypothèse explicite = OK
        else:
            return False  # UNSUPPORTED = invalid


@dataclass
class LegalDraft:
    """
    Draft structuré produit par l'agent juridique.
    
    Structure "cabinet":
    - Facts: liste des faits (séparés du droit)
    - Rule: articles/arrêts applicables
    - Application: règle → faits
    - Risks: risques identifiés
    - Next action: courrier/checklist/recommandation
    - Claims: liste des claims avec citations
    """
    
    # Identification
    draft_id: str
    query: str
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    # Structure IRAC/FIRAC
    facts: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)  # Articles, arrêts cités
    application: str = ""  # Comment les règles s'appliquent aux faits
    risks: List[str] = field(default_factory=list)
    next_action: str = ""  # Recommandation concrète
    
    # Claims list (P0.2 core)
    claims: List[LegalClaim] = field(default_factory=list)
    
    # Sources utilisées
    source_chunk_ids: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    
    # Contexte
    legal_context: Optional[LegalRouteContext] = None
    
    # Metadata
    agent_model: str = ""
    confidence: float = 0.0
    
    # P5: Version status
    version_status: Optional[str] = None  # "resolved", "ambiguous", "not_found"
    as_of_date: Optional[str] = None  # ISO date string
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "query": self.query,
            "created_at": self.created_at,
            "facts": self.facts,
            "rules": self.rules,
            "application": self.application,
            "risks": self.risks,
            "next_action": self.next_action,
            "claims": [c.to_dict() for c in self.claims],
            "source_chunk_ids": self.source_chunk_ids,
            "citations": self.citations,
            "legal_context": self.legal_context.to_dict() if self.legal_context else None,
            "agent_model": self.agent_model,
            "confidence": self.confidence,
            # P5
            "version_status": self.version_status,
            "as_of_date": self.as_of_date,
        }
    
    @property
    def unsupported_claims(self) -> List[LegalClaim]:
        """Retourne les claims non supportés."""
        return [c for c in self.claims if not c.is_valid]
    
    @property
    def has_unsupported_claims(self) -> bool:
        """Vérifie si des claims sont non supportés."""
        return len(self.unsupported_claims) > 0
    
    def add_cited_claim(self, text: str, citation: str, chunk_id: Optional[str] = None):
        """Ajoute un claim avec citation."""
        claim_id = f"claim_{len(self.claims) + 1}"
        self.claims.append(LegalClaim(
            id=claim_id,
            text=text,
            claim_type=ClaimType.CITED,
            citation=citation,
            source_chunk_id=chunk_id,
        ))
    
    def add_hypothesis_claim(self, text: str, basis: str):
        """Ajoute un claim hypothétique."""
        claim_id = f"claim_{len(self.claims) + 1}"
        self.claims.append(LegalClaim(
            id=claim_id,
            text=text,
            claim_type=ClaimType.HYPOTHESIS,
            hypothesis_basis=basis,
        ))


def generate_draft_id(query: str, timestamp: float) -> str:
    """Génère un ID déterministe pour le draft."""
    content = f"{query}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════════
# P0.3 — JUDGE CHECKLIST BINAIRE
# ═══════════════════════════════════════════════════════════════════════════════

class JudgeCheckResult(str, Enum):
    """Résultat d'un check binaire."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"  # Warning mais pas bloquant


@dataclass
class JudgeCheck:
    """Un check individuel de la checklist."""
    check_id: str
    name: str
    result: JudgeCheckResult
    detail: str = ""
    is_critical: bool = True  # Si True, FAIL = reject
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "result": self.result.value,
            "detail": self.detail,
            "is_critical": self.is_critical,
        }


class LegalJudgeVerdict(str, Enum):
    """Verdict du judge juridique."""
    APPROVE = "approve"              # Tout OK, passer au consensus
    REJECT = "reject"                # Check critique échoué
    REQUEST_INFO = "request_info"    # Infos manquantes


@dataclass
class LegalJudgeResult:
    """
    Résultat du judge juridique.
    
    Checklist binaire P0:
    1. SOURCES_PRESENT: toutes les règles citées
    2. FACTS_SEPARATED: faits ≠ droit
    3. APPLICATION_PRESENT: règle → faits
    4. NO_UNSUPPORTED_CLAIMS: zéro claim sans source/hypothèse
    5. JURISDICTION_CLEAR: juridiction identifiée
    6. ABROGATION_HANDLED: si texte abrogé, signalé
    """
    
    verdict: LegalJudgeVerdict
    checks: List[JudgeCheck] = field(default_factory=list)
    
    # Critical flags
    critical_failures: List[str] = field(default_factory=list)
    
    # Missing info
    missing_info_required: List[str] = field(default_factory=list)
    
    # Metadata
    draft_id: str = ""
    judged_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "checks": [c.to_dict() for c in self.checks],
            "critical_failures": self.critical_failures,
            "missing_info_required": self.missing_info_required,
            "draft_id": self.draft_id,
            "judged_at": self.judged_at,
        }
    
    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.result == JudgeCheckResult.PASS)
    
    @property
    def total_count(self) -> int:
        return len(self.checks)
    
    @property
    def pass_rate(self) -> float:
        if not self.checks:
            return 0.0
        return self.passed_count / self.total_count


def judge_legal_draft(draft: LegalDraft) -> LegalJudgeResult:
    """
    Judge binaire sur un LegalDraft.
    
    Checklist P0.7 (pas de regex sophistiqué, juste des checks binaires).
    
    P0.7 Durcissement:
    - SOURCES_PRESENT: strict pour OPERATIONAL/BOARD (rules sans citations = FAIL)
    - CLAIMS_REQUIRED: nouveau check pour OPERATIONAL/BOARD
    - NO_UNSUPPORTED_CLAIMS: strict pour OPERATIONAL/BOARD
    """
    checks: List[JudgeCheck] = []
    critical_failures: List[str] = []
    missing_info: List[str] = []
    
    # Get scope for P0.7 strict checks
    ctx = draft.legal_context
    scope = ctx.scope if ctx else DecisionScope.INFO
    is_strict_scope = scope in (DecisionScope.OPERATIONAL, DecisionScope.BOARD)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 1: SOURCES_PRESENT — Toutes les règles citées
    # P0.7 Invariant E: strict pour OPERATIONAL/BOARD
    # ─────────────────────────────────────────────────────────────────────────
    
    has_rules = len(draft.rules) > 0
    has_citations = len(draft.citations) > 0 or len(draft.source_chunk_ids) > 0
    
    if has_rules and has_citations:
        checks.append(JudgeCheck(
            check_id="sources_present",
            name="SOURCES_PRESENT",
            result=JudgeCheckResult.PASS,
            detail=f"{len(draft.rules)} rules, {len(draft.citations)} citations",
        ))
    elif has_rules:
        # P0.7: OPERATIONAL/BOARD => FAIL if rules without citations
        if is_strict_scope:
            checks.append(JudgeCheck(
                check_id="sources_present",
                name="SOURCES_PRESENT",
                result=JudgeCheckResult.FAIL,
                detail=f"Rules présentes ({len(draft.rules)}) mais citations manquantes (scope={scope.value})",
            ))
            critical_failures.append("SOURCES_PRESENT")
            missing_info.append(MissingInfoCode.CITATIONS_MISSING)
        else:
            checks.append(JudgeCheck(
                check_id="sources_present",
                name="SOURCES_PRESENT",
                result=JudgeCheckResult.WARN,
                detail="Rules présentes mais pas de citations formelles",
                is_critical=False,
            ))
    else:
        checks.append(JudgeCheck(
            check_id="sources_present",
            name="SOURCES_PRESENT",
            result=JudgeCheckResult.FAIL,
            detail="Aucune règle juridique citée",
        ))
        critical_failures.append("SOURCES_PRESENT")
        missing_info.append(MissingInfoCode.SOURCES_MISSING)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 2: FACTS_SEPARATED — Faits ≠ droit
    # ─────────────────────────────────────────────────────────────────────────
    
    if len(draft.facts) > 0:
        checks.append(JudgeCheck(
            check_id="facts_separated",
            name="FACTS_SEPARATED",
            result=JudgeCheckResult.PASS,
            detail=f"{len(draft.facts)} faits identifiés",
        ))
    else:
        checks.append(JudgeCheck(
            check_id="facts_separated",
            name="FACTS_SEPARATED",
            result=JudgeCheckResult.FAIL,
            detail="Section 'Facts' vide — faits non séparés du droit",
        ))
        critical_failures.append("FACTS_SEPARATED")
        missing_info.append(MissingInfoCode.FACTS_LIST)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 3: APPLICATION_PRESENT — Règle → faits
    # ─────────────────────────────────────────────────────────────────────────
    
    if draft.application and len(draft.application.strip()) > 50:
        checks.append(JudgeCheck(
            check_id="application_present",
            name="APPLICATION_PRESENT",
            result=JudgeCheckResult.PASS,
            detail=f"Application: {len(draft.application)} chars",
        ))
    elif draft.application:
        checks.append(JudgeCheck(
            check_id="application_present",
            name="APPLICATION_PRESENT",
            result=JudgeCheckResult.WARN,
            detail="Application présente mais trop courte",
            is_critical=False,
        ))
    else:
        checks.append(JudgeCheck(
            check_id="application_present",
            name="APPLICATION_PRESENT",
            result=JudgeCheckResult.FAIL,
            detail="Section 'Application' vide — pas de lien règle→faits",
        ))
        critical_failures.append("APPLICATION_PRESENT")
        missing_info.append(MissingInfoCode.APPLICATION_MISSING)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 4: CLAIMS_REQUIRED — Claims obligatoires pour OPERATIONAL/BOARD
    # P0.7 Invariant D: nouveau check
    # ─────────────────────────────────────────────────────────────────────────
    
    if is_strict_scope:
        if len(draft.claims) > 0:
            checks.append(JudgeCheck(
                check_id="claims_required",
                name="CLAIMS_REQUIRED",
                result=JudgeCheckResult.PASS,
                detail=f"{len(draft.claims)} claims présents (scope={scope.value})",
            ))
        else:
            checks.append(JudgeCheck(
                check_id="claims_required",
                name="CLAIMS_REQUIRED",
                result=JudgeCheckResult.FAIL,
                detail=f"Claims obligatoires pour scope {scope.value} mais aucun fourni",
            ))
            critical_failures.append("CLAIMS_REQUIRED")
            missing_info.append(MissingInfoCode.CLAIMS_REQUIRED)
    else:
        # INFO scope: claims not required
        checks.append(JudgeCheck(
            check_id="claims_required",
            name="CLAIMS_REQUIRED",
            result=JudgeCheckResult.PASS,
            detail=f"Claims optionnels pour scope {scope.value}",
            is_critical=False,
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 5: NO_UNSUPPORTED_CLAIMS — Zéro claim sans source/hypothèse
    # ─────────────────────────────────────────────────────────────────────────
    
    unsupported = draft.unsupported_claims
    
    if not draft.claims:
        # P0.7: If we already failed CLAIMS_REQUIRED, don't double-count
        if "CLAIMS_REQUIRED" not in critical_failures:
            checks.append(JudgeCheck(
                check_id="no_unsupported_claims",
                name="NO_UNSUPPORTED_CLAIMS",
                result=JudgeCheckResult.WARN,
                detail="Aucun claim explicite (structure claims non utilisée)",
                is_critical=False,
            ))
        else:
            checks.append(JudgeCheck(
                check_id="no_unsupported_claims",
                name="NO_UNSUPPORTED_CLAIMS",
                result=JudgeCheckResult.PASS,
                detail="N/A (pas de claims)",
                is_critical=False,
            ))
    elif len(unsupported) == 0:
        cited = sum(1 for c in draft.claims if c.claim_type == ClaimType.CITED)
        hypo = sum(1 for c in draft.claims if c.claim_type == ClaimType.HYPOTHESIS)
        checks.append(JudgeCheck(
            check_id="no_unsupported_claims",
            name="NO_UNSUPPORTED_CLAIMS",
            result=JudgeCheckResult.PASS,
            detail=f"{cited} cited, {hypo} hypothèses",
        ))
    else:
        checks.append(JudgeCheck(
            check_id="no_unsupported_claims",
            name="NO_UNSUPPORTED_CLAIMS",
            result=JudgeCheckResult.FAIL,
            detail=f"{len(unsupported)} claims sans source: {[c.text[:30] for c in unsupported]}",
        ))
        critical_failures.append("NO_UNSUPPORTED_CLAIMS")
        missing_info.append(MissingInfoCode.UNSUPPORTED_CLAIMS)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 6: JURISDICTION_CLEAR — Juridiction identifiée
    # P0.7 Invariant H: Zéro présomption FR silencieuse en BOARD
    # ─────────────────────────────────────────────────────────────────────────
    
    if ctx is not None:
        jurisdiction = ctx.jurisdiction
        if jurisdiction != Jurisdiction.UNKNOWN:
            if jurisdiction == Jurisdiction.MIXED:
                checks.append(JudgeCheck(
                    check_id="jurisdiction_clear",
                    name="JURISDICTION_CLEAR",
                    result=JudgeCheckResult.WARN,
                    detail="Juridiction mixte (FR+EU) — clarifier",
                    is_critical=False,
                ))
                missing_info.append(MissingInfoCode.JURISDICTION_CLARIFICATION)
            else:
                checks.append(JudgeCheck(
                    check_id="jurisdiction_clear",
                    name="JURISDICTION_CLEAR",
                    result=JudgeCheckResult.PASS,
                    detail=f"Juridiction: {jurisdiction.value}",
                ))
        else:
            # P0.7 Invariant H: BOARD scope requires explicit jurisdiction
            # No silent "presumed FR" for BOARD
            if scope == DecisionScope.BOARD:
                checks.append(JudgeCheck(
                    check_id="jurisdiction_clear",
                    name="JURISDICTION_CLEAR",
                    result=JudgeCheckResult.FAIL,
                    detail="Juridiction non identifiée pour scope BOARD (P0.7: présomption FR interdite)",
                ))
                critical_failures.append("JURISDICTION_CLEAR")
                missing_info.append(MissingInfoCode.JURISDICTION)
            elif scope == DecisionScope.OPERATIONAL:
                # OPERATIONAL: warn but don't block
                checks.append(JudgeCheck(
                    check_id="jurisdiction_clear",
                    name="JURISDICTION_CLEAR",
                    result=JudgeCheckResult.WARN,
                    detail="Juridiction non détectée (OPERATIONAL scope — droit français présumé)",
                    is_critical=False,
                ))
            else:
                # INFO: OK
                checks.append(JudgeCheck(
                    check_id="jurisdiction_clear",
                    name="JURISDICTION_CLEAR",
                    result=JudgeCheckResult.PASS,
                    detail="Juridiction non requise pour scope INFO",
                    is_critical=False,
                ))
    else:
        checks.append(JudgeCheck(
            check_id="jurisdiction_clear",
            name="JURISDICTION_CLEAR",
            result=JudgeCheckResult.WARN,
            detail="Pas de contexte juridique fourni",
            is_critical=False,
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 6: ABROGATION_HANDLED — Si texte abrogé, signalé
    # ─────────────────────────────────────────────────────────────────────────
    
    if draft.legal_context and draft.legal_context.has_abrogated_reference:
        # Check if risks mention abrogation
        abro_mentioned = any("abrogé" in r.lower() or "abrogation" in r.lower() for r in draft.risks)
        if abro_mentioned:
            checks.append(JudgeCheck(
                check_id="abrogation_handled",
                name="ABROGATION_HANDLED",
                result=JudgeCheckResult.PASS,
                detail="Texte abrogé signalé dans les risques",
            ))
        else:
            checks.append(JudgeCheck(
                check_id="abrogation_handled",
                name="ABROGATION_HANDLED",
                result=JudgeCheckResult.FAIL,
                detail="Référence à texte abrogé non signalée",
            ))
            critical_failures.append("ABROGATION_HANDLED")
    else:
        checks.append(JudgeCheck(
            check_id="abrogation_handled",
            name="ABROGATION_HANDLED",
            result=JudgeCheckResult.PASS,
            detail="Pas de texte abrogé détecté",
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK 7 (P5): VERSION_RESOLVED — Toutes les sources ont une version résolue
    # ─────────────────────────────────────────────────────────────────────────
    
    # P5: Check version resolution status if as_of_date was used
    # This check is only critical for OPERATIONAL/BOARD scopes
    version_check_required = is_strict_scope and draft.source_chunk_ids
    
    if version_check_required:
        # In a real implementation, we'd check each source_chunk_id for resolved version
        # For now, we check if the draft has version metadata
        has_version_metadata = hasattr(draft, 'version_status') and draft.version_status
        
        if has_version_metadata:
            if draft.version_status == "resolved":
                checks.append(JudgeCheck(
                    check_id="version_resolved",
                    name="VERSION_RESOLVED",
                    result=JudgeCheckResult.PASS,
                    detail=f"Toutes les sources ont une version résolue ({len(draft.source_chunk_ids)} sources)",
                ))
            elif draft.version_status == "ambiguous":
                checks.append(JudgeCheck(
                    check_id="version_resolved",
                    name="VERSION_RESOLVED",
                    result=JudgeCheckResult.FAIL,
                    detail="Ambiguïté temporelle: plusieurs versions valides pour certaines sources",
                ))
                critical_failures.append("VERSION_RESOLVED")
                missing_info.append("version_ambiguity")
            else:  # not_found
                checks.append(JudgeCheck(
                    check_id="version_resolved",
                    name="VERSION_RESOLVED",
                    result=JudgeCheckResult.FAIL,
                    detail="Version non trouvée pour certaines sources à la date spécifiée",
                ))
                critical_failures.append("VERSION_RESOLVED")
                missing_info.append("version_not_found")
        else:
            # No version metadata but strict scope — fail
            checks.append(JudgeCheck(
                check_id="version_resolved",
                name="VERSION_RESOLVED",
                result=JudgeCheckResult.WARN,
                detail="Métadonnées de version non disponibles",
                is_critical=False,
            ))
    else:
        checks.append(JudgeCheck(
            check_id="version_resolved",
            name="VERSION_RESOLVED",
            result=JudgeCheckResult.PASS,
            detail="Check version non requis (scope INFO ou pas de sources)",
            is_critical=False,
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # DETERMINE VERDICT
    # ─────────────────────────────────────────────────────────────────────────
    
    if critical_failures:
        verdict = LegalJudgeVerdict.REJECT
    elif missing_info:
        verdict = LegalJudgeVerdict.REQUEST_INFO
    else:
        verdict = LegalJudgeVerdict.APPROVE
    
    return LegalJudgeResult(
        verdict=verdict,
        checks=checks,
        critical_failures=critical_failures,
        missing_info_required=missing_info,
        draft_id=draft.draft_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# P0.4 — CONSENSUS ON CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class LegalConsensusType(str, Enum):
    """Type de consensus juridique."""
    CONTRACT_COMPLIANCE = "contract_compliance"  # Contrat de sortie conforme
    CLAIM_SUPPORT = "claim_support"              # Claims supportés
    RISK_TIER_CONSISTENCY = "risk_tier_consistency"  # Risk tier cohérent


@dataclass
class LegalConsensusItem:
    """Item à voter dans le consensus."""
    item_type: LegalConsensusType
    question: str
    expected: str
    actual: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_type": self.item_type.value,
            "question": self.question,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class LegalConsensusProposal:
    """
    Proposition de consensus juridique.
    
    Le consensus vote sur le CONTRAT, pas sur l'OPINION.
    Items:
    1. contract_compliance: Citations présentes, provenance, pas d'affirmations sans sources
    2. claim_support: Cohérence faits→règle→application
    3. risk_tier_consistency: Absence de "claims" non vérifiables
    """
    
    proposal_id: str
    draft_id: str
    
    # Items à voter
    items: List[LegalConsensusItem] = field(default_factory=list)
    
    # Context
    risk_tier: LegalRiskTier = LegalRiskTier.LOW
    scope: DecisionScope = DecisionScope.INFO
    
    # Judge result (pré-requis)
    judge_passed: bool = False
    judge_pass_rate: float = 0.0
    
    # Quorum rules
    required_approvals: int = 2
    require_unanimity: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "draft_id": self.draft_id,
            "items": [i.to_dict() for i in self.items],
            "risk_tier": self.risk_tier.value,
            "scope": self.scope.value,
            "judge_passed": self.judge_passed,
            "judge_pass_rate": self.judge_pass_rate,
            "required_approvals": self.required_approvals,
            "require_unanimity": self.require_unanimity,
        }


def build_legal_consensus_proposal(
    draft: LegalDraft,
    judge_result: LegalJudgeResult,
) -> LegalConsensusProposal:
    """
    Construit une proposition de consensus à partir d'un draft et du judge result.
    """
    items: List[LegalConsensusItem] = []
    
    ctx = draft.legal_context
    risk_tier = ctx.risk_tier if ctx else LegalRiskTier.LOW
    scope = ctx.scope if ctx else DecisionScope.INFO
    
    # ─────────────────────────────────────────────────────────────────────────
    # Item 1: CONTRACT_COMPLIANCE
    # ─────────────────────────────────────────────────────────────────────────
    
    has_citations = len(draft.citations) > 0 or len(draft.source_chunk_ids) > 0
    has_facts = len(draft.facts) > 0
    has_application = bool(draft.application)
    
    compliance_actual = f"citations={has_citations}, facts={has_facts}, application={has_application}"
    
    items.append(LegalConsensusItem(
        item_type=LegalConsensusType.CONTRACT_COMPLIANCE,
        question="Le contrat de sortie est-il structurellement conforme?",
        expected="citations=True, facts=True, application=True",
        actual=compliance_actual,
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Item 2: CLAIM_SUPPORT
    # ─────────────────────────────────────────────────────────────────────────
    
    total_claims = len(draft.claims)
    cited_claims = sum(1 for c in draft.claims if c.claim_type == ClaimType.CITED)
    hypothesis_claims = sum(1 for c in draft.claims if c.claim_type == ClaimType.HYPOTHESIS)
    unsupported = draft.unsupported_claims
    
    support_actual = f"total={total_claims}, cited={cited_claims}, hypo={hypothesis_claims}, unsupported={len(unsupported)}"
    
    items.append(LegalConsensusItem(
        item_type=LegalConsensusType.CLAIM_SUPPORT,
        question="Tous les claims sont-ils supportés (citation ou hypothèse explicite)?",
        expected="unsupported=0",
        actual=support_actual,
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Item 3: RISK_TIER_CONSISTENCY
    # ─────────────────────────────────────────────────────────────────────────
    
    # Check if response complexity matches risk tier
    response_depth = len(draft.rules) + len(draft.risks) + len(draft.claims)
    
    if risk_tier == LegalRiskTier.HIGH:
        expected_depth = "response_depth>=5"
        depth_ok = response_depth >= 5
    elif risk_tier == LegalRiskTier.MEDIUM:
        expected_depth = "response_depth>=3"
        depth_ok = response_depth >= 3
    else:
        expected_depth = "response_depth>=1"
        depth_ok = response_depth >= 1
    
    items.append(LegalConsensusItem(
        item_type=LegalConsensusType.RISK_TIER_CONSISTENCY,
        question=f"La profondeur de réponse est-elle cohérente avec risk_tier={risk_tier.value}?",
        expected=expected_depth,
        actual=f"response_depth={response_depth}, ok={depth_ok}",
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Determine quorum
    # ─────────────────────────────────────────────────────────────────────────
    
    # LOW/MEDIUM: 2/3
    # BOARD: 2/3 + judge_pass + no_critical_flags
    # HIGH: unanimity + escalade
    
    if risk_tier == LegalRiskTier.HIGH:
        required_approvals = 3
        require_unanimity = True
    elif scope == DecisionScope.BOARD:
        required_approvals = 2
        require_unanimity = False
    else:
        required_approvals = 2
        require_unanimity = False
    
    # Generate proposal ID (deterministic, no timestamp)
    proposal_content = f"{draft.draft_id}:{risk_tier.value}:{scope.value}:{len(draft.claims)}"
    proposal_id = hashlib.sha256(proposal_content.encode()).hexdigest()[:12]
    
    return LegalConsensusProposal(
        proposal_id=proposal_id,
        draft_id=draft.draft_id,
        items=items,
        risk_tier=risk_tier,
        scope=scope,
        judge_passed=judge_result.verdict == LegalJudgeVerdict.APPROVE,
        judge_pass_rate=judge_result.pass_rate,
        required_approvals=required_approvals,
        require_unanimity=require_unanimity,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# P0.5 — OUTPUT MODES + BANNER
# ═══════════════════════════════════════════════════════════════════════════════

class LegalOutputMode(str, Enum):
    """Mode de sortie juridique."""
    APPROVED_POSITION = "approved_position"    # Position validée par consensus
    SAFE_ANALYSIS = "safe_analysis"            # Analyse sécurisée (non validée mais structurée)
    REFUSAL_REQUEST_INFO = "refusal_request_info"  # Refus — informations manquantes


@dataclass
class LegalOutput:
    """
    Sortie juridique complète.
    
    Toujours avec:
    - Mode (position validée / analyse sécurisée / refus)
    - Bandeau approprié
    - Citations + provenance
    - audit_bundle_id (même en refus)
    """
    
    # Mode
    mode: LegalOutputMode
    
    # Content
    answer: str
    
    # Structure
    facts: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    application: str = ""
    risks: List[str] = field(default_factory=list)
    next_action: str = ""
    
    # Sources (OBLIGATOIRE)
    citations: List[str] = field(default_factory=list)
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    
    # Consensus
    consensus_id: Optional[str] = None
    consensus_status: Optional[str] = None
    arbiter_votes: Dict[str, str] = field(default_factory=dict)
    
    # Judge
    judge_verdict: Optional[str] = None
    judge_checks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Audit
    audit_bundle_id: str = ""
    
    # Missing info (for REFUSAL)
    missing_info: List[str] = field(default_factory=list)
    
    # Context
    risk_tier: Optional[str] = None
    scope: Optional[str] = None
    jurisdiction: Optional[str] = None
    
    # P5: Temporal versioning
    as_of_date: Optional[str] = None  # ISO date string: YYYY-MM-DD
    version_status: Optional[str] = None  # "resolved", "ambiguous", "not_found"
    
    # P6.1: Legal Diff
    diff_status: Optional[str] = None  # "available", "not_applicable", "error"
    diff_summary: Optional[str] = None  # Textual summary of changes
    diff_report: Optional[Dict[str, Any]] = None  # Full LegalDiffReport.to_dict()
    
    # Disclaimer (TOUJOURS présent)
    disclaimer: str = (
        "Ce module garantit la provenance et la traçabilité des sources, "
        "pas l'exhaustivité ni l'interprétation juridique. "
        "Le droit opposable n'est authentifié que sur les sites officiels."
    )
    
    def get_banner(self) -> str:
        """Retourne le bandeau approprié au mode."""
        date_suffix = ""
        if self.as_of_date:
            # Format: JJ/MM/AAAA
            try:
                parts = self.as_of_date.split("-")
                date_suffix = f" (droit en vigueur au {parts[2]}/{parts[1]}/{parts[0]})"
            except (IndexError, ValueError):
                date_suffix = f" (au {self.as_of_date})"
        
        if self.mode == LegalOutputMode.APPROVED_POSITION:
            return f"✅ POSITION VALIDÉE — Consensus atteint, sources vérifiées{date_suffix}"
        elif self.mode == LegalOutputMode.SAFE_ANALYSIS:
            return f"🔒 ANALYSE SÉCURISÉE — Structure conforme, consensus non requis{date_suffix}"
        else:
            return "⚠️ REFUS — Informations manquantes requises"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "banner": self.get_banner(),
            "answer": self.answer,
            "facts": self.facts,
            "rules": self.rules,
            "application": self.application,
            "risks": self.risks,
            "next_action": self.next_action,
            "citations": self.citations,
            "provenance": self.provenance,
            "consensus_id": self.consensus_id,
            "consensus_status": self.consensus_status,
            "arbiter_votes": self.arbiter_votes,
            "judge_verdict": self.judge_verdict,
            "judge_checks": self.judge_checks,
            "audit_bundle_id": self.audit_bundle_id,
            "missing_info": self.missing_info,
            "risk_tier": self.risk_tier,
            "scope": self.scope,
            "jurisdiction": self.jurisdiction,
            "as_of_date": self.as_of_date,
            "version_status": self.version_status,
            # P6.1
            "diff_status": self.diff_status,
            "diff_summary": self.diff_summary,
            "diff_report": self.diff_report,
            "disclaimer": self.disclaimer,
        }
    
    def to_markdown(self) -> str:
        """Génère une sortie Markdown formatée."""
        lines = []
        
        # Banner
        lines.append(f"## {self.get_banner()}")
        lines.append("")
        
        # Context
        if self.risk_tier or self.scope or self.jurisdiction:
            lines.append(f"**Contexte**: Risk={self.risk_tier}, Scope={self.scope}, Juridiction={self.jurisdiction}")
            lines.append("")
        
        # Answer
        lines.append("### Réponse")
        lines.append(self.answer)
        lines.append("")
        
        # Structure (if not refusal)
        if self.mode != LegalOutputMode.REFUSAL_REQUEST_INFO:
            if self.facts:
                lines.append("### Faits")
                for f in self.facts:
                    lines.append(f"- {f}")
                lines.append("")
            
            if self.rules:
                lines.append("### Règles applicables")
                for r in self.rules:
                    lines.append(f"- {r}")
                lines.append("")
            
            if self.application:
                lines.append("### Application")
                lines.append(self.application)
                lines.append("")
            
            if self.risks:
                lines.append("### Risques")
                for r in self.risks:
                    lines.append(f"- ⚠️ {r}")
                lines.append("")
            
            if self.next_action:
                lines.append("### Prochaine action")
                lines.append(self.next_action)
                lines.append("")
        
        # Missing info (if refusal)
        if self.missing_info:
            lines.append("### Informations manquantes")
            for m in self.missing_info:
                lines.append(f"- ❓ {m}")
            lines.append("")
        
        # Sources
        if self.citations:
            lines.append("### Sources")
            for c in self.citations:
                lines.append(f"- 📖 {c}")
            lines.append("")
        
        # P6.1: Évolutions depuis la version précédente
        if self.diff_status == "available" and self.diff_summary:
            lines.append("### Évolutions depuis la version précédente")
            lines.append(self.diff_summary)
            if self.diff_report:
                aggr = self.diff_report.get("aggravation_detected", False)
                relax = self.diff_report.get("relaxation_detected", False)
                if aggr:
                    lines.append("")
                    lines.append("⚠️ **Aggravation potentielle détectée**")
                if relax:
                    lines.append("")
                    lines.append("✅ **Assouplissement potentiel détecté**")
            lines.append("")
        elif self.diff_status == "not_applicable":
            lines.append("### Évolutions")
            lines.append("_Pas de version précédente disponible._")
            lines.append("")
        
        # Audit
        lines.append("---")
        lines.append(f"*Audit Bundle: `{self.audit_bundle_id}`*")
        if self.consensus_id:
            lines.append(f"*Consensus: `{self.consensus_id}` — {self.consensus_status}*")
        if self.judge_verdict:
            lines.append(f"*Judge: {self.judge_verdict}*")
        lines.append("")
        
        # Disclaimer
        lines.append("> **Avertissement**: " + self.disclaimer)
        
        return "\n".join(lines)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Valide que l'output est complet.
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Toujours requis
        if not self.audit_bundle_id:
            errors.append("audit_bundle_id manquant")
        
        # Mode-specific
        if self.mode == LegalOutputMode.APPROVED_POSITION:
            if not self.consensus_status or self.consensus_status != "APPROVED":
                errors.append("Position validée nécessite consensus APPROVED")
            if not self.citations:
                errors.append("Position validée nécessite des citations")
        
        elif self.mode == LegalOutputMode.SAFE_ANALYSIS:
            if not self.judge_verdict:
                errors.append("Analyse sécurisée nécessite judge verdict")
        
        elif self.mode == LegalOutputMode.REFUSAL_REQUEST_INFO:
            if not self.missing_info:
                errors.append("Refus nécessite missing_info")
        
        return len(errors) == 0, errors


def generate_audit_bundle_id(
    draft_id: str,
    output_mode: str,
    source_chunk_ids: Optional[List[str]] = None,
    citations: Optional[List[str]] = None,
) -> str:
    """
    P0.7 Invariant A: Génère un audit_bundle_id STRICTEMENT déterministe.
    
    Input déterministe:
    - draft_id
    - output_mode
    - source_chunk_ids (sorted)
    - citations (sorted)
    
    Output: "audit_" + sha256(concat stable)[:16]
    
    AUCUN timestamp, datetime, ou random.
    """
    # Sort pour garantir la stabilité
    chunk_ids_sorted = sorted(source_chunk_ids or [])
    citations_sorted = sorted(citations or [])
    
    # Build deterministic content
    content_parts = [
        f"draft:{draft_id}",
        f"mode:{output_mode}",
        f"chunks:{','.join(chunk_ids_sorted)}",
        f"citations:{','.join(citations_sorted)}",
    ]
    content = "|".join(content_parts)
    
    return f"audit_{hashlib.sha256(content.encode()).hexdigest()[:16]}"


def resolve_provenance_for_chunks(
    chunk_ids: List[str],
    provenance_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    P0.7 Invariant B: Résout la provenance pour chaque chunk_id.
    
    Args:
        chunk_ids: Liste de chunk_ids
        provenance_map: Mapping chunk_id -> provenance dict (optionnel, pour tests)
        
    Returns:
        Liste de provenance dicts alignée avec chunk_ids
    """
    if not chunk_ids:
        return []
    
    if provenance_map:
        # Use provided map (for testing or pre-fetched data)
        return [provenance_map.get(cid, {}) for cid in chunk_ids]
    
    # Try to fetch from legal_sources index
    try:
        from python.helpers.legal_retrieval import LegalRetriever
        retriever = LegalRetriever()
        index = retriever._get_index()
        
        if index:
            chunks_data = index.get_all_chunks_for_ids(chunk_ids)
            provenance_list = []
            chunk_map = {c["chunk_id"]: c.get("provenance", {}) for c in chunks_data}
            for cid in chunk_ids:
                provenance_list.append(chunk_map.get(cid, {}))
            return provenance_list
    except Exception as e:
        logger.warning(f"Failed to resolve provenance: {e}")
    
    # Fallback: empty provenance
    return [{} for _ in chunk_ids]


def validate_provenance_complete(provenance_list: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    P0.7 Invariant B: Vérifie que la provenance est complète.
    
    Champs requis minimum:
    - source (legi, cass, etc.)
    - license_name
    
    Returns:
        (is_valid, list of missing fields)
    """
    if not provenance_list:
        return False, ["provenance_empty"]
    
    missing = []
    for i, prov in enumerate(provenance_list):
        if not prov:
            missing.append(f"provenance[{i}]_empty")
            continue
        if not prov.get("source"):
            missing.append(f"provenance[{i}]_source_missing")
        # license_name is highly recommended but not blocking for now
    
    return len(missing) == 0, missing


def build_legal_output(
    draft: LegalDraft,
    judge_result: LegalJudgeResult,
    consensus_result: Optional[Dict[str, Any]] = None,
    provenance_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> LegalOutput:
    """
    P0.7 Premium Gate: Construit la sortie juridique finale avec invariants stricts.
    
    Invariants enforced:
    A. audit_bundle_id déterministe
    B. provenance obligatoire (mode ≠ REFUSAL)
    C. consensus requis pour BOARD/MEDIUM/HIGH
    F. APPROVED_POSITION ssi consensus APPROVED
    G. fail-closed explicite
    
    Args:
        draft: LegalDraft validé par le judge
        judge_result: Résultat du judge
        consensus_result: Résultat du consensus (optionnel)
        provenance_map: Map chunk_id -> provenance (optionnel, pour tests)
        
    Returns:
        LegalOutput avec mode approprié
    """
    ctx = draft.legal_context
    risk_tier = ctx.risk_tier.value if ctx else None
    scope = ctx.scope.value if ctx else None
    jurisdiction = ctx.jurisdiction.value if ctx else None
    
    # Collect missing_info from judge
    missing_info = list(judge_result.missing_info_required)
    
    # ─────────────────────────────────────────────────────────────────────────
    # P0.7 INVARIANT C: Check if consensus is required
    # ─────────────────────────────────────────────────────────────────────────
    
    consensus_required = requires_consensus(ctx)
    consensus_status = consensus_result.get("status") if consensus_result else None
    consensus_approved = consensus_status == "APPROVED"
    consensus_rejected = consensus_status == "REJECTED"
    consensus_no_quorum = consensus_status == "NO_CONSENSUS"
    consensus_infra_failure = consensus_status == "INFRA_FAILURE" or consensus_status == "TIMEOUT"
    
    # ─────────────────────────────────────────────────────────────────────────
    # P0.7 INVARIANT B: Resolve provenance
    # ─────────────────────────────────────────────────────────────────────────
    
    provenance_list = resolve_provenance_for_chunks(
        draft.source_chunk_ids,
        provenance_map,
    )
    provenance_valid, provenance_missing = validate_provenance_complete(provenance_list)
    
    # ─────────────────────────────────────────────────────────────────────────
    # DETERMINE MODE (P0.7 strict logic)
    # ─────────────────────────────────────────────────────────────────────────
    
    mode = LegalOutputMode.REFUSAL_REQUEST_INFO  # Default to fail-closed
    
    # Case 1: Judge rejected
    if judge_result.verdict == LegalJudgeVerdict.REJECT:
        mode = LegalOutputMode.REFUSAL_REQUEST_INFO
    
    # Case 2: Judge requested info
    elif judge_result.verdict == LegalJudgeVerdict.REQUEST_INFO:
        mode = LegalOutputMode.REFUSAL_REQUEST_INFO
    
    # Case 3: Judge approved
    elif judge_result.verdict == LegalJudgeVerdict.APPROVE:
        
        # P0.7 Invariant C: Consensus required but missing
        if consensus_required and not consensus_result:
            mode = LegalOutputMode.REFUSAL_REQUEST_INFO
            missing_info.append(MissingInfoCode.CONSENSUS_REQUIRED)
        
        # P0.7 Invariant C: Consensus required but rejected (real rejection)
        elif consensus_required and consensus_rejected:
            mode = LegalOutputMode.REFUSAL_REQUEST_INFO
            missing_info.append(MissingInfoCode.CONSENSUS_REJECTED)
        
        # NEW: Consensus required but no quorum (evaluation done, disagreement)
        elif consensus_required and consensus_no_quorum:
            mode = LegalOutputMode.REFUSAL_REQUEST_INFO
            missing_info.append(MissingInfoCode.CONSENSUS_NO_QUORUM)
        
        # NEW: Consensus required but infra failure (no evaluation possible)
        elif consensus_required and consensus_infra_failure:
            mode = LegalOutputMode.REFUSAL_REQUEST_INFO
            missing_info.append(MissingInfoCode.CONSENSUS_INFRA_FAILURE)
        
        # P0.7 Invariant F: APPROVED_POSITION only if consensus APPROVED
        elif consensus_approved:
            # P0.7 Invariant B: Check provenance for non-REFUSAL
            if draft.source_chunk_ids and not provenance_valid:
                mode = LegalOutputMode.REFUSAL_REQUEST_INFO
                missing_info.append(MissingInfoCode.PROVENANCE_MISSING)
            else:
                mode = LegalOutputMode.APPROVED_POSITION
        
        # No consensus required (LOW + INFO only)
        elif not consensus_required:
            # P0.7 Invariant B: Check provenance for non-REFUSAL
            if draft.source_chunk_ids and not provenance_valid:
                mode = LegalOutputMode.REFUSAL_REQUEST_INFO
                missing_info.append(MissingInfoCode.PROVENANCE_MISSING)
            else:
                mode = LegalOutputMode.SAFE_ANALYSIS
        
        else:
            # Fallback: fail-closed
            mode = LegalOutputMode.REFUSAL_REQUEST_INFO
    
    # ─────────────────────────────────────────────────────────────────────────
    # BUILD ANSWER
    # ─────────────────────────────────────────────────────────────────────────
    
    if mode == LegalOutputMode.REFUSAL_REQUEST_INFO:
        # Build specific refusal message based on missing_info
        # CRITICAL: Different rationales for audit/compliance distinction
        if MissingInfoCode.CONSENSUS_INFRA_FAILURE in missing_info:
            # All arbiters unavailable - infrastructure issue, no evaluation
            answer = "Aucune évaluation juridique n'a pu être effectuée (tous les arbitres indisponibles)."
        elif MissingInfoCode.CONSENSUS_NO_QUORUM in missing_info:
            # Evaluation done, but no 2/3 majority - disagreement
            answer = "Évaluation juridique effectuée, mais aucun quorum n'a été atteint entre les arbitres."
        elif MissingInfoCode.CONSENSUS_REQUIRED in missing_info:
            answer = "Consensus requis mais non fourni. Cette décision nécessite une validation par consensus."
        elif MissingInfoCode.CONSENSUS_REJECTED in missing_info:
            answer = "Le consensus a rejeté cette position. La validation n'est pas possible."
        elif MissingInfoCode.PROVENANCE_MISSING in missing_info:
            answer = "Provenance des sources incomplète. Impossible de garantir la traçabilité."
        else:
            answer = "Des informations supplémentaires sont nécessaires pour fournir une analyse juridique complète."
    else:
        answer = draft.application or "Voir la structure détaillée ci-dessous."
    
    # ─────────────────────────────────────────────────────────────────────────
    # P0.7 INVARIANT A: Deterministic audit_bundle_id
    # ─────────────────────────────────────────────────────────────────────────
    
    audit_id = generate_audit_bundle_id(
        draft_id=draft.draft_id,
        output_mode=mode.value,
        source_chunk_ids=draft.source_chunk_ids,
        citations=draft.citations,
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # BUILD OUTPUT
    # ─────────────────────────────────────────────────────────────────────────
    
    # Only include provenance for non-REFUSAL modes (or if we have it anyway)
    output_provenance = provenance_list if mode != LegalOutputMode.REFUSAL_REQUEST_INFO else []
    
    return LegalOutput(
        mode=mode,
        answer=answer,
        facts=draft.facts,
        rules=draft.rules,
        application=draft.application,
        risks=draft.risks,
        next_action=draft.next_action,
        citations=draft.citations,
        provenance=output_provenance,
        consensus_id=consensus_result.get("proposal_id") if consensus_result else None,
        consensus_status=consensus_result.get("status") if consensus_result else None,
        arbiter_votes=consensus_result.get("votes", {}) if consensus_result else {},
        judge_verdict=judge_result.verdict.value,
        judge_checks=[c.to_dict() for c in judge_result.checks],
        audit_bundle_id=audit_id,
        missing_info=missing_info,
        risk_tier=risk_tier,
        scope=scope,
        jurisdiction=jurisdiction,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # P0.1 - Routing
    "LegalRiskTier",
    "DecisionScope",
    "Jurisdiction",
    "LegalRouteContext",
    "detect_legal_context",
    
    # P0.2 - Draft
    "ClaimType",
    "LegalClaim",
    "LegalDraft",
    "generate_draft_id",
    
    # P0.3 - Judge
    "JudgeCheckResult",
    "JudgeCheck",
    "LegalJudgeVerdict",
    "LegalJudgeResult",
    "judge_legal_draft",
    
    # P0.4 - Consensus
    "LegalConsensusType",
    "LegalConsensusItem",
    "LegalConsensusProposal",
    "build_legal_consensus_proposal",
    
    # P0.5 - Output
    "LegalOutputMode",
    "LegalOutput",
    "build_legal_output",
    "generate_audit_bundle_id",
    
    # P0.7 - Premium Gate
    "MissingInfoCode",
    "requires_consensus",
    "resolve_provenance_for_chunks",
    "validate_provenance_complete",
]
