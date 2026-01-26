"""
Deterministic Router — Policy-driven intent detection.

This is the CORE of the routing system.
- Pure function: same input → same output (STRICTLY DETERMINISTIC)
- No LLM judgment
- No embeddings
- No randomness (no uuid, no datetime)
- Fully testable

Usage:
    from python.helpers.router import decide_route
    
    decision = decide_route("Analyse financière du deal M&A")
    print(decision.intents)  # [finance, legal_safe]
    print(decision.is_board_level)  # True
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple

from .routing_contract import (
    RouteDecision,
    RouteIntent,
    RouteVerdict,
    IntentName,
    validate_route_decision,
)
from .policy import (
    Keyword,
    IntentPolicy,
    INTENT_POLICIES,
    BOARD_LEVEL_KEYWORDS,
    BOARD_LEVEL_THRESHOLD,
    BOARD_LEVEL_CORE_INTENTS,
    MULTI_INTENT_RULES,
    INJECTION_PATTERNS,
    POLICY_VERSION,
)

logger = logging.getLogger("deterministic_router")


# ═══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _canonicalize_text(text: str) -> str:
    """
    Canonicalize text for deterministic hashing.
    
    - lowercase
    - strip leading/trailing whitespace
    - collapse multiple whitespace to single space
    """
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def _stable_route_id(canonical_text: str) -> str:
    """
    Generate stable route_id from canonical text.
    
    Uses SHA256 for cryptographic determinism.
    """
    return hashlib.sha256(canonical_text.encode('utf-8')).hexdigest()[:8]


def _stable_input_hash(canonical_text: str) -> str:
    """
    Generate stable input_hash from canonical text.
    
    Uses SHA256 (not MD5) for consistency.
    """
    return hashlib.sha256(canonical_text.encode('utf-8')).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def decide_route(
    text: str,
    available_agents: Optional[Set[IntentName]] = None,
    force_board_level: bool = False,
    min_confidence: float = 0.25,
) -> RouteDecision:
    """
    Determine routing decision for a given text.
    
    This function is STRICTLY DETERMINISTIC:
    - Same input text → same route_id, input_hash, intents, verdict
    - No randomness, no uuid, no datetime
    
    Args:
        text: User request text
        available_agents: Set of available agent intents (None = all available)
        force_board_level: Force board-level mode
        min_confidence: Minimum confidence to proceed
        
    Returns:
        RouteDecision with verdict, intents, and metadata
    """
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 0: Canonicalize and generate deterministic IDs
    # ─────────────────────────────────────────────────────────────────────────
    
    canonical_text = _canonicalize_text(text)
    route_id = _stable_route_id(canonical_text)
    input_hash = _stable_input_hash(canonical_text)
    
    # For pattern matching, use canonical text
    text_lower = canonical_text
    
    # Default available agents
    if available_agents is None:
        available_agents = set(IntentName)
    
    reasons: List[str] = []
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Anti-injection check
    # ─────────────────────────────────────────────────────────────────────────
    
    injection_blocked, injection_attempt = _check_injection(text_lower)
    if injection_blocked:
        reasons.append(f"Injection pattern detected: {injection_attempt[:50]}")
        logger.warning(f"[{route_id}] Injection detected: {injection_attempt[:100]}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Score all intents (including unavailable for critical check)
    # ─────────────────────────────────────────────────────────────────────────
    
    intent_scores: Dict[IntentName, Tuple[float, List[str]]] = {}
    unavailable_critical_intents: List[IntentName] = []
    
    for intent_name, policy in INTENT_POLICIES.items():
        score, matched = _score_intent(text_lower, policy)
        
        # Apply blockers
        if score > 0 and policy.blockers:
            for blocker in policy.blockers:
                if blocker in text_lower:
                    score *= 0.1  # Heavily penalize
                    reasons.append(f"Intent {intent_name.value} blocked by '{blocker}'")
                    break
        
        if score >= policy.min_score_threshold:
            # Check if this critical intent is unavailable
            if intent_name not in available_agents:
                if policy.is_critical:
                    unavailable_critical_intents.append(intent_name)
                    reasons.append(f"Critical intent {intent_name.value} detected but unavailable")
                continue  # Don't add to scores if unavailable
            
            intent_scores[intent_name] = (score, matched)
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Check board-level triggers
    # ─────────────────────────────────────────────────────────────────────────
    
    board_score = _score_board_level(text_lower)
    is_board_level = force_board_level or board_score >= BOARD_LEVEL_THRESHOLD
    
    if is_board_level:
        reasons.append(f"Board-level triggered (score={board_score:.1f})")
        
        # Add core intents if board-level
        for core_intent in BOARD_LEVEL_CORE_INTENTS:
            if core_intent in available_agents and core_intent not in intent_scores:
                intent_scores[core_intent] = (
                    BOARD_LEVEL_THRESHOLD * 0.5,  # Base score
                    ["board-level-core"]
                )
                reasons.append(f"Added {core_intent.value} as board-level core")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Apply multi-intent rules (ONLY if board-level for legal rule)
    # ─────────────────────────────────────────────────────────────────────────
    
    detected_intents = set(intent_scores.keys())
    
    for rule in MULTI_INTENT_RULES:
        # Check if rule requires board-level
        requires_board = getattr(rule, 'require_board_level', False)
        if requires_board and not is_board_level:
            continue  # Skip this rule if not board-level
        
        should_add = False
        
        if rule.condition == "all":
            should_add = rule.if_intents.issubset(detected_intents)
        elif rule.condition == "any":
            should_add = bool(rule.if_intents & detected_intents)
        
        if should_add and rule.add_intent in available_agents:
            if rule.add_intent not in intent_scores:
                intent_scores[rule.add_intent] = (3.0, ["multi-intent-rule"])
                reasons.append(f"Added {rule.add_intent.value}: {rule.reason}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Build RouteIntent list
    # ─────────────────────────────────────────────────────────────────────────
    
    intents: List[RouteIntent] = []
    
    for intent_name, (score, matched) in intent_scores.items():
        policy = INTENT_POLICIES.get(intent_name)
        
        # Normalize score to 0-1 range
        normalized_score = min(score / 10.0, 1.0)
        
        intents.append(RouteIntent(
            name=intent_name,
            score=normalized_score,
            matched_keywords=matched[:5],
            is_required=policy.is_critical if policy else False,
            reason=f"Score {score:.1f} from {len(matched)} matches",
        ))
    
    # Sort by score descending (deterministic due to stable sorting)
    intents.sort(key=lambda x: (-x.score, x.name.value))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Check unavailable critical intents
    # ─────────────────────────────────────────────────────────────────────────
    
    if unavailable_critical_intents:
        # Ensure we have at least one intent for contract compliance
        if not intents:
            intents = [RouteIntent(
                name=IntentName.MULTITASK,
                score=0.1,
                matched_keywords=[],
                is_required=False,
                reason="fallback (critical unavailable)",
            )]
        
        return RouteDecision(
            verdict=RouteVerdict.REFUSE,
            intents=intents,
            routing_strength=0.0,
            is_board_level=is_board_level,
            requires_contradictor=False,
            reasons=reasons + [f"Critical agents unavailable: {[i.value for i in unavailable_critical_intents]}"],
            policy_version=POLICY_VERSION,
            clarification_prompt=f"Cette requête nécessite l'agent {unavailable_critical_intents[0].value} qui est indisponible.",
            missing_info=[f"agent_{i.value}" for i in unavailable_critical_intents],
            injection_blocked=injection_blocked,
            injection_attempt=injection_attempt if injection_blocked else "",
            route_id=route_id,
            input_hash=input_hash,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Handle injection enforcement (SECURITY DECISION)
    # ─────────────────────────────────────────────────────────────────────────
    
    if injection_blocked:
        # Determine if this is a HIGH-STAKES context
        # High-stakes = board-level OR critical intent OR strategic signal
        has_critical_intent = any(
            i.name in {IntentName.LEGAL_SAFE, IntentName.MEDICAL, IntentName.RESEARCHER}
            for i in intents
        )
        
        # Strategic signal: high routing_strength + finance/legal
        # This catches due diligence, cession, JV even without board-level trigger
        top_score = intents[0].score if intents else 0.0
        has_strategic_signal = (
            top_score >= 0.3 and  # Normalized 0.3 = raw 3.0+
            any(i.name in {IntentName.FINANCE, IntentName.LEGAL_SAFE} for i in intents)
        )
        
        is_high_stakes = is_board_level or has_critical_intent or has_strategic_signal
        
        if is_high_stakes:
            # HIGH-STAKES + INJECTION → ALWAYS NEEDS_CLARIFICATION
            # This is a hard security rule, not a soft preference
            if not intents:
                intents = [RouteIntent(
                    name=IntentName.MULTITASK,
                    score=0.3,
                    matched_keywords=[],
                    is_required=False,
                    reason="fallback (injection + high-stakes)",
                )]
            
            clarification_msg = (
                "⚠️ Une instruction de contournement a été détectée dans votre demande. "
                "Pour des raisons de sécurité, veuillez reformuler sans instructions "
                "d'override (ex: 'ignore les règles', 'ne pas appeler legal')."
            )
            
            return RouteDecision(
                verdict=RouteVerdict.NEEDS_CLARIFICATION,
                intents=intents,
                routing_strength=0.3,
                is_board_level=is_board_level,
                requires_contradictor=False,
                reasons=reasons + [f"HIGH-STAKES injection blocked: {injection_attempt[:30]}"],
                policy_version=POLICY_VERSION,
                clarification_prompt=clarification_msg,
                missing_info=["reformulation_sans_override"],
                injection_blocked=True,
                injection_attempt=injection_attempt,
                route_id=route_id,
                input_hash=input_hash,
            )
        
        # LOW-STAKES injection: proceed but log + ignore override instruction
        # The injection is flagged but we route normally based on keywords
        reasons.append("Injection detected (low-stakes), routing on keywords only")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8: Determine verdict
    # ─────────────────────────────────────────────────────────────────────────
    
    verdict, clarification, missing = _determine_verdict(
        intents=intents,
        is_board_level=is_board_level,
        available_agents=available_agents,
        min_confidence=min_confidence,
        text=text,
    )
    
    if verdict != RouteVerdict.PROCEED:
        reasons.append(f"Verdict={verdict.value}: {clarification or 'See missing_info'}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9: CONTRACT ENFORCEMENT - PROCEED must have intents
    # ─────────────────────────────────────────────────────────────────────────
    
    if verdict == RouteVerdict.PROCEED and not intents:
        # Inject MULTITASK as fallback to satisfy contract
        intents = [RouteIntent(
            name=IntentName.MULTITASK,
            score=0.3,
            matched_keywords=[],
            is_required=False,
            reason="fallback (no specific intent detected)",
        )]
        reasons.append("Added MULTITASK as fallback (contract enforcement)")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 10: Calculate routing_strength (coverage score, NOT probability)
    # ─────────────────────────────────────────────────────────────────────────
    
    if intents:
        # Weighted average of top intents + floor boost if above threshold
        top_scores = [i.score for i in intents[:3]]
        base_strength = sum(top_scores) / len(top_scores)
        
        # If primary intent exceeded its policy threshold, boost floor to 0.65
        # This prevents "low confidence" on clearly matched intents
        primary_exceeded_threshold = any(
            i.score >= 0.3 for i in intents[:1]  # Primary scored 3.0+ raw
        )
        if primary_exceeded_threshold:
            routing_strength = max(base_strength, 0.65)
        else:
            routing_strength = base_strength
    else:
        routing_strength = 0.0
    
    # Boost for board-level (more intents = better coverage)
    if is_board_level and len(intents) >= 2:
        routing_strength = min(routing_strength * 1.1, 0.95)
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 11: Determine if contradictor needed
    # ─────────────────────────────────────────────────────────────────────────
    
    requires_contradictor = is_board_level and len(intents) >= 2
    
    if requires_contradictor:
        reasons.append("Contradictor required for board-level multi-intent")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 12: Build final decision
    # ─────────────────────────────────────────────────────────────────────────
    
    decision = RouteDecision(
        verdict=verdict,
        intents=intents,
        routing_strength=routing_strength,
        is_board_level=is_board_level,
        requires_contradictor=requires_contradictor,
        reasons=reasons,
        policy_version=POLICY_VERSION,
        clarification_prompt=clarification,
        missing_info=missing,
        injection_blocked=injection_blocked,
        injection_attempt=injection_attempt if injection_blocked else "",
        route_id=route_id,
        input_hash=input_hash,
    )
    
    # Validate contract
    errors = validate_route_decision(decision)
    if errors:
        logger.error(f"[{route_id}] Contract violation: {errors}")
    
    # Log decision (no sensitive data)
    logger.info(
        f"[{route_id}] Route: {verdict.value} | "
        f"Intents: {[i.name.value for i in intents]} | "
        f"Board: {is_board_level} | Strength: {routing_strength:.2f} | "
        f"InjBlocked: {injection_blocked}"
    )
    
    return decision


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _score_intent(text: str, policy: IntentPolicy) -> Tuple[float, List[str]]:
    """
    Calculate score for a single intent.
    
    Returns:
        (score, matched_keywords)
    """
    score = 0.0
    matched: List[str] = []
    
    for kw in policy.keywords:
        if kw.use_boundary:
            pattern = r'\b' + re.escape(kw.word) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                if kw.is_negative:
                    score -= kw.weight
                else:
                    score += kw.weight
                    matched.append(kw.word)
        else:
            if kw.word.lower() in text:
                if kw.is_negative:
                    score -= kw.weight
                else:
                    score += kw.weight
                    matched.append(kw.word)
    
    return max(score, 0.0), matched


def _score_board_level(text: str) -> float:
    """Calculate board-level score."""
    score = 0.0
    
    for kw in BOARD_LEVEL_KEYWORDS:
        if kw.use_boundary:
            pattern = r'\b' + re.escape(kw.word) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                score += kw.weight
        else:
            if kw.word.lower() in text:
                score += kw.weight
    
    return score


def _check_injection(text: str) -> Tuple[bool, str]:
    """
    Check for prompt injection attempts.
    
    Only matches override/disable patterns, not benign roleplay.
    
    Returns:
        (is_blocked, matched_pattern)
    """
    for pattern in INJECTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group(0)
    
    return False, ""


def _determine_verdict(
    intents: List[RouteIntent],
    is_board_level: bool,
    available_agents: Set[IntentName],
    min_confidence: float,
    text: str,
) -> Tuple[RouteVerdict, str, List[str]]:
    """
    Determine the final verdict.
    
    Returns:
        (verdict, clarification_prompt, missing_info)
    """
    # No intents detected
    if not intents:
        # Check if text is too short/vague
        if len(text.split()) < 3:
            return (
                RouteVerdict.NEEDS_CLARIFICATION,
                "Votre demande est trop courte. Pouvez-vous préciser ce que vous souhaitez?",
                ["context", "objective"],
            )
        
        # Will fallback to MULTITASK in contract enforcement
        return RouteVerdict.PROCEED, "", []
    
    # Check if critical intents are available
    required_intents = [i for i in intents if i.is_required]
    for req_intent in required_intents:
        if req_intent.name not in available_agents:
            return (
                RouteVerdict.REFUSE,
                f"L'agent {req_intent.name.value} est requis mais indisponible. "
                f"Cette requête ne peut pas être traitée en toute sécurité.",
                [f"agent_{req_intent.name.value}"],
            )
    
    # Board-level with insufficient coverage
    if is_board_level:
        covered_core = sum(
            1 for i in intents 
            if i.name in BOARD_LEVEL_CORE_INTENTS
        )
        if covered_core < 2:
            return (
                RouteVerdict.NEEDS_CLARIFICATION,
                "Cette décision stratégique nécessite plus de contexte. "
                "Quels aspects souhaitez-vous analyser (financier, commercial, juridique)?",
                ["domain_focus", "decision_criteria"],
            )
    
    # Low confidence
    top_confidence = intents[0].score if intents else 0.0
    if top_confidence < min_confidence:
        return (
            RouteVerdict.NEEDS_CLARIFICATION,
            "Je ne suis pas certain de comprendre votre demande. "
            "Pouvez-vous reformuler ou préciser le domaine concerné?",
            ["domain", "specific_question"],
        )
    
    # All good
    return RouteVerdict.PROCEED, "", []


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_primary_intent(text: str) -> Optional[IntentName]:
    """
    Quick helper to get the primary intent.
    
    Returns:
        Primary IntentName or None
    """
    decision = decide_route(text)
    return decision.primary_intent


def should_involve_legal(text: str) -> bool:
    """Check if legal_safe should be involved."""
    decision = decide_route(text)
    return any(i.name == IntentName.LEGAL_SAFE for i in decision.intents)


def is_board_level_request(text: str) -> bool:
    """Check if request is board-level."""
    decision = decide_route(text)
    return decision.is_board_level


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "decide_route",
    "get_primary_intent",
    "should_involve_legal",
    "is_board_level_request",
    "_canonicalize_text",  # Exposed for testing
    "_stable_route_id",    # Exposed for testing
    "_stable_input_hash",  # Exposed for testing
]
