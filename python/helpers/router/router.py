"""
Deterministic Router — Policy-driven intent detection.

This is the CORE of the routing system.
- Pure function: same input → same output (deterministic)
- No LLM judgment
- No embeddings
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
import uuid
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
# MAIN ROUTING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def decide_route(
    text: str,
    available_agents: Optional[Set[IntentName]] = None,
    force_board_level: bool = False,
    min_confidence: float = 0.25,  # Lower threshold for single-intent
) -> RouteDecision:
    """
    Determine routing decision for a given text.
    
    This function is DETERMINISTIC: same input → same output.
    
    Args:
        text: User request text
        available_agents: Set of available agent intents (None = all available)
        force_board_level: Force board-level mode
        min_confidence: Minimum confidence to proceed
        
    Returns:
        RouteDecision with verdict, intents, and metadata
    """
    # Generate route ID and input hash
    route_id = str(uuid.uuid4())[:8]
    input_hash = hashlib.md5(text.encode()).hexdigest()[:12]
    
    # Normalize text
    text_lower = text.lower().strip()
    
    # Default available agents
    if available_agents is None:
        available_agents = set(IntentName)
    
    reasons: List[str] = []
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Anti-injection check
    # ─────────────────────────────────────────────────────────────────────────
    
    injection_blocked, injection_attempt = _check_injection(text_lower)
    if injection_blocked:
        reasons.append(f"Injection attempt blocked: {injection_attempt[:50]}")
        logger.warning(f"[{route_id}] Injection blocked: {injection_attempt[:100]}")
    
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
    # STEP 4: Apply multi-intent rules
    # ─────────────────────────────────────────────────────────────────────────
    
    detected_intents = set(intent_scores.keys())
    
    for rule in MULTI_INTENT_RULES:
        should_add = False
        
        if rule.condition == "all":
            should_add = rule.if_intents.issubset(detected_intents)
        elif rule.condition == "any":
            should_add = bool(rule.if_intents & detected_intents)
        
        if should_add and rule.add_intent in available_agents:
            if rule.add_intent not in intent_scores:
                # Add with moderate score
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
    
    # Sort by score descending
    intents.sort(key=lambda x: x.score, reverse=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Check unavailable critical intents
    # ─────────────────────────────────────────────────────────────────────────
    
    if unavailable_critical_intents:
        # Critical intent needed but not available = REFUSE
        return RouteDecision(
            verdict=RouteVerdict.REFUSE,
            intents=intents,
            confidence=0.0,
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
    # STEP 7: Determine verdict
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
    # STEP 8: Calculate overall confidence
    # ─────────────────────────────────────────────────────────────────────────
    
    if intents:
        # Weighted average of top intents
        top_scores = [i.score for i in intents[:3]]
        confidence = sum(top_scores) / len(top_scores)
    else:
        confidence = 0.0
    
    # Boost confidence for board-level (more intents = more thorough)
    if is_board_level and len(intents) >= 2:
        confidence = min(confidence * 1.1, 0.95)
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9: Determine if contradictor needed
    # ─────────────────────────────────────────────────────────────────────────
    
    requires_contradictor = is_board_level and len(intents) >= 2
    
    if requires_contradictor:
        reasons.append("Contradictor required for board-level multi-intent")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 10: Build final decision
    # ─────────────────────────────────────────────────────────────────────────
    
    decision = RouteDecision(
        verdict=verdict,
        intents=intents,
        confidence=confidence,
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
    
    # Validate
    errors = validate_route_decision(decision)
    if errors:
        logger.warning(f"[{route_id}] Validation errors: {errors}")
    
    # Log decision
    logger.info(
        f"[{route_id}] Route: {verdict.value} | "
        f"Intents: {[i.name.value for i in intents]} | "
        f"Board: {is_board_level} | Conf: {confidence:.2f}"
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
        
        # Fallback to multitask
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
]
