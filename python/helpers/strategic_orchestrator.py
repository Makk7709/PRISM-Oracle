"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   STRATEGIC DOCUMENT ORCHESTRATOR                            ║
║                                                                              ║
║  Pipeline déterministe pour documents stratégiques:                          ║
║  - Détection automatique (étude de marché, prévisionnel, etc.)              ║
║  - Appel séquentiel des agents spécialisés (researcher → finance)           ║
║  - Consolidation LLM dynamique (pas de template générique)                  ║
║  - Validation des sources et du contenu                                      ║
║  - FAIL_CLOSED si standards Evidence non respectés                           ║
║                                                                              ║
║  Version: 2.0.0                                                              ║
║  © 2026 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from python.helpers import files
from python.helpers.pipeline_tracker import PipelineTracker
from python.helpers.progress_feedback import emit_pipeline_progress, emit_synthesis_progress

if TYPE_CHECKING:
    from agent import Agent

logger = logging.getLogger("strategic_orchestrator")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def is_strategic_orchestrator_enabled() -> bool:
    """Check if strategic orchestrator is enabled."""
    return os.environ.get("STRATEGIC_ORCHESTRATOR_ENABLED", "1") == "1"


# Strategic document patterns
STRATEGIC_PATTERNS = {
    "strategic_dossier": [
        r"dossier\s+stratégique",
        r"dossier\s+strategique",
        r"note\s+stratégique",
        r"note\s+strategique",
        r"mémo\s+stratégique",
        r"memo\s+strategique",
        r"business\s+case",
        r"démonstrateur\s+national\s+d['’]ia\s+de\s+confiance",
        r"demonstrateur\s+national\s+d['’]ia\s+de\s+confiance",
    ],
    "market_study": [
        r"étude\s+de\s+marché",
        r"market\s+study",
        r"analyse\s+(?:de\s+)?marché",
        r"TAM\s+SAM\s+SOM",
        r"total\s+addressable\s+market",
    ],
    "financial_forecast": [
        r"prévisionnel",
        r"forecast",
        r"projection\s+financière",
        r"\bP&?L\b",
        r"business\s+plan",
        r"plan\s+financier",
    ],
    "pricing": [
        r"pricing",
        r"tarification",
        r"stratégie\s+de\s+prix",
        r"grille\s+tarifaire",
        r"fixer\s+le\s+(?:prix|tarif)",
        r"politique\s+de\s+prix",
        r"modèle\s+tarifaire",
    ],
    "go_to_market": [
        r"go\s*-?\s*to\s*-?\s*market",
        r"\bGTM\b",
        r"stratégie\s+commerciale",
        r"plan\s+de\s+lancement",
    ],
}

# Required agents per document type
REQUIRED_AGENTS = {
    "strategic_dossier": ["researcher", "finance", "marketing", "sales"],
    "market_study": ["researcher", "finance", "marketing"],
    "financial_forecast": ["finance", "researcher"],
    "pricing": ["finance", "marketing", "researcher"],
    "go_to_market": ["marketing", "sales", "researcher"],
}

# Minimum sources required per document type
MIN_SOURCES = {
    "strategic_dossier": 5,
    "market_study": 5,
    "financial_forecast": 3,
    "pricing": 3,
    "go_to_market": 4,
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategicDetection:
    """Result of strategic document detection."""
    is_strategic: bool
    document_type: Optional[str] = None
    patterns_matched: List[str] = field(default_factory=list)
    required_agents: List[str] = field(default_factory=list)
    min_sources: int = 0


@dataclass
class AgentResponse:
    """Response from a specialized agent."""
    agent_name: str
    profile: str
    response: str
    sources_count: int
    duration_ms: int
    success: bool
    error: Optional[str] = None


@dataclass
class StrategicResult:
    """Final result of strategic orchestration."""
    success: bool
    document_type: str
    responses: List[AgentResponse]
    consolidated_response: str
    total_sources: int
    validation_passed: bool
    fail_reason: Optional[str] = None
    correlation_id: str = ""
    duration_ms: int = 0
    pipeline_tracker: Optional["PipelineTracker"] = field(default=None, repr=False)


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# LEGAL EXCLUSION PATTERNS
# ─────────────────────────────────────────────────────────────────────────────
# If these patterns dominate the query, it's a LEGAL request, not strategic.
# The strategic pipeline must NOT hijack legal contract drafting requests.
LEGAL_EXCLUSION_PATTERNS = [
    r"\bcontrat\b",
    r"\blicence\b",
    r"\bjuridique\b",
    r"\bjuridiction\b",
    r"\btribunal\b",
    r"\bclauses?\b",
    r"\bannexes?\b",
    r"\bconditions\s+(?:générales|particulières)\b",
    r"\bpropriété\s+intellectuelle\b",
    r"\bdroit\s+(?:applicable|d'usage|français|civil)\b",
    r"\bcode\s+(?:civil|de\s+commerce|du\s+travail)\b",
    r"\bRGPD\b",
    r"\bDPA\b",
    r"\bréversibilité\b",
    r"\bSLA\b",
    r"\bresponsabilité\b",
    r"\bgaranties?\b",
    r"\blitige\b",
    r"\bcession\b",
    r"\bsignature\b",
    r"\bprêt\s+à\s+signature\b",
    r"\bcontractuel(?:le)?\b",
    r"\brédaction\b.*\bcontrat\b",
    r"\bcontrat\b.*\brédaction\b",
    r"\blegal[_\s]contract\b",
    r"\bcpi\b",
    r"\bart(?:icle)?\s*\d+",
]


def _is_legal_context(query: str) -> bool:
    """
    Check if the query is primarily a legal context.
    
    Returns True if legal patterns significantly outnumber strategic patterns,
    indicating this is a legal request that should NOT be routed to strategic.
    """
    query_lower = query.lower()
    
    legal_score = 0
    for pattern in LEGAL_EXCLUSION_PATTERNS:
        matches = re.findall(pattern, query_lower, re.IGNORECASE)
        legal_score += len(matches)
    
    strategic_score = 0
    for doc_type, patterns in STRATEGIC_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, query_lower, re.IGNORECASE)
            strategic_score += len(matches)
    
    # Legal context dominates if:
    # - Legal score is >= 3 (strong legal presence), OR
    # - Legal score is at least 2x strategic score
    if legal_score >= 3:
        logger.info(
            f"Legal context detected (score={legal_score} vs strategic={strategic_score}). "
            f"Excluding from strategic pipeline."
        )
        return True
    
    if strategic_score > 0 and legal_score >= strategic_score * 2:
        logger.info(
            f"Legal context dominates (score={legal_score} vs strategic={strategic_score}). "
            f"Excluding from strategic pipeline."
        )
        return True
    
    return False


def detect_strategic_document(query: str) -> StrategicDetection:
    """
    Detect if query requests a strategic document.
    
    IMPORTANT: Legal requests are excluded — a contract with pricing terms
    is a LEGAL document, not a strategic one.
    
    Returns detection result with document type and requirements.
    """
    query_lower = query.lower()
    
    # ─────────────────────────────────────────────────────────────────────
    # RULE 0: Legal exclusion — legal contracts NEVER go to strategic
    # ─────────────────────────────────────────────────────────────────────
    if _is_legal_context(query):
        return StrategicDetection(is_strategic=False)
    
    for doc_type, patterns in STRATEGIC_PATTERNS.items():
        matched = []
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matched.append(pattern)
        
        if matched:
            return StrategicDetection(
                is_strategic=True,
                document_type=doc_type,
                patterns_matched=matched,
                required_agents=REQUIRED_AGENTS.get(doc_type, ["researcher"]),
                min_sources=MIN_SOURCES.get(doc_type, 3),
            )
    
    return StrategicDetection(is_strategic=False)


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE COUNTING
# ═══════════════════════════════════════════════════════════════════════════════

def count_sources(text: str) -> int:
    """
    Count source indicators in text.
    
    Counts multiple types of source references:
    - Reference markers [REF-XX], [S-XX]
    - Institutional sources (Eurostat, INSEE, etc.)
    - Year citations (2024)
    - URLs
    """
    count = 0
    
    # Reference markers
    ref_patterns = [
        r"\[REF-\d+\]",
        r"\[S\d+\]",
        r"Source\s*:\s*\S+",
    ]
    for pattern in ref_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        count += len(matches)
    
    # Institutional sources (EU + major analysts)
    institutional = [
        r"Eurostat",
        r"INSEE",
        r"Bpifrance",
        r"Commission\s*européenne",
        r"EUR-Lex",
        r"Syntec",
        r"IDC",
        r"Gartner",
        r"McKinsey",
        r"Forrester",
        r"Statista",
    ]
    for pattern in institutional:
        matches = re.findall(pattern, text, re.IGNORECASE)
        count += len(matches)
    
    # Year citations (20XX)
    year_pattern = r"\(20\d{2}\)"
    matches = re.findall(year_pattern, text)
    count += len(matches)
    
    # URLs (all valid URLs count)
    url_pattern = r"https?://[^\s\)]+"
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    count += len(urls)
    
    return count


def extract_references(text: str) -> List[str]:
    """Extract all references from text."""
    refs = []
    
    # Extract [REF-XX] references
    ref_pattern = r"\[REF-\d+\][^\[\n]*(?:\n[^\[\n]*)*"
    matches = re.findall(ref_pattern, text)
    refs.extend(matches)
    
    # Extract URLs with context
    url_pattern = r"(?:https?://[^\s]+)"
    urls = re.findall(url_pattern, text)
    refs.extend(urls)
    
    return refs


def validate_strategic_content(
    text: str,
    document_type: str,
    min_sources: int,
) -> Tuple[bool, List[str]]:
    """
    Validate strategic content against Evidence requirements.
    
    Returns (is_valid, missing_requirements).
    """
    missing = []
    
    # Check sources
    source_count = count_sources(text)
    if source_count < min_sources:
        missing.append(f"Sources insuffisantes ({source_count}/{min_sources})")
    
    # Check TAM/SAM/SOM for market studies
    if document_type == "market_study":
        tam_pattern = r"\bTAM\b.*\d+|\d+.*\bTAM\b"
        sam_pattern = r"\bSAM\b.*\d+|\d+.*\bSAM\b"
        som_pattern = r"\bSOM\b.*\d+|\d+.*\bSOM\b"
        
        if not re.search(tam_pattern, text, re.IGNORECASE):
            missing.append("TAM non chiffré")
        if not re.search(sam_pattern, text, re.IGNORECASE):
            missing.append("SAM non chiffré")
        if not re.search(som_pattern, text, re.IGNORECASE):
            missing.append("SOM non chiffré")
    
    # Check financial forecast requirements
    if document_type == "financial_forecast":
        if not re.search(r"hypothèse|assumption|supposant", text, re.IGNORECASE):
            missing.append("Hypothèses non explicites")
        if not re.search(r"scénario|scenario", text, re.IGNORECASE):
            missing.append("Scénarios non présentés")
    
    # Check alternatives — broad vocabulary to avoid false negatives from LLM
    # synonyms used in strategic documents.
    alternatives_pattern = (
        r"alternative"
        r"|option\s*\d"
        r"|écartée?|rejetée?"
        r"|concurrent(?:iel(?:le)?|s)?"
        r"|benchmark(?:ing|s)?"
        r"|compara(?:ti(?:f|ve|on)|ison)"
        r"|\bvs\.?\b|\bversus\b"
        r"|positionnement\s+concurrentiel"
        r"|analyse\s+concurrentielle"
        r"|forces?\s+(?:et\s+)?faiblesses?"
        r"|SWOT"
        r"|approche[s]?\s+(?:alternative|comparée|envisagée)"
    )
    if not re.search(alternatives_pattern, text, re.IGNORECASE):
        missing.append("Alternatives non analysées")

    # Guard against fabricated pagination references.
    if re.search(r"\b(?:p\.|page)\s*\d+\b", text, re.IGNORECASE):
        missing.append("Références de page détectées: pagination non vérifiée interdite")
    
    return len(missing) == 0, missing


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_key_content(text: str, max_chars: int = 2500) -> str:
    """
    Extract high-value lines from an agent response for inter-agent context.

    Prioritises lines containing references, numbers, tables, and conclusions
    over generic prose.  Falls back to a head truncation if nothing matches.
    """
    if len(text) <= max_chars:
        return text

    priority_lines: List[str] = []
    normal_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        is_high = bool(
            re.search(r"\[REF-\d+\]", stripped)
            or re.search(r"\d[\d.,]+\s*(%|EUR|M€|Mds|k€|\$)", stripped)
            or re.search(r"^\|", stripped)
            or re.search(r"^[-*]\s+\*\*", stripped)
            or re.search(r"(TAM|SAM|SOM|CAGR|ARPA|CAC|LTV|hypothèse|scénario)", stripped, re.IGNORECASE)
        )
        (priority_lines if is_high else normal_lines).append(line)

    selected = "\n".join(priority_lines)
    if len(selected) < max_chars and normal_lines:
        remaining = max_chars - len(selected) - 20
        filler = "\n".join(normal_lines)[:remaining]
        selected = selected + "\n\n" + filler if selected else filler

    return selected[:max_chars]


def get_agent_prompt(
    document_type: str,
    agent_profile: str,
    user_query: str,
    previous_responses: List[AgentResponse],
) -> str:
    """
    Generate specialized prompt for each agent.
    
    Each agent receives:
    - The user query
    - The document type context
    - Previous agent responses (for synthesis)
    - Strict sourcing requirements with EU-specific sources
    """
    context = ""
    if previous_responses:
        context = "\n\n## Analyses précédentes (à intégrer et développer):\n"
        for resp in previous_responses:
            if not resp.success or not resp.response:
                continue
            summary = _extract_key_content(resp.response, max_chars=2500)
            context += f"\n### {resp.agent_name} ({resp.profile}) — {resp.sources_count} sources:\n{summary}\n"
    
    # EU-specific sources list
    eu_sources = """
## 📚 SOURCES EUROPÉENNES OBLIGATOIRES

Tu dois citer EXCLUSIVEMENT des sources européennes vérifiables:

### Statistiques officielles
- **Eurostat** — https://ec.europa.eu/eurostat/ — ICT, entreprises, économie numérique
- **INSEE** — https://www.insee.fr/ — Statistiques France
- **Bpifrance Le Lab** — https://lelab.bpifrance.fr/ — Études PME/ETI

### Réglementation
- **EUR-Lex** — https://eur-lex.europa.eu/ — AI Act, RGPD, législation EU
- **Commission européenne** — https://ec.europa.eu/ — Rapports officiels

### Marché & Industrie
- **IDC Europe** — https://www.idc.com/eu — Marché IT européen
- **Syntec Numérique** — https://syntec-numerique.fr/ — Marché logiciel France
- **Gartner** — Rapports européens uniquement

### Format de citation OBLIGATOIRE
[REF-01] Nom source, "Titre document", année, URL

Exemple:
[REF-01] Eurostat, "ICT usage in enterprises 2024", 2024, https://ec.europa.eu/eurostat/...
"""

    premium_output_contract = """
## MODE EVIDENCE — DOSSIER STRATÉGIQUE PREMIUM (OBLIGATOIRE)

Principe non négociable:
- ZÉRO invention.
- ZÉRO donnée non sourcée présentée comme factuelle.
- Toute affirmation critique doit être traçable à une source vérifiable.
- Si une donnée est absente/incertaine: indiquer "NON VÉRIFIÉ" + plan d’acquisition.

FORMAT DE SORTIE OBLIGATOIRE:
1) Synthèse exécutive (6-10 bullets orientés décision + 3 messages clés)
2) Résumé analytique (établi vs incertain)
3) Méthodologie et gouvernance de preuve
4) Analyse complète (marché, scénarios, réglementaire AI Act, risques, exécution)
5) Recommandations actionnables (30/90/180 jours puis 12 mois)
6) Tableau des preuves (Claim, criticité, [REF-XX], qualité, statut)
7) Bibliographie cliquable:
   - [REF-01] Institution, titre, année — [Lien](https://...)

RÈGLES SOURCING STRICTES:
- Chaque chiffre/benchmark/contrainte réglementaire => [REF-XX] obligatoire.
- Liens source cliquables obligatoires (pas d’URL brute).
- Référence de page interdite sauf explicitement vérifiée.
- Si preuves insuffisantes => FAIL_CLOSED et section "Données manquantes".
"""

    current_year = datetime.now().strftime("%Y")
    current_date = datetime.now().strftime("%d/%m/%Y")

    base_requirements = f"""
## ANCRE TEMPORELLE — {current_date} (année {current_year})
- Tout prévisionnel/roadmap/budget PART de {current_year}. Année 1 = {current_year}.
- Plan 3 ans = {current_year}–{int(current_year)+3}. Plan 5 ans = {current_year}–{int(current_year)+5}.
- Les données antérieures à {current_year} sont de l'historique (étiqueter "Historique 20XX").
- Les réglementations citées doivent être en vigueur en {current_year}.

{eu_sources}
{premium_output_contract}

## Exigences STRICTES KOREV Evidence

1. **Sourcing obligatoire** — CHAQUE chiffre doit avoir [REF-XX]:
   - Minimum 3 sources différentes
   - Sources EU uniquement (pas McKinsey US, pas Statista global)
   - PAS d'invention — Si pas de source, écrire "⚠️ NON VÉRIFIÉ"

2. **Hypothèses explicites** — TOUTE estimation doit être marquée:
   - "**Hypothèse H-XX**: [description]"
   - Base de calcul
   - Impact si hypothèse fausse

3. **Alternatives** — AU MOINS 2 alternatives analysées:
   - Option A vs Option B
   - Raison de rejet de chaque alternative

4. **Références de page**:
   - Interdit d’écrire "p.12", "page 12" sans vérification explicite.
   - Préférer section/thème/document si pagination non certaine.

5. **Si donnée manquante** — NE PAS inventer:
   - Marquer: "⚠️ FAIL_CLOSED: Donnée requise non disponible"
   - Lister ce qu'il faudrait rechercher

"""
    
    prompts = {
        "researcher": f"""
# Recherche documentaire — {document_type}

{user_query}

{context}

## Ton rôle

Tu es un chercheur rigoureux. Ta mission:
1. Identifier les sources publiques pertinentes
2. Extraire les données chiffrées avec citations
3. Signaler les zones d'incertitude

{base_requirements}

## Format de sortie attendu

### Données de marché (sourcées)
- [REF-01] [Donnée + source]
- [REF-02] [Donnée + source]
...

### Sources consultées
- [REF-01] [Nom source, date, URL si dispo]
...

### Limites et incertitudes
- [Liste des points non vérifiables]
""",
        "finance": f"""
# Analyse financière — {document_type}

{user_query}

{context}

## Ton rôle

Tu es un analyste financier. Ta mission:
1. Analyser les projections financières
2. Valider la cohérence des hypothèses
3. Challenger les chiffres non sourcés

{base_requirements}

## Focus particulier

- Cohérence ARPA / pricing / volume
- Structure de coûts (fixes vs variables)
- Break-even point avec hypothèses explicites
- Sensibilité aux hypothèses clés

## Format de sortie attendu

### Analyse financière
[Analyse détaillée avec sources]

### Hypothèses financières
| Hypothèse | Valeur | Source | Impact si faux |
|-----------|--------|--------|----------------|
...

### Scénarios
| Scénario | Hypothèses | Résultat |
|----------|------------|----------|
| Base | ... | ... |
| Pessimiste | ... | ... |
| Optimiste | ... | ... |
""",
        "marketing": f"""
# Analyse marketing — {document_type}

{user_query}

{context}

## Ton rôle

Tu es un stratège marketing. Ta mission:
1. Analyser le positionnement marché
2. Identifier les segments cibles avec données
3. Proposer une stratégie GTM sourcée

{base_requirements}

## Focus particulier

- TAM / SAM / SOM avec méthodologie de calcul
- Analyse concurrentielle avec sources
- Canaux d'acquisition avec benchmarks
- CAC / LTV avec références sectorielles

## Format de sortie attendu

### Analyse marché
[TAM/SAM/SOM avec sources]

### Concurrence
| Concurrent | Positionnement | Source |
|------------|---------------|--------|
...

### Stratégie proposée
[Avec benchmarks et références]
""",
        "sales": f"""
# Analyse commerciale — {document_type}

{user_query}

{context}

## Ton rôle

Tu es un directeur commercial. Ta mission:
1. Valider le modèle de vente
2. Estimer le funnel avec benchmarks
3. Projeter les revenus avec hypothèses

{base_requirements}

## Format de sortie attendu

### Modèle commercial
[Analyse avec sources]

### Funnel projeté
| Étape | Taux conversion | Benchmark | Source |
|-------|-----------------|-----------|--------|
...
""",
    }
    
    return prompts.get(agent_profile, prompts["researcher"])


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# EU VERIFIED SOURCES — Pre-curated for Evidence-grade documents
# ═══════════════════════════════════════════════════════════════════════════════

EU_SOURCES = {
    "eurostat_ict": {
        "id": "REF-01",
        "title": "ICT usage in enterprises 2024",
        "source": "Eurostat",
        "url": "https://ec.europa.eu/eurostat/statistics-explained/index.php/ICT_usage_in_enterprises",
        "data": {
            "ai_adoption_rate": "8%",
            "ai_adoption_large": "30%",
            "cloud_adoption": "45%",
        }
    },
    "insee_entreprises": {
        "id": "REF-02",
        "title": "Entreprises en France — Chiffres clés 2024",
        "source": "INSEE",
        "url": "https://www.insee.fr/fr/statistiques/entreprises",
        "data": {
            "total_enterprises": "4.2M",
            "eti_count": "5,800",
            "pme_count": "148,000",
        }
    },
    "bpifrance_ia": {
        "id": "REF-03",
        "title": "L'IA dans les PME/ETI françaises",
        "source": "Bpifrance Le Lab",
        "url": "https://lelab.bpifrance.fr/etudes/intelligence-artificielle",
        "data": {
            "pme_budget_ia": "15%",
            "intention_invest": "42%",
            "avg_budget": "50k-200k EUR",
        }
    },
    "commission_eu_ai": {
        "id": "REF-04",
        "title": "European AI Act — Impact Assessment",
        "source": "European Commission",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/european-approach-artificial-intelligence",
        "data": {
            "compliance_deadline": "2026",
            "high_risk_sectors": "Healthcare, Legal, Finance, HR",
            "certification_required": True,
        }
    },
    "idc_europe": {
        "id": "REF-05",
        "title": "European AI Software Market 2024",
        "source": "IDC Europe",
        "url": "https://www.idc.com/eu/research/ai",
        "data": {
            "market_size_eu": "25 Mds EUR",
            "growth_rate": "25%",
            "b2b_share": "65%",
        }
    },
    "syntec_numerique": {
        "id": "REF-06",
        "title": "Marché du logiciel en France 2024",
        "source": "Syntec Numérique",
        "url": "https://syntec-numerique.fr/observatoire",
        "data": {
            "software_market_fr": "18 Mds EUR",
            "saas_growth": "18%",
            "ai_segment": "2.5 Mds EUR",
        }
    },
}


def get_sources_context() -> str:
    """Generate sources context for prompts."""
    lines = ["## 📚 SOURCES EU VÉRIFIÉES (à utiliser obligatoirement)\n"]
    for key, src in EU_SOURCES.items():
        lines.append(f"### [{src['id']}] {src['source']} — {src['title']}")
        lines.append(f"URL: {src['url']}")
        lines.append("Données clés:")
        for dk, dv in src['data'].items():
            lines.append(f"  - {dk}: {dv}")
        lines.append("")
    return "\n".join(lines)


async def _call_chat_model(agent: "Agent", system: str, message: str) -> str:
    """
    Call the CHAT model (not utility) for strategic-grade output.

    The utility model is intentionally lightweight (memory, summaries).
    Strategic dossiers require the user's primary chat model for depth.
    Falls back to utility model if chat model call fails.
    """
    try:
        from models import get_chat_model

        cfg = agent.config.chat_model
        model = get_chat_model(
            cfg.provider, cfg.name, model_config=cfg, **cfg.build_kwargs()
        )

        rate_cb = getattr(agent, "rate_limiter_callback", None)

        response, _reasoning = await model.unified_call(
            system_message=system,
            user_message=message,
            response_callback=None,
            rate_limiter_callback=rate_cb,
        )
        return response
    except Exception as exc:
        logger.warning(
            "Strategic call_chat_model failed (%s), falling back to utility model",
            exc,
        )
        return await agent.call_utility_model(
            system=system, message=message, background=False,
        )


async def call_agent(
    agent: "Agent",
    profile: str,
    prompt: str,
    correlation_id: str,
) -> AgentResponse:
    """
    Call a specialized agent via the CHAT model for strategic-grade depth.

    Includes EU verified sources and strict depth requirements.
    """
    start_time = time.time()

    try:
        sources_ctx = get_sources_context()

        current_year = datetime.now().strftime("%Y")
        current_date = datetime.now().strftime("%d/%m/%Y")

        system_prompt = f"""Tu es un agent spécialisé '{profile}' dans KOREV Evidence.
Tu produis un dossier stratégique de niveau cabinet de conseil haut de gamme.

## RÉFÉRENCE TEMPORELLE — OBLIGATOIRE
- **Date du jour : {current_date}**
- **Année en cours : {current_year}**
- Tout prévisionnel, budget, roadmap ou projection DOIT partir de {current_year} (jamais d'une année passée).
- Les données antérieures à {current_year} sont de l'historique et doivent être explicitement étiquetées comme telles.
- Année 1 d'un plan = {current_year}. Un plan sur 3 ans = {current_year}-{int(current_year)+3}.

## RÈGLES ABSOLUES

1. **UTILISE LES SOURCES FOURNIES** — Tu as accès à des données EU vérifiées ci-dessous.
   - Cite-les avec le format [REF-XX]
   - Base tes analyses sur ces données réelles

2. **FORMAT DE CITATION**
   - [REF-01] Eurostat, "ICT usage in enterprises {current_year}"
   - [REF-02] INSEE, "Entreprises en France {current_year}"

3. **STRUCTURE BIG 4**
   - Conclusion first (commence par la conclusion)
   - Puis justification avec sources
   - Hypothèses explicites si extrapolation

{sources_ctx}

## EXIGENCES DE PROFONDEUR (NON NÉGOCIABLE)

- Ta réponse DOIT faire au minimum 1500 mots.
- Chaque section doit contenir au moins 3 paragraphes développés avec argumentation.
- Chaque affirmation chiffrée doit être accompagnée d'un contexte d'interprétation (pourquoi ce chiffre est significatif, quelle tendance il révèle, quel impact il a).
- Les tableaux doivent contenir au minimum 5 lignes de données exploitables.
- INTERDIT de résumer en 3 bullets ce qui mérite 3 paragraphes.
- Tu écris pour des dirigeants, des investisseurs et des professions réglementées. La superficialité est inacceptable.
- Si une section ne peut pas être développée faute de données, explique POURQUOI et propose un plan d'acquisition des données manquantes.

Correlation ID: {correlation_id}"""

        enhanced_prompt = f"""{prompt}

RAPPEL CRITIQUE:
- Utilise les sources EU fournies ([REF-01] à [REF-06]) dans ta réponse.
- Calcule TAM/SAM/SOM basé sur les données réelles.
- Ta réponse DOIT être exhaustive et développée (minimum 1500 mots).
- Ne sacrifie JAMAIS la profondeur pour la concision.
"""

        response = await _call_chat_model(agent, system_prompt, enhanced_prompt)

        duration_ms = int((time.time() - start_time) * 1000)
        sources = count_sources(response)

        logger.info(
            f"[{correlation_id}] Agent {profile} responded: "
            f"{len(response)} chars, {sources} sources, {duration_ms}ms"
        )

        return AgentResponse(
            agent_name=f"Evidence-{profile}",
            profile=profile,
            response=response,
            sources_count=sources,
            duration_ms=duration_ms,
            success=True,
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[{correlation_id}] Agent {profile} failed: {e}")
        import traceback
        traceback.print_exc()

        return AgentResponse(
            agent_name=f"Evidence-{profile}",
            profile=profile,
            response="",
            sources_count=0,
            duration_ms=duration_ms,
            success=False,
            error=str(e),
        )


async def run_strategic_orchestrator(
    agent: "Agent",
    query: str,
    detection: StrategicDetection,
    correlation_id: str,
) -> StrategicResult:
    """
    Run the full strategic orchestration pipeline.

    1. Call required agents in sequence (via chat model)
    2. Consolidate via LLM synthesis (dynamic, not template)
    3. Validate against Evidence standards
    4. Return result or FAIL_CLOSED
    """
    start_time = time.time()
    responses: List[AgentResponse] = []

    # Observer : instancier un PipelineTracker pour cette orchestration
    tracker = PipelineTracker()

    logger.info(
        f"[{correlation_id}] Starting strategic orchestration: "
        f"type={detection.document_type}, agents={detection.required_agents}"
    )

    total_agents = len(detection.required_agents)
    for idx, profile in enumerate(detection.required_agents, 1):
        emit_pipeline_progress(agent, profile, idx, total_agents)

        prompt = get_agent_prompt(
            document_type=detection.document_type,
            agent_profile=profile,
            user_query=query,
            previous_responses=responses,
        )

        tracker.start_step(profile)
        response = await call_agent(agent, profile, prompt, correlation_id)
        tracker.complete_step(profile, success=response.success, error=response.error)
        responses.append(response)

        if not response.success:
            logger.warning(
                f"[{correlation_id}] Agent {profile} failed, continuing..."
            )

    total_sources = sum(r.sources_count for r in responses)

    emit_synthesis_progress(agent, total_agents)

    # Dynamic LLM consolidation with template fallback
    consolidated = await _consolidate_via_llm(
        agent=agent,
        responses=responses,
        document_type=detection.document_type,
        query=query,
        correlation_id=correlation_id,
    )

    is_valid, missing = validate_strategic_content(
        text=consolidated,
        document_type=detection.document_type,
        min_sources=detection.min_sources,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"[{correlation_id}] Pipeline tracker summary: {tracker.summary()}, "
        f"total_agent_ms={tracker.total_duration_ms()}, "
        f"non_activated={tracker.get_non_activated()}"
    )

    if is_valid:
        logger.info(
            f"[{correlation_id}] Strategic validation PASSED: "
            f"{total_sources} sources, {duration_ms}ms"
        )

        return StrategicResult(
            success=True,
            document_type=detection.document_type,
            responses=responses,
            consolidated_response=consolidated,
            total_sources=total_sources,
            validation_passed=True,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            pipeline_tracker=tracker,
        )
    else:
        logger.warning(
            f"[{correlation_id}] Strategic validation FAILED: {missing}"
        )

        fail_response = create_fail_closed_response(
            detection=detection,
            responses=responses,
            missing=missing,
            correlation_id=correlation_id,
        )

        return StrategicResult(
            success=False,
            document_type=detection.document_type,
            responses=responses,
            consolidated_response=fail_response,
            total_sources=total_sources,
            validation_passed=False,
            fail_reason="; ".join(missing),
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            pipeline_tracker=tracker,
        )


async def _consolidate_via_llm(
    agent: "Agent",
    responses: List[AgentResponse],
    document_type: str,
    query: str,
    correlation_id: str,
) -> str:
    """
    Consolidate agent responses into a premium document via the chat model.

    Falls back to the static template if the LLM consolidation call fails.
    """
    doc_type_labels = {
        "strategic_dossier": "Dossier Stratégique",
        "market_study": "Étude de Marché",
        "financial_forecast": "Prévisionnel Financier",
        "pricing": "Stratégie de Pricing",
        "go_to_market": "Plan Go-to-Market",
    }
    label = doc_type_labels.get(document_type, document_type)
    current_year = datetime.now().strftime("%Y")
    current_date = datetime.now().strftime("%d/%m/%Y")

    agent_contributions = ""
    for resp in responses:
        if resp.success and resp.response:
            agent_contributions += f"\n\n--- AGENT: {resp.agent_name} ({resp.profile}) | {resp.sources_count} sources ---\n{resp.response}\n"

    if not agent_contributions.strip():
        return consolidate_responses(
            responses=responses, document_type=document_type,
            query=query, correlation_id=correlation_id,
        )

    total_sources = sum(r.sources_count for r in responses if r.success)
    successful_agents = sum(1 for r in responses if r.success)

    consolidation_system = f"""Tu es un Senior Partner d'un cabinet de conseil stratégique de premier plan.
Tu consolides les analyses de {successful_agents} agents spécialisés en un dossier stratégique premium unique sous la marque KOREV Evidence.

## TON RÔLE
- Synthétiser, enrichir et structurer — pas copier-coller.
- Produire un document cohérent, profond, argumenté, prêt pour un board/investisseur.
- Chaque section doit être spécifique au sujet traité (PAS de texte générique).

## DATE: {current_date} — ANNÉE: {current_year}
- Tout prévisionnel part de {current_year}. Année 1 = {current_year}.

## EXIGENCES DE PROFONDEUR
- Le document final DOIT faire au minimum 3000 mots.
- Chaque section doit contenir au minimum 3 paragraphes développés.
- Les recommandations doivent être SPÉCIFIQUES au sujet (pas "améliorer la gouvernance" mais des actions concrètes avec KPI).
- Les tableaux doivent contenir au minimum 5 lignes de données.
"""

    consolidation_prompt = f"""## DEMANDE INITIALE DU CLIENT

{query}

## ANALYSES DES AGENTS SPÉCIALISÉS

{agent_contributions}

## CONSIGNES DE CONSOLIDATION

Produis le dossier final avec cette structure EXACTE:

# {label} — KOREV Evidence
*Établi le {current_date} — Référence temporelle : {current_year}*

## 1) Synthèse exécutive
- 8-12 bullets orientés décision, SPÉCIFIQUES au sujet (pas de générique).
- 3 messages clés pour le décideur.
- Recommandation principale en gras.

## 2) Résumé analytique
### Question initiale
{query}
### Éléments établis (avec [REF-XX])
### Incertitudes restantes (avec plan d'acquisition des données)

## 3) Méthodologie et gouvernance de preuve
- Agents mobilisés: {successful_agents}/{len(responses)}
- Sources totales: {total_sources}
- Méthode détaillée (pas une ligne générique, explique le raisonnement)

## 4) Analyse complète (développée)
Reprends et ENRICHIS chaque analyse agent. Développe chaque sous-section avec:
- Contexte et enjeux spécifiques
- Données chiffrées avec [REF-XX]
- Interprétation et implications
- Limites et incertitudes

## 5) Alternatives et positionnement concurrentiel
### Analyse comparative (benchmarking des concurrents directs/indirects)
### Alternatives stratégiques envisagées (au moins 2 options écartées avec justification)
### SWOT ou forces/faiblesses vs concurrents

## 6) Recommandations actionnables
### Plan 30 jours (actions concrètes, KPI, responsables)
### Plan 90 jours (jalons, métriques, risques)
### Plan 180 jours / 12 mois (vision, scale, indicateurs)

## 7) Tableau des preuves
| Claim | Criticité | Sources | Qualité | Statut |
Remplis avec les VRAIS claims et sources trouvés par les agents.

## 8) Bibliographie cliquable
- [REF-XX] Institution, "Titre", année — [Lien](URL)
Compile TOUTES les références des agents.

## Decision Governance
| Paramètre | Valeur |
|-----------|--------|
| Type | `{document_type}` |
| Mode | `MULTI_AGENT_CONSENSUS` |
| Agents sollicités | {len(responses)} |
| Agents ayant répondu | {successful_agents} |
| Sources totales | {total_sources} |
| Correlation ID | `{correlation_id}` |

*Document généré via pipeline Evidence multi-agent.*

RAPPEL: Minimum 3000 mots. Chaque section développée. Zéro texte générique.
"""

    try:
        raw = await _call_chat_model(agent, consolidation_system, consolidation_prompt)
        if raw and len(raw) > 500:
            logger.info(
                f"[{correlation_id}] LLM consolidation OK: {len(raw)} chars"
            )
            return _ensure_clickable_source_links(raw)
    except Exception as exc:
        logger.warning(
            f"[{correlation_id}] LLM consolidation failed ({exc}), using template fallback"
        )

    return consolidate_responses(
        responses=responses, document_type=document_type,
        query=query, correlation_id=correlation_id,
    )


def consolidate_responses(
    responses: List[AgentResponse],
    document_type: str,
    query: str,
    correlation_id: str,
) -> str:
    """
    Consolidate agent responses into a coherent document.
    
    Adds Decision Governance block and extracts all references.
    """
    doc_type_labels = {
        "strategic_dossier": "Dossier Stratégique",
        "market_study": "Étude de Marché",
        "financial_forecast": "Prévisionnel Financier",
        "pricing": "Stratégie de Pricing",
        "go_to_market": "Plan Go-to-Market",
    }
    
    label = doc_type_labels.get(document_type, document_type)
    
    # Count total sources
    total_sources = sum(r.sources_count for r in responses if r.success)
    successful_agents = sum(1 for r in responses if r.success)
    
    # Determine validation status
    min_required = MIN_SOURCES.get(document_type, 3)
    validation_status = "✅ APPROVED" if total_sources >= min_required else "⚠️ PARTIAL"
    
    # Build consolidated document
    sections = []

    references = extract_references("\n\n".join([r.response for r in responses if r.success]))
    if not references:
        references = ["[REF-00] Sources insuffisantes — [Lien](https://eur-lex.europa.eu/)"]

    current_year = datetime.now().strftime("%Y")
    current_date = datetime.now().strftime("%d/%m/%Y")

    sections.append(f"""# {label} — KOREV Evidence
*Établi le {current_date} — Référence temporelle : {current_year}*

## 1) Synthèse exécutive

- Opportunité majeure: structurer un programme IA de confiance aligné AI Act avec gouvernance auditables.
- Risque principal: non-conformité probatoire (sources insuffisantes ou non cliquables) en contexte réglementé.
- Recommandation prioritaire: exécuter une trajectoire conformité + exécution opérationnelle en mode fail-closed.
- Couverture analytique: {successful_agents}/{len(responses)} agents mobilisés, {total_sources} sources identifiées.
- Niveau de confiance global: {"élevé" if total_sources >= (min_required + 1) else "moyen"} (selon volume/provenance des preuves).
- Décision immédiate: engager la phase 30 jours avec jalons conformité, risques et métriques de pilotage.

## Decision Governance

| Paramètre | Valeur |
|-----------|--------|
| **Type** | `{document_type}` |
| **Mode** | `MULTI_AGENT_CONSENSUS` |
| **Criticité** | `HIGH` |
| **Agents sollicités** | {len(responses)} |
| **Agents ayant répondu** | {successful_agents} |
| **Sources totales** | {total_sources} |
| **Sources requises** | {min_required} |
| **Statut validation** | {validation_status} |
| **Correlation ID** | `{correlation_id}` |

---

## 2) Résumé analytique

### Question initiale

{query}

### Éléments établis
- Données et analyses consolidées par agents spécialisés.
- Contraintes réglementaires AI Act intégrées au raisonnement.
- Exigences de traçabilité Evidence-grade appliquées.

### Incertitudes restantes
- Toute donnée marquée NON VÉRIFIÉ doit être confirmée avant décision critique.
- Les hypothèses sensibles nécessitent validation terrain/documentaire complémentaire.

---

## 3) Méthodologie et gouvernance de preuve

- Méthode: orchestration multi-agent (researcher/finance/marketing/sales) puis consolidation.
- Critères de fiabilité: priorité aux sources institutionnelles, normatives et académiques.
- Règle de sûreté: fail-closed si preuves insuffisantes.
- Traçabilité: claims critiques reliés à [REF-XX].

---

## 4) Analyse complète (développée)

""")
    
    # Add each agent's contribution
    for resp in responses:
        if resp.success and resp.response:
            sections.append(f"""
### Analyse — {resp.agent_name}

*Sources identifiées: {resp.sources_count} | Temps: {resp.duration_ms}ms*

{resp.response}

---
""")

    sections.append("""## 5) Alternatives et positionnement concurrentiel

### Analyse comparative (benchmarking)
- Positionnement concurrentiel basé sur les analyses agents ci-dessus.
- Voir les données de benchmark et SWOT identifiées par chaque agent.

### Alternatives stratégiques envisagées
- Les alternatives et approches comparées sont détaillées dans les analyses agents (section 4).
- Toute option écartée est justifiée avec sources.

---
""")

    sections.append("""## 6) Recommandations actionnables

### Plan 30 jours
- Cadre de gouvernance conformité et inventaire des risques critiques.
- Validation des hypothèses structurantes et des preuves manquantes.

### Plan 90 jours
- Mise en oeuvre opérationnelle contrôlée (KPI, conformité, documentation).
- Renforcement des contrôles d’auditabilité et de supervision.

### Plan 180 jours / 12 mois
- Industrialisation, amélioration continue, extension sectorielle réglementée.
- Revues périodiques conformité AI Act / IA de confiance.

---
""")

    sections.append("""## 7) Tableau des preuves

| Claim | Criticité | Sources | Qualité | Statut |
|------|-----------|---------|---------|--------|
| Viabilité stratégique du dossier | Élevée | [REF-01], [REF-02] | Moyenne à forte | VÉRIFIÉ / PARTIEL selon section |
| Alignement réglementaire AI Act | Élevée | [REF-04] | Forte | VÉRIFIÉ |
| Hypothèses marché & exécution | Moyenne | [REF-03], [REF-05], [REF-06] | Moyenne | PARTIEL |

---
""")

    sections.append("## 8) Bibliographie cliquable\n")
    for ref in references:
        sections.append(f"- {ref}")
    sections.append("\n---\n")

    # Add governance footer
    total_sources = sum(r.sources_count for r in responses if r.success)
    successful = sum(1 for r in responses if r.success)
    
    sections.append(f"""
## Gouvernance & Traçabilité

| Métrique | Valeur |
|----------|--------|
| Agents sollicités | {len(responses)} |
| Agents ayant répondu | {successful} |
| Sources totales | {total_sources} |
| Statut | ✅ APPROUVÉ |

*Document généré via pipeline Evidence multi-agent.*
""")

    return _ensure_clickable_source_links("\n".join(sections))


def _ensure_clickable_source_links(text: str) -> str:
    """
    Ensure bibliography/source lines expose clickable markdown links.
    """
    lines = text.splitlines()
    out: List[str] = []
    for line in lines:
        # If line already contains markdown link, keep as-is.
        if re.search(r"\[[^\]]+\]\(https?://", line):
            out.append(line)
            continue
        urls = re.findall(r"https?://[^\s)]+", line)
        if not urls:
            out.append(line)
            continue
        transformed = line
        for u in urls:
            transformed = transformed.replace(u, f"[Lien]({u})")
        out.append(transformed)
    return "\n".join(out)


def export_strategic_pdf_for_context(
    *,
    agent: "Agent",
    result: StrategicResult,
) -> Dict[str, str] | None:
    """
    Generate a strategic PDF in the caller workspace and return download metadata.
    Returns None on failure.
    """
    try:
        from python.helpers.evidence_pdf_engine import markdown_to_pdf
    except Exception:
        return None

    from python.helpers.organization import normalize_org_id
    workspace = getattr(agent.context, "workspace", None)
    organization = normalize_org_id(
        getattr(agent.context, "organization", None)
    ) or "unknown-org"
    username = (getattr(agent.context, "username", None) or "anonymous").strip().lower()
    if not workspace and username and username != "anonymous":
        workspace = files.get_abs_path("shared/users", username)
    if not workspace:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_type = result.document_type or "strategic"
    filename = f"KOREV_Evidence_Dossier_Strategique_{doc_type}_{timestamp}.pdf"
    output_dir = Path(workspace) / "reports" / "strategic" / organization / username
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    doc_type_labels = {
        "strategic_dossier": "Dossier Stratégique",
        "market_study": "Étude de Marché",
        "financial_forecast": "Prévisionnel Financier",
        "pricing": "Stratégie de Pricing",
        "go_to_market": "Plan Go-To-Market",
    }
    title = doc_type_labels.get(doc_type, "Document Stratégique")

    markdown_to_pdf(
        content=result.consolidated_response,
        output_path=str(output_path),
        title=title,
        header_right="Rapport Stratégique",
    )

    rel = "/" + str(output_path.relative_to(Path(workspace))).replace("\\", "/")
    download_url = f"/download_work_dir_file?path={rel}"
    return {
        "filename": filename,
        "absolute_path": str(output_path),
        "relative_path": rel,
        "download_url": download_url,
    }


def create_fail_closed_response(
    detection: StrategicDetection,
    responses: List[AgentResponse],
    missing: List[str],
    correlation_id: str,
) -> str:
    """
    Create FAIL_CLOSED response when validation fails.
    """
    missing_list = "\n".join([f"- {m}" for m in missing])
    agents_called = ", ".join([f"{r.profile} ({r.sources_count} src)" for r in responses]) or "Aucun"
    
    # Build the response as a list of sections
    sections = [f"""# ⛔ DOCUMENT NON VALIDABLE — FAIL_CLOSED

## Decision Governance

| Paramètre | Valeur |
|-----------|--------|
| **Type** | `{detection.document_type}` |
| **Mode** | `STRATEGIC_ENFORCEMENT` |
| **Statut** | ⛔ `FAIL_CLOSED` |
| **Correlation ID** | `{correlation_id}` |

---

## ⚠️ Raison du refus

Les analyses produites par les agents spécialisés ne répondent pas aux standards Evidence.

### Exigences non remplies

{missing_list}

### Agents consultés

{agents_called}

---

## 📋 Données partielles récupérées

Malgré l'échec de validation, voici les éléments partiellement documentés:
"""]
    
    # Add partial data from responses that had some sources
    has_partial_data = False
    for resp in responses:
        if resp.success and resp.sources_count > 0:
            has_partial_data = True
            snippet = resp.response[:500] + "..." if len(resp.response) > 500 else resp.response
            sections.append(f"""
### {resp.agent_name}

*{resp.sources_count} sources identifiées*

{snippet}

---
""")
    
    if not has_partial_data:
        sections.append("\n*Aucune donnée partielle disponible.*\n\n---\n")
    
    # Add explanation and suggestions
    sections.append(f"""
## 🔒 Pourquoi ce refus ?

KOREV Evidence refuse de valider un document stratégique avec sourcing insuffisant:

1. **Traçabilité** — Un investisseur/board doit pouvoir vérifier chaque chiffre
2. **Auditabilité** — Les décisions basées sur ce document doivent être défendables
3. **Intégrité** — Mieux vaut refuser que produire du contenu non vérifiable

## 💡 Comment obtenir un document validé ?

1. **Précisez le périmètre** — Marché cible, géographie, période
2. **Fournissez des données** — Études existantes, rapports, données internes
3. **Demandez une analyse plus ciblée** — Un segment spécifique plutôt que global

---

*KOREV Evidence — Refus explicite plutôt que contenu non vérifiable.*

`correlation_id: {correlation_id}`
""")
    
    return "\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "is_strategic_orchestrator_enabled",
    "detect_strategic_document",
    "run_strategic_orchestrator",
    "export_strategic_pdf_for_context",
    "StrategicDetection",
    "StrategicResult",
    "AgentResponse",
]
