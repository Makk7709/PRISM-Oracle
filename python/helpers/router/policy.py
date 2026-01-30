"""
Routing Policy — Deterministic rules for intent detection.

This policy defines:
- Weighted keywords per intent (with word boundaries)
- Negative keywords (anti-match)
- Board-level triggers (strategic requests)
- Multi-intent addition rules
- Required intent combinations

NO LLM JUDGMENT. Pure code-driven policy.

VERSION NOTES:
- v1.1.0: Fixed acquisition collision (marketing vs M&A)
- v1.1.0: Finance->Legal rule now requires board-level
- v1.1.0: Injection patterns reduced to override-only
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
        min_score_threshold=2.5,
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
        ],
        blockers=["patient", "medical"],  # Removed juridique/tribunal - can have commercial+legal
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
            Keyword("loi française", weight=4.0, use_boundary=False),
            Keyword("loi sur", weight=3.0, use_boundary=False),
            Keyword("contractuel", weight=3.0),
            Keyword("contractuelles", weight=3.0),
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
            Keyword("module", weight=2.5),
            Keyword("refactor", weight=3.5),
            Keyword("refactoring", weight=3.5),
            Keyword("test", weight=2.0),
            Keyword("ci/cd", weight=3.5, use_boundary=False),
        ],
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # RESEARCHER
    # ─────────────────────────────────────────────────────────────────────────────
    # TODO P1: Recalibrate is_critical for RESEARCHER - may cause over-blocking
    IntentName.RESEARCHER: IntentPolicy(
        name=IntentName.RESEARCHER,
        min_score_threshold=3.0,
        is_critical=True,  # TODO P1: Review if this should remain critical
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
            # Marketing acquisition (NOT M&A)
            Keyword("user acquisition", weight=4.0, use_boundary=False),
            Keyword("customer acquisition", weight=4.0, use_boundary=False),
            Keyword("acquisition seo", weight=4.0, use_boundary=False),
            Keyword("acquisition client", weight=3.5, use_boundary=False),
            Keyword("acquisition utilisateurs", weight=4.0, use_boundary=False),
            Keyword("acquisition utilisateur", weight=4.0, use_boundary=False),
            Keyword("growth hacking", weight=4.0, use_boundary=False),
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
# NOTE: "acquisition" alone removed - too ambiguous (marketing vs M&A)
# Use specific M&A phrases instead
BOARD_LEVEL_KEYWORDS: List[Keyword] = [
    # Strategic
    Keyword("stratégie", weight=4.0),
    Keyword("strategy", weight=4.0),
    Keyword("stratégique", weight=4.0),
    Keyword("strategic", weight=4.0),
    
    # M&A specific (NOT generic "acquisition")
    # Use use_boundary=False for phrases with apostrophes/special chars
    Keyword("acquisition d'entreprise", weight=6.0, use_boundary=False),
    Keyword("acquisition d'une entreprise", weight=6.0, use_boundary=False),
    Keyword("acquisition d'une société", weight=6.0, use_boundary=False),
    Keyword("company acquisition", weight=6.0, use_boundary=False),
    Keyword("buyout", weight=6.0),
    Keyword("takeover", weight=6.0),
    Keyword("term sheet", weight=6.0, use_boundary=False),
    Keyword("letter of intent", weight=5.0, use_boundary=False),
    Keyword("fusion-acquisition", weight=6.0, use_boundary=False),
    Keyword("merger", weight=5.0),
    Keyword("fusion", weight=5.0),
    Keyword("m&a", weight=6.0, use_boundary=False),
    Keyword("lbo", weight=6.0, use_boundary=False),
    Keyword("ipo", weight=6.0, use_boundary=False),
    
    # Due diligence (strategic process, not generic research)
    Keyword("due diligence", weight=5.0, use_boundary=False),
    Keyword("due dil", weight=4.0, use_boundary=False),  # Common abbrev
    
    # Shareholder agreements / governance
    Keyword("pacte d'actionnaires", weight=5.0, use_boundary=False),
    Keyword("shareholders agreement", weight=5.0, use_boundary=False),
    Keyword("shareholder agreement", weight=5.0, use_boundary=False),
    Keyword("governance board", weight=4.0, use_boundary=False),
    
    # Joint ventures
    Keyword("joint venture", weight=5.0, use_boundary=False),
    Keyword("joint-venture", weight=5.0, use_boundary=False),
    Keyword("jv agreement", weight=4.0, use_boundary=False),
    
    # Asset sales / divestitures
    Keyword("cession de filiale", weight=5.0, use_boundary=False),
    Keyword("cession filiale", weight=5.0, use_boundary=False),
    Keyword("cession d'actifs", weight=5.0, use_boundary=False),
    Keyword("asset sale", weight=4.0, use_boundary=False),
    Keyword("divestiture", weight=5.0),
    Keyword("carve-out", weight=5.0, use_boundary=False),
    Keyword("spin-off", weight=5.0, use_boundary=False),
    
    # Restructuring (with governance context)
    Keyword("restructuration plan", weight=4.0, use_boundary=False),
    Keyword("plan de restructuration", weight=5.0, use_boundary=False),
    Keyword("restructuration stratégique", weight=5.0, use_boundary=False),
    Keyword("pse", weight=4.0),  # Plan de Sauvegarde de l'Emploi
    
    # Fundraising
    Keyword("levée de fonds", weight=4.0),
    Keyword("fundraising", weight=4.0),
    Keyword("série a", weight=4.0),
    Keyword("series a", weight=4.0),
    Keyword("série b", weight=4.0),
    Keyword("series b", weight=4.0),
    
    # Board/Comex
    Keyword("board", weight=3.5),
    Keyword("comité", weight=3.0),
    Keyword("comex", weight=4.0),
    Keyword("direction générale", weight=4.0),
    Keyword("executive committee", weight=4.0),
    Keyword("roadmap stratégique", weight=4.0),
    
    # Critical decisions
    Keyword("recommandation stratégique", weight=4.0),
    Keyword("strategic recommendation", weight=4.0),
    Keyword("décision critique", weight=5.0),
    Keyword("critical decision", weight=5.0),
    Keyword("investissement majeur", weight=4.0),
    Keyword("major investment", weight=4.0),
    
    # Risk
    Keyword("risque majeur", weight=4.0),
    Keyword("major risk", weight=4.0),
    Keyword("risque stratégique", weight=4.0),
    Keyword("strategic risk", weight=4.0),
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
    require_board_level: bool = False  # If True, only apply when is_board_level


MULTI_INTENT_RULES: List[MultiIntentRule] = [
    # Finance + Legal => might need Sales for commercial context
    # This rule does NOT require board-level
    MultiIntentRule(
        if_intents={IntentName.FINANCE, IntentName.LEGAL_SAFE},
        add_intent=IntentName.SALES,
        condition="all",
        reason="Finance+Legal often involves commercial negotiation",
        require_board_level=False,
    ),
    
    # Finance => add Legal ONLY for board-level decisions
    # This prevents over-routing legal for simple finance queries
    MultiIntentRule(
        if_intents={IntentName.FINANCE},
        add_intent=IntentName.LEGAL_SAFE,
        condition="all",
        reason="Board-level financial decisions require legal review",
        require_board_level=True,  # CRITICAL: Only apply when board-level
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# ANTI-INJECTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns that indicate prompt injection attempt
# REDUCED to override/disable patterns only - no benign roleplay patterns
INJECTION_PATTERNS: List[str] = [
    # Override/disable instructions (English)
    r"ignore\s+all\s+instructions?",
    r"ignore\s+all\s+rules?",
    r"ignore\s+instructions",
    r"ignore\s+previous\s+instructions?",
    r"bypass\s+policy",
    r"bypass\s+routing",
    r"override\s+routing",
    r"override\s+policy",
    
    # Override/disable instructions (French)
    r"ignore\s+toutes?\s+(tes|les|mes)\s+r[eè]gles?",
    r"ignore\s+toutes?\s+(tes|les|mes)\s+instructions?",
    r"oublie\s+(tes|les|mes)\s+instructions?",
    
    # Disable specific agents
    r"don't\s+call\s+legal",
    r"do\s+not\s+call\s+legal",
    r"ne\s+pas\s+appeler\s+legal",
    r"ne\s+pas\s+appeler\s+juridique",
    r"skip\s+legal",
    r"skip\s+agent",
    r"désactiver\s+legal",
    r"disable\s+legal",
    
    # Forget/reset instructions
    r"forget\s+your\s+instructions",
    r"forget\s+previous\s+instructions",
    r"reset\s+your\s+instructions",
    
    # Explicit attack patterns
    r"route\s+to\s+hacker",
    r"just\s+do\s+what\s+i\s+say",
]

# NOTE: The following patterns are NOT injection (benign roleplay):
# - "act as my lawyer" -> legitimate legal request
# - "pretend you are an expert" -> role instruction
# - "you are now a consultant" -> persona instruction
# - "system prompt" -> could be legitimate discussion
# These are moved out of INJECTION_PATTERNS to avoid false positives.


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGIC DOCUMENT KEYWORDS (force HIGH criticality + multi-agent)
# ═══════════════════════════════════════════════════════════════════════════════

# These keywords trigger strategic document detection
# When matched, the request becomes HIGH criticality with mandatory agents
STRATEGIC_DOCUMENT_KEYWORDS: List[Keyword] = [
    # Market Study
    Keyword("étude de marché", weight=6.0, use_boundary=False),
    Keyword("market study", weight=6.0, use_boundary=False),
    Keyword("market analysis", weight=5.0, use_boundary=False),
    Keyword("analyse du marché", weight=5.0, use_boundary=False),
    Keyword("tam", weight=4.0),  # Total Addressable Market
    Keyword("sam", weight=4.0),  # Serviceable Available Market
    Keyword("som", weight=4.0),  # Serviceable Obtainable Market
    Keyword("taille du marché", weight=5.0, use_boundary=False),
    Keyword("market size", weight=5.0, use_boundary=False),
    
    # Financial Forecast
    Keyword("prévisionnel", weight=5.0),
    Keyword("financial forecast", weight=5.0, use_boundary=False),
    Keyword("projection financière", weight=5.0, use_boundary=False),
    Keyword("p&l", weight=4.0, use_boundary=False),
    Keyword("compte de résultat prévisionnel", weight=6.0, use_boundary=False),
    Keyword("break-even", weight=4.0, use_boundary=False),
    Keyword("point mort", weight=4.0, use_boundary=False),
    
    # Pricing
    Keyword("stratégie de prix", weight=5.0, use_boundary=False),
    Keyword("pricing strategy", weight=5.0, use_boundary=False),
    Keyword("modèle économique", weight=4.0, use_boundary=False),
    Keyword("business model", weight=4.0, use_boundary=False),
    Keyword("unit economics", weight=5.0, use_boundary=False),
    
    # GTM
    Keyword("go-to-market", weight=5.0, use_boundary=False),
    Keyword("go to market", weight=5.0, use_boundary=False),
    Keyword("gtm", weight=4.0),
    Keyword("stratégie de lancement", weight=5.0, use_boundary=False),
    Keyword("launch strategy", weight=5.0, use_boundary=False),
    
    # Competitive Analysis
    Keyword("analyse concurrentielle", weight=5.0, use_boundary=False),
    Keyword("competitive analysis", weight=5.0, use_boundary=False),
    Keyword("benchmark concurrentiel", weight=5.0, use_boundary=False),
    
    # Business Plan
    Keyword("business plan", weight=5.0, use_boundary=False),
    Keyword("plan d'affaires", weight=5.0, use_boundary=False),
]

# Threshold for strategic document detection
STRATEGIC_DOCUMENT_THRESHOLD: float = 4.0


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY VERSION
# ═══════════════════════════════════════════════════════════════════════════════

POLICY_VERSION = "1.2.0"  # Updated for strategic document support


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
    # Strategic documents
    "STRATEGIC_DOCUMENT_KEYWORDS",
    "STRATEGIC_DOCUMENT_THRESHOLD",
]
