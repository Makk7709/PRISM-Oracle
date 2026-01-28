"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MOCK LLM FIXTURE — P2.c                                   ║
║                                                                              ║
║  Mock LLM contractuel pour tests FIRAC et consensus.                        ║
║  Retourne des réponses JSON déterministes basées sur le prompt.             ║
║                                                                              ║
║  Utilisation:                                                                ║
║    from tests.fixtures.mock_llm import create_mock_llm, MockLLMResponses    ║
║    llm = create_mock_llm()                                                  ║
║    response = await llm(messages=[...], temperature=0)                      ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# FIRAC RESPONSE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

FIRAC_RESPONSE_TEMPLATE = {
    "facts": [
        "Requête utilisateur concernant une question juridique",
        "Contexte identifié dans les sources disponibles"
    ],
    "rules": [
        "Art. 1103 C. civ. : Les contrats légalement formés tiennent lieu de loi",
        "Art. 1104 C. civ. : Les contrats doivent être exécutés de bonne foi"
    ],
    "application": (
        "L'analyse des sources disponibles permet d'identifier les règles applicables "
        "à la situation présentée. Les principes de bonne foi contractuelle et de force "
        "obligatoire des contrats s'appliquent au cas d'espèce."
    ),
    "risks": [
        "⚠️ Interprétation jurisprudentielle variable selon les tribunaux",
        "⚠️ Évolution législative possible"
    ],
    "next_action": "Vérifier les sources sur Légifrance et consulter un professionnel si nécessaire",
    "claims": [
        {
            "text": "Les contrats doivent être exécutés de bonne foi",
            "claim_type": "cited",
            "citation": "Art. 1104 C. civ.",
            "chunk_id": "chunk_002"
        },
        {
            "text": "La force obligatoire des contrats est un principe fondamental",
            "claim_type": "cited",
            "citation": "Art. 1103 C. civ.",
            "chunk_id": "chunk_000"
        }
    ]
}

FIRAC_RESPONSE_NO_SOURCES = {
    "facts": [
        "Requête utilisateur concernant une question juridique"
    ],
    "rules": [],
    "application": (
        "Aucune source pertinente n'a été identifiée pour cette question. "
        "Une analyse approfondie nécessite des informations complémentaires."
    ),
    "risks": [
        "⚠️ Aucune source identifiée"
    ],
    "next_action": "REQUEST_INFO",
    "claims": []
}

FIRAC_RESPONSE_CLAUSE_NON_CONCURRENCE = {
    "facts": [
        "Question relative à une clause de non-concurrence",
        "Contexte de droit du travail"
    ],
    "rules": [
        "Cass. soc., 10 juill. 2002 : Conditions de validité de la clause de non-concurrence",
        "Art. L1121-1 C. trav. : Restrictions proportionnées au but recherché"
    ],
    "application": (
        "La clause de non-concurrence n'est licite que si elle remplit quatre conditions cumulatives : "
        "être indispensable à la protection des intérêts légitimes de l'entreprise, "
        "être limitée dans le temps et dans l'espace, tenir compte des spécificités de l'emploi, "
        "et comporter une contrepartie financière."
    ),
    "risks": [
        "⚠️ Risque de nullité si contrepartie financière insuffisante",
        "⚠️ Jurisprudence stricte sur les conditions de validité"
    ],
    "next_action": "Vérifier les conditions de validité avec les pièces du dossier",
    "claims": [
        {
            "text": "La clause de non-concurrence doit comporter une contrepartie financière",
            "claim_type": "cited",
            "citation": "Cass. soc., 10 juill. 2002",
            "chunk_id": "chunk_013"
        },
        {
            "text": "Les restrictions doivent être proportionnées au but recherché",
            "claim_type": "cited",
            "citation": "Art. L1121-1 C. trav.",
            "chunk_id": "chunk_007"
        }
    ]
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS RESPONSE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

CONSENSUS_APPROVE_RESPONSE = {
    "approve": True,
    "reasoning": "L'analyse juridique respecte les exigences de traçabilité et de citation des sources.",
    "confidence": 0.85,
    "risks_identified": []
}

CONSENSUS_REJECT_RESPONSE = {
    "approve": False,
    "reasoning": "L'analyse présente des affirmations sans sources vérifiables.",
    "confidence": 0.75,
    "risks_identified": ["Claims non sourcés détectés"]
}


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK LLM FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

class MockLLMResponses:
    """Container for mock LLM response templates."""
    
    FIRAC_TEMPLATE = FIRAC_RESPONSE_TEMPLATE
    FIRAC_NO_SOURCES = FIRAC_RESPONSE_NO_SOURCES
    FIRAC_CLAUSE_NON_CONCURRENCE = FIRAC_RESPONSE_CLAUSE_NON_CONCURRENCE
    CONSENSUS_APPROVE = CONSENSUS_APPROVE_RESPONSE
    CONSENSUS_REJECT = CONSENSUS_REJECT_RESPONSE


def create_mock_llm(
    default_response: Optional[Dict[str, Any]] = None,
    response_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Callable:
    """
    Create a mock LLM function for testing.
    
    Args:
        default_response: Default response when no pattern matches
        response_map: Map of regex patterns to responses
        
    Returns:
        Async function that mimics LLM behavior
    """
    _default = default_response or FIRAC_RESPONSE_TEMPLATE
    _map = response_map or {}
    
    # Built-in pattern matching
    BUILTIN_PATTERNS = {
        r"non.?concurrence|clause.*travail": FIRAC_RESPONSE_CLAUSE_NON_CONCURRENCE,
        r"SOURCES DISPONIBLES.*Aucune|sources_block.*\(Aucune": FIRAC_RESPONSE_NO_SOURCES,
        r"consensus|vote|approve": CONSENSUS_APPROVE_RESPONSE,
    }
    
    async def mock_llm_func(
        messages: List[Dict[str, str]],
        temperature: float = 0,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        """Mock LLM that returns deterministic JSON responses."""
        
        # Extract prompt content
        prompt_content = ""
        for msg in messages:
            if isinstance(msg, dict):
                prompt_content += msg.get("content", "") + "\n"
            elif isinstance(msg, str):
                prompt_content += msg + "\n"
        
        prompt_lower = prompt_content.lower()
        
        # Check custom patterns first
        for pattern, response in _map.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                return json.dumps(response, ensure_ascii=False, indent=2)
        
        # Check built-in patterns
        for pattern, response in BUILTIN_PATTERNS.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                return json.dumps(response, ensure_ascii=False, indent=2)
        
        # Return default
        return json.dumps(_default, ensure_ascii=False, indent=2)
    
    return mock_llm_func


def create_consensus_mock(approve: bool = True) -> Callable:
    """
    Create a mock for consensus voting.
    
    Args:
        approve: Whether the consensus should approve
        
    Returns:
        Async function that returns consensus response
    """
    response = CONSENSUS_APPROVE_RESPONSE if approve else CONSENSUS_REJECT_RESPONSE
    
    async def mock_consensus_func(
        messages: List[Dict[str, str]],
        temperature: float = 0,
        **kwargs,
    ) -> str:
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    return mock_consensus_func


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def assert_firac_structure(response: Dict[str, Any]) -> None:
    """
    Assert that a response has valid FIRAC structure.
    
    Raises:
        AssertionError: If structure is invalid
    """
    required_keys = {"facts", "rules", "application", "risks", "next_action", "claims"}
    missing = required_keys - set(response.keys())
    assert not missing, f"Missing FIRAC keys: {missing}"
    
    assert isinstance(response["facts"], list), "facts must be a list"
    assert isinstance(response["rules"], list), "rules must be a list"
    assert isinstance(response["application"], str), "application must be a string"
    assert len(response["application"]) >= 50, "application must be at least 50 chars"
    assert isinstance(response["risks"], list), "risks must be a list"
    assert isinstance(response["next_action"], str), "next_action must be a string"
    assert isinstance(response["claims"], list), "claims must be a list"
    
    # Validate claims structure
    for claim in response["claims"]:
        assert "text" in claim, "claim must have text"
        assert "claim_type" in claim, "claim must have claim_type"
        assert claim["claim_type"] in ("cited", "hypothesis"), \
            f"claim_type must be cited or hypothesis, got {claim['claim_type']}"
        
        if claim["claim_type"] == "cited":
            assert "citation" in claim, "cited claim must have citation"
            assert "chunk_id" in claim, "cited claim must have chunk_id"
        elif claim["claim_type"] == "hypothesis":
            assert "basis" in claim or "text" in claim, "hypothesis claim must have basis or text"


def assert_no_unsupported_claims(response: Dict[str, Any]) -> None:
    """
    Assert that response has no UNSUPPORTED claims.
    
    This is required for OPERATIONAL/BOARD scope.
    """
    for claim in response.get("claims", []):
        assert claim.get("claim_type") != "unsupported", \
            f"UNSUPPORTED claims not allowed: {claim}"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "create_mock_llm",
    "create_consensus_mock",
    "MockLLMResponses",
    "assert_firac_structure",
    "assert_no_unsupported_claims",
    # Response templates
    "FIRAC_RESPONSE_TEMPLATE",
    "FIRAC_RESPONSE_NO_SOURCES",
    "FIRAC_RESPONSE_CLAUSE_NON_CONCURRENCE",
    "CONSENSUS_APPROVE_RESPONSE",
    "CONSENSUS_REJECT_RESPONSE",
]
