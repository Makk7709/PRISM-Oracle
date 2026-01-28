"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CUSTOM ASSERTIONS                                         ║
║                                                                              ║
║  Assertions spécialisées pour tests PRISM + Evidence.                          ║
║  Messages d'erreur explicites et parlants.                                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import re
from typing import Any, Dict, List, Optional, Set

from .fixtures import INJECTION_PATTERNS


# ═══════════════════════════════════════════════════════════════════════════════
# VOTE SCHEMA ASSERTIONS
# ═══════════════════════════════════════════════════════════════════════════════

VALID_VOTE_TYPES = {"approve", "reject", "abstain", "unavailable"}
VALID_PROVIDERS = {"arbiter_1", "arbiter_2", "arbiter_3", "Claude", "GPT-4", "Gemini"}


def assert_vote_schema(vote: Dict[str, Any], strict: bool = True) -> None:
    """
    Valide le schéma d'un vote.
    
    Schema attendu:
    {
        "provider": str (non vide),
        "approve": bool,
        "confidence": float (0.0-1.0),
        "reasoning": str,
        "latency_ms": int (>= 0),
        "risks_identified": List[str] (optionnel)
    }
    
    Raises:
        AssertionError with detailed message
    """
    assert isinstance(vote, dict), \
        f"Vote must be a dict, got {type(vote).__name__}"
    
    # Required fields
    required_fields = {"provider", "approve", "confidence", "reasoning"}
    missing = required_fields - set(vote.keys())
    assert not missing, \
        f"Vote missing required fields: {missing}. Got: {set(vote.keys())}"
    
    # Provider validation
    assert isinstance(vote["provider"], str), \
        f"provider must be str, got {type(vote['provider']).__name__}"
    assert len(vote["provider"]) > 0, \
        "provider cannot be empty string"
    
    # Approve validation
    assert isinstance(vote["approve"], bool), \
        f"approve must be bool, got {type(vote['approve']).__name__}: {vote['approve']}"
    
    # Confidence validation
    assert isinstance(vote["confidence"], (int, float)), \
        f"confidence must be numeric, got {type(vote['confidence']).__name__}"
    assert 0.0 <= vote["confidence"] <= 1.0, \
        f"confidence must be in [0.0, 1.0], got {vote['confidence']}"
    
    # Reasoning validation
    assert isinstance(vote["reasoning"], str), \
        f"reasoning must be str, got {type(vote['reasoning']).__name__}"
    
    # Optional latency_ms
    if "latency_ms" in vote:
        assert isinstance(vote["latency_ms"], int), \
            f"latency_ms must be int, got {type(vote['latency_ms']).__name__}"
        assert vote["latency_ms"] >= 0, \
            f"latency_ms cannot be negative, got {vote['latency_ms']}"
    
    # Optional risks_identified
    if "risks_identified" in vote:
        assert isinstance(vote["risks_identified"], list), \
            f"risks_identified must be list, got {type(vote['risks_identified']).__name__}"
        for risk in vote["risks_identified"]:
            assert isinstance(risk, str), \
                f"Each risk must be str, got {type(risk).__name__}"
    
    # Strict mode: no extra fields
    if strict:
        allowed_fields = required_fields | {"latency_ms", "risks_identified"}
        extra = set(vote.keys()) - allowed_fields
        assert not extra, \
            f"Vote contains unexpected fields: {extra}"


def assert_contract_valid(response: str) -> Dict[str, Any]:
    """
    Valide et parse une réponse LLM contre le contrat strict.
    
    Returns:
        Parsed dict if valid
        
    Raises:
        AssertionError if invalid
    """
    # Must be valid JSON
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Response is not valid JSON: {e}\nResponse: {response[:200]}")
    
    # Validate schema
    assert isinstance(parsed, dict), \
        f"Response must be a JSON object, got {type(parsed).__name__}"
    
    # Required fields
    assert "approve" in parsed, \
        f"Response missing 'approve' field. Got: {list(parsed.keys())}"
    assert isinstance(parsed["approve"], bool), \
        f"'approve' must be boolean, got {type(parsed['approve']).__name__}"
    
    assert "reasoning" in parsed, \
        f"Response missing 'reasoning' field. Got: {list(parsed.keys())}"
    assert isinstance(parsed["reasoning"], str), \
        f"'reasoning' must be string"
    
    # Optional but typed
    if "confidence" in parsed:
        assert isinstance(parsed["confidence"], (int, float)), \
            f"'confidence' must be numeric"
        assert 0 <= parsed["confidence"] <= 1, \
            f"'confidence' out of bounds [0,1]: {parsed['confidence']}"
    
    if "risks_identified" in parsed:
        assert isinstance(parsed["risks_identified"], list), \
            f"'risks_identified' must be array"
    
    return parsed


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS RESULT ASSERTIONS
# ═══════════════════════════════════════════════════════════════════════════════

VALID_CONSENSUS_STATUS = {
    "PENDING",
    "APPROVED",
    "REJECTED",
    "NO_CONSENSUS",
    "INFRA_FAILURE",
    "SKIPPED",
}


def assert_consensus_result(
    result: Dict[str, Any],
    expected_status: str = None,
    min_votes: int = None,
    max_latency_ms: int = None
) -> None:
    """
    Valide un résultat de consensus.
    
    Schema attendu:
    {
        "proposal_id": str (UUID),
        "status": str (APPROVED|REJECTED|NO_CONSENSUS|INFRA_FAILURE|SKIPPED),
        "votes": {"approvals": int, "rejections": int, ...},
        "decision_time_ms": int (optionnel)
    }
    """
    assert isinstance(result, dict), \
        f"Consensus result must be dict, got {type(result).__name__}"
    
    # Proposal ID
    assert "proposal_id" in result, \
        f"Missing proposal_id in result"
    assert isinstance(result["proposal_id"], str), \
        f"proposal_id must be string"
    
    # Status
    assert "status" in result, \
        f"Missing status in result"
    status = result["status"]
    if hasattr(status, 'value'):
        status = status.value
    assert status in VALID_CONSENSUS_STATUS, \
        f"Invalid status '{status}'. Valid: {VALID_CONSENSUS_STATUS}"
    
    if expected_status:
        assert status == expected_status, \
            f"Expected status '{expected_status}', got '{status}'"
    
    # Votes
    if "votes" in result:
        votes = result["votes"]
        assert isinstance(votes, dict), \
            f"votes must be dict, got {type(votes).__name__}"
        
        for key in ["approvals", "rejections"]:
            if key in votes:
                assert isinstance(votes[key], int), \
                    f"votes.{key} must be int"
                assert votes[key] >= 0, \
                    f"votes.{key} cannot be negative"
        
        if min_votes is not None:
            total = votes.get("total", sum(votes.values()))
            assert total >= min_votes, \
                f"Expected at least {min_votes} votes, got {total}"
    
    # Latency check
    if max_latency_ms is not None and "decision_time_ms" in result:
        assert result["decision_time_ms"] <= max_latency_ms, \
            f"Consensus took {result['decision_time_ms']}ms, max allowed: {max_latency_ms}ms"


def assert_quorum_2_3(approvals: int, rejections: int, total: int) -> str:
    """
    Vérifie le quorum 2/3 et retourne le statut attendu.
    
    Returns:
        "APPROVED", "REJECTED", or "NO_CONSENSUS"
    """
    required = (total * 2 + 2) // 3  # ceil(2/3)
    
    if approvals >= required:
        return "APPROVED"
    elif rejections >= required:
        return "REJECTED"
    else:
        return "NO_CONSENSUS"


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG ASSERTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def assert_audit_entry(
    audit_log: List[Dict[str, Any]],
    expected_type: str,
    correlation_id: str = None,
    required_fields: List[str] = None
) -> Dict[str, Any]:
    """
    Vérifie qu'une entrée d'audit existe.
    
    Returns:
        The matching entry
        
    Raises:
        AssertionError if not found
    """
    matching = [
        entry for entry in audit_log
        if entry.get("event_type") == expected_type
    ]
    
    assert len(matching) > 0, \
        f"No audit entry found with type '{expected_type}'. " \
        f"Found types: {[e.get('event_type') for e in audit_log]}"
    
    entry = matching[0]
    
    # Check correlation_id if specified
    if correlation_id:
        assert entry.get("correlation_id") == correlation_id, \
            f"Correlation ID mismatch: expected '{correlation_id}', " \
            f"got '{entry.get('correlation_id')}'"
    
    # Check required fields
    if required_fields:
        for field in required_fields:
            assert field in entry, \
                f"Audit entry missing field '{field}'. Entry: {entry}"
    
    return entry


def assert_audit_sequence(
    audit_log: List[Dict[str, Any]],
    expected_sequence: List[str]
) -> None:
    """
    Vérifie que les entrées d'audit suivent la séquence attendue.
    """
    actual_types = [e.get("event_type") for e in audit_log]
    
    # Check that all expected types appear in order
    expected_idx = 0
    for actual_type in actual_types:
        if expected_idx < len(expected_sequence) and actual_type == expected_sequence[expected_idx]:
            expected_idx += 1
    
    assert expected_idx == len(expected_sequence), \
        f"Audit sequence mismatch.\n" \
        f"Expected: {expected_sequence}\n" \
        f"Actual:   {actual_types}\n" \
        f"Missing:  {expected_sequence[expected_idx:]}"


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY ASSERTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def assert_no_bypass(
    mcp_calls: List[Dict[str, Any]],
    forbidden_tools: List[str]
) -> None:
    """
    Vérifie qu'aucun outil interdit n'a été appelé.
    """
    called_tools = [f"{c['server']}/{c['tool']}" for c in mcp_calls]
    
    for tool in forbidden_tools:
        assert tool not in called_tools, \
            f"SECURITY: Forbidden tool '{tool}' was called! " \
            f"All calls: {called_tools}"


def assert_sanitized(content: str, check_patterns: List[str] = None) -> None:
    """
    Vérifie que le contenu est sanitisé (pas d'injection).
    """
    patterns = check_patterns or INJECTION_PATTERNS
    
    for pattern in patterns:
        assert pattern.lower() not in content.lower(), \
            f"SECURITY: Unsanitized content detected! " \
            f"Pattern '{pattern}' found in content"


def assert_no_sensitive_data(content: str) -> None:
    """
    Vérifie qu'aucune donnée sensible n'est exposée.
    """
    sensitive_patterns = [
        r"api[_-]?key",
        r"password",
        r"secret",
        r"token",
        r"bearer",
        r"authorization",
        r"\b[A-Za-z0-9]{32,}\b",  # Long random strings
    ]
    
    content_lower = content.lower()
    for pattern in sensitive_patterns:
        matches = re.findall(pattern, content_lower)
        # Allow pattern mentions but not actual values
        if matches:
            # Check it's not an actual secret (surrounded by = or :)
            for match in matches:
                if re.search(rf"{match}\s*[=:]\s*['\"]?\w+", content_lower):
                    raise AssertionError(
                        f"SECURITY: Potential sensitive data exposure! "
                        f"Pattern '{pattern}' with value found"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE ASSERTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def assert_latency_budget(
    operations: List[Dict[str, Any]],
    budget_ms: int,
    operation_key: str = "latency_ms"
) -> None:
    """
    Vérifie que le budget de latence n'est pas dépassé.
    """
    total_latency = sum(op.get(operation_key, 0) for op in operations)
    
    assert total_latency <= budget_ms, \
        f"Latency budget exceeded! Total: {total_latency}ms, Budget: {budget_ms}ms\n" \
        f"Breakdown: {[op.get(operation_key, 0) for op in operations]}"


def assert_p95_latency(
    latencies: List[int],
    max_p95_ms: int
) -> None:
    """
    Vérifie le percentile 95 des latences.
    """
    if not latencies:
        return
    
    sorted_latencies = sorted(latencies)
    p95_idx = int(len(sorted_latencies) * 0.95)
    p95 = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
    
    assert p95 <= max_p95_ms, \
        f"P95 latency too high: {p95}ms > {max_p95_ms}ms\n" \
        f"All latencies: {sorted_latencies}"


# ═══════════════════════════════════════════════════════════════════════════════
# IDEMPOTENCE ASSERTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def assert_idempotent(
    result1: Dict[str, Any],
    result2: Dict[str, Any],
    ignore_fields: List[str] = None
) -> None:
    """
    Vérifie que deux résultats sont identiques (idempotence).
    """
    ignore = set(ignore_fields or ["timestamp", "latency_ms", "proposal_id"])
    
    def clean(d: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in d.items() if k not in ignore}
    
    clean1 = clean(result1)
    clean2 = clean(result2)
    
    assert clean1 == clean2, \
        f"Results are not idempotent!\n" \
        f"Result 1: {clean1}\n" \
        f"Result 2: {clean2}\n" \
        f"Diff: {set(clean1.items()) ^ set(clean2.items())}"
