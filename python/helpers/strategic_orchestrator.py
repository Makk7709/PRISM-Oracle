"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   STRATEGIC DOCUMENT ORCHESTRATOR                            ║
║                                                                              ║
║  Pipeline déterministe pour documents stratégiques:                          ║
║  - Détection automatique (étude de marché, prévisionnel, etc.)              ║
║  - Appel séquentiel des agents spécialisés (researcher → finance)           ║
║  - Validation des sources et du contenu                                      ║
║  - FAIL_CLOSED si standards Evidence non respectés                           ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2026 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import uuid4

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
    "market_study": ["researcher", "finance", "marketing"],
    "financial_forecast": ["finance", "researcher"],
    "pricing": ["finance", "marketing", "researcher"],
    "go_to_market": ["marketing", "sales", "researcher"],
}

# Minimum sources required per document type
MIN_SOURCES = {
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


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_strategic_document(query: str) -> StrategicDetection:
    """
    Detect if query requests a strategic document.
    
    Returns detection result with document type and requirements.
    """
    query_lower = query.lower()
    
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
    """Count source indicators in text."""
    patterns = [
        r"\[REF-\d+\]",
        r"\[S\d+\]",
        r"Source\s*:\s*\S+",
        r"Eurostat|Gartner|McKinsey|Forrester|IDC|Statista|INSEE",
        r"\(20\d{2}\)",  # Year citations
        r"https?://\S+",  # URLs
    ]
    
    count = 0
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        count += len(matches)
    
    return count


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
    
    # Check alternatives
    if not re.search(r"alternative|option\s*\d|écartée?|rejetée?", text, re.IGNORECASE):
        missing.append("Alternatives non analysées")
    
    return len(missing) == 0, missing


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

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
    - Strict sourcing requirements
    """
    context = ""
    if previous_responses:
        context = "\n\n## Analyses précédentes:\n"
        for resp in previous_responses:
            context += f"\n### {resp.agent_name} ({resp.profile}):\n{resp.response[:500]}...\n"
    
    base_requirements = """
## Exigences STRICTES

1. **Sourcing obligatoire** — Chaque chiffre/affirmation doit citer sa source:
   - Format: [REF-XX] avec liste des sources en fin
   - Sources acceptées: Eurostat, INSEE, Gartner, McKinsey, Statista, rapports publics
   - PAS d'invention de chiffres sans source

2. **Hypothèses explicites** — Toute hypothèse doit être clairement marquée:
   - "Hypothèse: [description]"
   - Impact si hypothèse fausse

3. **Alternatives** — Au moins 2 alternatives avec raison d'élimination

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

async def call_agent(
    agent: "Agent",
    profile: str,
    prompt: str,
    correlation_id: str,
) -> AgentResponse:
    """
    Call a specialized agent and capture response.
    """
    start_time = time.time()
    
    try:
        # Use the agent's utility model for specialized calls
        response = await agent.call_utility_model(
            system=f"Tu es un agent spécialisé '{profile}' dans KOREV Evidence. "
                   f"Tu dois fournir une analyse SOURCÉE et VÉRIFIABLE. "
                   f"Corrélation: {correlation_id}",
            message=prompt,
            background=False,
        )
        
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
    
    1. Call required agents in sequence
    2. Consolidate responses
    3. Validate against Evidence standards
    4. Return result or FAIL_CLOSED
    """
    start_time = time.time()
    responses: List[AgentResponse] = []
    
    logger.info(
        f"[{correlation_id}] Starting strategic orchestration: "
        f"type={detection.document_type}, agents={detection.required_agents}"
    )
    
    # Call each required agent
    for profile in detection.required_agents:
        prompt = get_agent_prompt(
            document_type=detection.document_type,
            agent_profile=profile,
            user_query=query,
            previous_responses=responses,
        )
        
        response = await call_agent(agent, profile, prompt, correlation_id)
        responses.append(response)
        
        # If critical agent fails, continue but log warning
        if not response.success:
            logger.warning(
                f"[{correlation_id}] Agent {profile} failed, continuing..."
            )
    
    # Count total sources
    total_sources = sum(r.sources_count for r in responses)
    
    # Consolidate responses
    consolidated = consolidate_responses(
        responses=responses,
        document_type=detection.document_type,
        query=query,
        correlation_id=correlation_id,
    )
    
    # Validate content
    is_valid, missing = validate_strategic_content(
        text=consolidated,
        document_type=detection.document_type,
        min_sources=detection.min_sources,
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Build result
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
        )


def consolidate_responses(
    responses: List[AgentResponse],
    document_type: str,
    query: str,
    correlation_id: str,
) -> str:
    """
    Consolidate agent responses into a coherent document.
    """
    doc_type_labels = {
        "market_study": "Étude de Marché",
        "financial_forecast": "Prévisionnel Financier",
        "pricing": "Stratégie de Pricing",
        "go_to_market": "Plan Go-to-Market",
    }
    
    label = doc_type_labels.get(document_type, document_type)
    
    # Build consolidated document
    sections = []
    
    sections.append(f"""# {label} — KOREV Evidence

## Decision Governance

| Paramètre | Valeur |
|-----------|--------|
| **Type** | `{document_type}` |
| **Mode** | `MULTI_AGENT_CONSENSUS` |
| **Agents consultés** | {len(responses)} |
| **Correlation ID** | `{correlation_id}` |

---

## Question initiale

{query}

---
""")
    
    # Add each agent's contribution
    for resp in responses:
        if resp.success and resp.response:
            sections.append(f"""
## Analyse — {resp.agent_name}

*Sources identifiées: {resp.sources_count} | Temps: {resp.duration_ms}ms*

{resp.response}

---
""")
    
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
    
    return "\n".join(sections)


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
    "StrategicDetection",
    "StrategicResult",
    "AgentResponse",
]
