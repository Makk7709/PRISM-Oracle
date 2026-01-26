"""
Routing Policy — Deterministic rules for intent detection.

This policy defines:
- Weighted keywords per intent (with word boundaries)
- Negative keywords (anti-match)
- Board-level triggers (strategic requests)
- Multi-intent addition rules
- Required intent combinations

NO LLM JUDGMENT. Pure code-driven policy.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum

from .routing_contract import IntentName


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORD DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Keyword:
    """A weighted keyword for intent matching."""
    word: str
    weight: float = 1.0
    use_boundary: bool = True  # Use \b word boundaries
    is_negative: bool = False  # If True, reduces score


@dataclass
class IntentPolicy:
    """Policy for a single intent."""
    
    name: IntentName
    keywords: List[Keyword] = field(default_factory=list)
    min_score_threshold: float = 2.0  # Minimum score to include intent
    is_critical: bool = False  # If True, cannot be skipped when matched
    
    # Negative keywords that block this intent
    blockers: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT POLICIES
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_POLICIES: Dict[IntentName, IntentPolicy] = {
    
    # ─────────────────────────────────────────────────────────────────────────────
    # FINANCE
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.FINANCE: IntentPolicy(
        name=IntentName.FINANCE,
        min_score_threshold=2.5,  # Lowered for better coverage
        keywords=[
            # High weight - very specific
            Keyword("dcf", weight=5.0, use_boundary=False),
            Keyword("ebitda", weight=5.0, use_boundary=False),
            Keyword("valorisation", weight=4.0),
            Keyword("valuation", weight=4.0),
            Keyword("due diligence", weight=4.0),
            Keyword("m&a", weight=4.0, use_boundary=False),
            Keyword("lbo", weight=4.0, use_boundary=False),
            Keyword("irr", weight=4.0, use_boundary=False),
            Keyword("npv", weight=4.0, use_boundary=False),
            Keyword("cash flow", weight=4.0),
            Keyword("flux de trésorerie", weight=4.0),
            # Medium weight
            Keyword("financier", weight=3.0),
            Keyword("financière", weight=3.0),
            Keyword("financial", weight=3.0),
            Keyword("bilan", weight=3.0),
            Keyword("compte de résultat", weight=3.0),
            Keyword("p&l", weight=3.0, use_boundary=False),
            Keyword("investissement", weight=3.0),
            Keyword("investment", weight=3.0),
            Keyword("budget", weight=2.5),
            Keyword("forecast", weight=2.5),
            Keyword("prévisionnel", weight=2.5),
            # Lower weight
            Keyword("coût", weight=2.0),
            Keyword("cost", weight=2.0),
            Keyword("revenue", weight=2.0),
            Keyword("chiffre d'affaires", weight=2.0),
            Keyword("marge", weight=2.0),
            Keyword("margin", weight=2.0),
            Keyword("roi", weight=3.0, use_boundary=False),
            Keyword("calculer", weight=1.5),
            Keyword("analyse financière", weight=4.0),
            Keyword("financial analysis", weight=4.0),
            Keyword("projection", weight=2.5),
        ],
        blockers=["patient", "medical", "diagnostic", "symptom"],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # SALES
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.SALES: IntentPolicy(
        name=IntentName.SALES,
        min_score_threshold=2.5,
        keywords=[
            # High weight
            Keyword("pricing", weight=4.0),
            Keyword("tarification", weight=4.0),
            Keyword("prospect", weight=4.0),
            Keyword("pipeline", weight=4.0),
            Keyword("closing", weight=4.0),
            Keyword("deal", weight=3.5),
            Keyword("négociation", weight=3.5),
            Keyword("negotiation", weight=3.5),
            # Medium weight
            Keyword("vente", weight=3.0),
            Keyword("sales", weight=3.0),
            Keyword("client", weight=2.5),
            Keyword("customer", weight=2.5),
            Keyword("contrat commercial", weight=3.0),
            Keyword("commercial", weight=2.5),
            Keyword("offre", weight=2.0),
            Keyword("proposal", weight=2.5),
            Keyword("quotation", weight=2.5),
            Keyword("devis", weight=2.5),
            # Lower weight
            Keyword("crm", weight=2.0, use_boundary=False),
            Keyword("lead", weight=2.0),
            Keyword("conversion", weight=2.5),
            Keyword("taux de conversion", weight=3.5),
            Keyword("négociation", weight=3.5),
        ],
        blockers=["patient", "medical", "juridique", "tribunal"],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # LEGAL_SAFE
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.LEGAL_SAFE: IntentPolicy(
        name=IntentName.LEGAL_SAFE,
        min_score_threshold=2.5,
        is_critical=True,  # Cannot skip when matched
        keywords=[
            # High weight - very specific legal
            Keyword("tribunal", weight=5.0),
            Keyword("greffe", weight=5.0),
            Keyword("assignation", weight=5.0),
            Keyword("plaidoirie", weight=5.0),
            Keyword("jurisprudence", weight=5.0),
            Keyword("code civil", weight=4.0),
            Keyword("code pénal", weight=4.0),
            Keyword("code du travail", weight=4.0),
            Keyword("mise en demeure", weight=4.0),
            Keyword("contentieux", weight=4.0),
            Keyword("litige", weight=4.0),
            Keyword("prud'hommes", weight=4.0),
            # Medium weight
            Keyword("juridique", weight=3.5),
            Keyword("legal", weight=3.5),
            Keyword("avocat", weight=3.5),
            Keyword("contrat", weight=3.0),
            Keyword("clause", weight=3.0),
            Keyword("rgpd", weight=3.0, use_boundary=False),
            Keyword("gdpr", weight=3.0, use_boundary=False),
            Keyword("conformité", weight=3.0),
            Keyword("compliance", weight=3.0),
            Keyword("cession", weight=3.0),
            Keyword("responsabilité", weight=3.0),
            Keyword("liability", weight=3.0),
            # Lower weight
            Keyword("droit", weight=2.0),
            Keyword("law", weight=2.0),
            Keyword("règlement", weight=2.0),
            Keyword("statuts", weight=2.5),
            Keyword("non-concurrence", weight=4.0),
            Keyword("non concurrence", weight=4.0),
        ],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # MEDICAL
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.MEDICAL: IntentPolicy(
        name=IntentName.MEDICAL,
        min_score_threshold=3.0,
        is_critical=True,
        keywords=[
            # High weight - clearly medical
            Keyword("diagnostic", weight=5.0),
            Keyword("diagnosis", weight=5.0),
            Keyword("patient", weight=4.0),
            Keyword("traitement", weight=4.0),
            Keyword("treatment", weight=4.0),
            Keyword("médicament", weight=4.0),
            Keyword("drug", weight=4.0),
            Keyword("posologie", weight=5.0),
            Keyword("dosage", weight=4.0),
            Keyword("effet secondaire", weight=5.0),
            Keyword("side effect", weight=5.0),
            Keyword("ordonnance", weight=4.0),
            Keyword("prescription", weight=4.0),
            # Medium weight
            Keyword("médical", weight=3.5),
            Keyword("medical", weight=3.5),
            Keyword("clinique", weight=3.5),
            Keyword("clinical", weight=3.5),
            Keyword("symptôme", weight=3.5),
            Keyword("symptom", weight=3.5),
            Keyword("maladie", weight=3.0),
            Keyword("disease", weight=3.0),
            Keyword("pathologie", weight=3.5),
            Keyword("essai clinique", weight=4.0),
            Keyword("clinical trial", weight=4.0),
        ],
        # Block medical when context is clearly business
        blockers=["saas", "software", "startup", "marketing campaign", "pricing strategy"],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # DEVELOPER
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.DEVELOPER: IntentPolicy(
        name=IntentName.DEVELOPER,
        min_score_threshold=2.5,
        keywords=[
            # High weight
            Keyword("code", weight=3.0),
            Keyword("bug", weight=4.0),
            Keyword("debug", weight=4.0),
            Keyword("api", weight=3.5, use_boundary=False),
            Keyword("backend", weight=3.5),
            Keyword("frontend", weight=3.5),
            Keyword("database", weight=3.5),
            Keyword("deploy", weight=3.5),
            Keyword("docker", weight=4.0),
            Keyword("kubernetes", weight=4.0),
            Keyword("git", weight=3.0),
            # Medium weight
            Keyword("développement", weight=3.0),
            Keyword("development", weight=3.0),
            Keyword("programming", weight=3.0),
            Keyword("script", weight=2.5),
            Keyword("function", weight=2.0),
            Keyword("class", weight=2.0),
            Keyword("module", weight=2.0),
            Keyword("refactor", weight=3.5),
            Keyword("refactoring", weight=3.5),
            Keyword("test", weight=2.0),
            Keyword("ci/cd", weight=3.5, use_boundary=False),
            Keyword("module", weight=2.5),
        ],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # RESEARCHER
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.RESEARCHER: IntentPolicy(
        name=IntentName.RESEARCHER,
        min_score_threshold=3.0,
        is_critical=True,
        keywords=[
            # High weight
            Keyword("recherche", weight=3.5),
            Keyword("research", weight=3.5),
            Keyword("étude", weight=3.0),
            Keyword("study", weight=3.0),
            Keyword("scientifique", weight=4.0),
            Keyword("scientific", weight=4.0),
            Keyword("peer review", weight=5.0),
            Keyword("publication", weight=3.5),
            Keyword("paper", weight=3.0),
            Keyword("méthodologie", weight=4.0),
            Keyword("methodology", weight=4.0),
            Keyword("hypothesis", weight=4.0),
            Keyword("hypothèse", weight=4.0),
            Keyword("abstract", weight=3.5),
            Keyword("literature review", weight=4.0),
            Keyword("meta-analysis", weight=5.0),
            Keyword("méta-analyse", weight=5.0),
        ],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # MARKETING
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.MARKETING: IntentPolicy(
        name=IntentName.MARKETING,
        min_score_threshold=3.0,
        keywords=[
            # High weight
            Keyword("marketing", weight=4.0),
            Keyword("campagne", weight=3.5),
            Keyword("campaign", weight=3.5),
            Keyword("branding", weight=4.0),
            Keyword("marque", weight=3.0),
            Keyword("brand", weight=3.0),
            Keyword("seo", weight=4.0, use_boundary=False),
            Keyword("sem", weight=3.5, use_boundary=False),
            Keyword("content", weight=2.5),
            Keyword("contenu", weight=2.5),
            Keyword("social media", weight=3.5),
            Keyword("réseaux sociaux", weight=3.5),
            Keyword("linkedin", weight=3.0),
            Keyword("audience", weight=3.0),
            Keyword("engagement", weight=3.0),
            Keyword("acquisition", weight=2.5),  # Can be M&A too
            Keyword("growth", weight=2.5),
            Keyword("croissance", weight=2.5),
        ],
        blockers=["tribunal", "juridique", "patient"],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # MULTITASK (fallback)
    # ─────────────────────────────────────────────────────────────────────────────
    IntentName.MULTITASK: IntentPolicy(
        name=IntentName.MULTITASK,
        min_score_threshold=0.0,  # Always available as fallback
        keywords=[
            # General keywords
            Keyword("aide", weight=1.0),
            Keyword("help", weight=1.0),
            Keyword("question", weight=1.0),
            Keyword("explain", weight=1.0),
            Keyword("expliquer", weight=1.0),
        ],
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# BOARD-LEVEL TRIGGERS
# ═══════════════════════════════════════════════════════════════════════════════

# Keywords that trigger board-level mode (strategic decisions)
BOARD_LEVEL_KEYWORDS: List[Keyword] = [
    # Strategic
    Keyword("stratégie", weight=4.0),
    Keyword("strategy", weight=4.0),
    Keyword("stratégique", weight=4.0),
    Keyword("strategic", weight=4.0),
    
    # High-stakes decisions
    Keyword("acquisition", weight=4.0),
    Keyword("merger", weight=4.0),
    Keyword("fusion", weight=4.0),
    Keyword("ipo", weight=5.0, use_boundary=False),
    Keyword("levée de fonds", weight=4.0),
    Keyword("fundraising", weight=4.0),
    Keyword("série a", weight=4.0),
    Keyword("series a", weight=4.0),
    
    # Board/Comex
    Keyword("board", weight=3.5),
    Keyword("comité", weight=3.0),
    Keyword("comex", weight=4.0),
    Keyword("direction", weight=3.0),
    Keyword("roadmap", weight=3.0),
    
    # Critical decisions
    Keyword("recommandation", weight=3.0),
    Keyword("recommendation", weight=3.0),
    Keyword("décision", weight=2.5),
    Keyword("decision", weight=2.5),
    Keyword("décision critique", weight=5.0),
    Keyword("critical decision", weight=5.0),
    Keyword("investissement majeur", weight=4.0),
    Keyword("major investment", weight=4.0),
    Keyword("investissement", weight=2.0),
    Keyword("investment", weight=2.0),
    
    # Risk
    Keyword("risque majeur", weight=4.0),
    Keyword("major risk", weight=4.0),
    Keyword("critical", weight=3.0),
    Keyword("critique", weight=3.0),
]

# Score threshold for board-level activation
BOARD_LEVEL_THRESHOLD: float = 6.0

# Core intents for board-level requests
BOARD_LEVEL_CORE_INTENTS: Set[IntentName] = {
    IntentName.FINANCE,
    IntentName.SALES,
    IntentName.LEGAL_SAFE,
}


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-INTENT RULES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MultiIntentRule:
    """Rule for adding intents based on combinations."""
    if_intents: Set[IntentName]  # If these intents are present
    add_intent: IntentName       # Add this intent
    condition: str = "all"       # "all" or "any"
    reason: str = ""


MULTI_INTENT_RULES: List[MultiIntentRule] = [
    # Finance + Legal => might need Sales for commercial context
    MultiIntentRule(
        if_intents={IntentName.FINANCE, IntentName.LEGAL_SAFE},
        add_intent=IntentName.SALES,
        condition="all",
        reason="Finance+Legal often involves commercial negotiation",
    ),
    
    # Any board-level with Finance => add Legal for compliance check
    MultiIntentRule(
        if_intents={IntentName.FINANCE},
        add_intent=IntentName.LEGAL_SAFE,
        condition="all",
        reason="Financial decisions require legal review",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# ANTI-INJECTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns that indicate prompt injection attempt
INJECTION_PATTERNS: List[str] = [
    r"ignore.*rules?",
    r"ignore.*instructions?",
    r"ignore\s+all",
    r"forget.*previous",
    r"forget.*your.*instructions",
    r"bypass.*policy",
    r"don't.*call.*legal",
    r"ne.*pas.*appeler",
    r"skip.*agent",
    r"skip.*legal",
    r"route.*to.*hacker",
    r"direct.*to.*developer",
    r"override.*routing",
    r"system.*prompt",
    r"you.*are.*now",
    r"act.*as.*if",
    r"pretend.*you",
    r"just.*do.*what.*i.*say",
]


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY VERSION
# ═══════════════════════════════════════════════════════════════════════════════

POLICY_VERSION = "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "Keyword",
    "IntentPolicy",
    "MultiIntentRule",
    "INTENT_POLICIES",
    "BOARD_LEVEL_KEYWORDS",
    "BOARD_LEVEL_THRESHOLD",
    "BOARD_LEVEL_CORE_INTENTS",
    "MULTI_INTENT_RULES",
    "INJECTION_PATTERNS",
    "POLICY_VERSION",
]
