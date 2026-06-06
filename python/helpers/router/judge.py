"""
Judge Step — Pre-consensus contradiction detection.

The Judge analyzes outputs from multiple agents and:
1. Detects contradictions in assumptions/numbers
2. Identifies missing critical information
3. Determines if a second pass is needed
4. Prepares targeted instructions for each agent

This is NOT full consensus - it's a lightweight check before final response.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import re

from .routing_contract import (
    AgentResult,
    AgentVerdict,
    RouteDecision,
    IntentName,
)

logger = logging.getLogger("judge_step")


# ═══════════════════════════════════════════════════════════════════════════════
# JUDGE VERDICT
# ═══════════════════════════════════════════════════════════════════════════════

class JudgeVerdict(str, Enum):
    """Judge's decision on whether to proceed."""
    PROCEED = "proceed"                     # All good, continue to final response
    NEEDS_SECOND_PASS = "needs_second_pass" # Contradictions found, need clarification
    REFUSE_TO_CONCLUDE = "refuse_to_conclude"  # Critical info missing, cannot conclude


@dataclass
class SecondPassInstruction:
    """Instruction for an agent during second pass."""
    agent: str
    instruction: str
    priority: str = "high"  # high, medium, low
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "instruction": self.instruction,
            "priority": self.priority,
        }


@dataclass
class Contradiction:
    """A detected contradiction between agents."""
    agents: List[str]
    topic: str
    values: Dict[str, str]  # agent -> value
    severity: str = "medium"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agents": self.agents,
            "topic": self.topic,
            "values": self.values,
            "severity": self.severity,
        }


@dataclass
class JudgeResult:
    """
    Result of the judge step.
    
    Contains:
    - verdict: Whether to proceed, need second pass, or refuse
    - contradictions: List of detected contradictions
    - missing_info: Critical information that's missing
    - second_pass_instructions: What each agent should do in second pass
    """
    
    verdict: JudgeVerdict
    
    # Contradictions detected
    contradictions: List[Contradiction] = field(default_factory=list)
    
    # Missing critical info
    missing_info: List[str] = field(default_factory=list)
    missing_from_agents: Dict[str, List[str]] = field(default_factory=dict)
    
    # Verdict divergence
    verdict_divergence: bool = False
    verdicts_by_agent: Dict[str, str] = field(default_factory=dict)
    
    # Second pass instructions
    second_pass_instructions: List[SecondPassInstruction] = field(default_factory=list)
    
    # Metadata
    reasons: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "missing_info": self.missing_info,
            "missing_from_agents": self.missing_from_agents,
            "verdict_divergence": self.verdict_divergence,
            "verdicts_by_agent": self.verdicts_by_agent,
            "second_pass_instructions": [i.to_dict() for i in self.second_pass_instructions],
            "reasons": self.reasons,
            "confidence": self.confidence,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN JUDGE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def judge_step(
    agent_results: List[AgentResult],
    route_decision: RouteDecision,
    strict_mode: bool = False,
) -> JudgeResult:
    """
    Analyze agent outputs and determine if we can proceed.
    
    Args:
        agent_results: List of AgentResult from subordinate agents
        route_decision: The original routing decision
        strict_mode: If True, any contradiction = REFUSE
        
    Returns:
        JudgeResult with verdict and instructions
    """
    reasons: List[str] = []
    contradictions: List[Contradiction] = []
    missing_info: List[str] = []
    missing_from_agents: Dict[str, List[str]] = {}
    second_pass: List[SecondPassInstruction] = []
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Check for schema failures
    # ─────────────────────────────────────────────────────────────────────────
    
    valid_results = [r for r in agent_results if r.schema_valid]
    invalid_results = [r for r in agent_results if not r.schema_valid]
    
    if invalid_results:
        for inv in invalid_results:
            reasons.append(f"Agent {inv.agent} returned invalid schema")
            second_pass.append(SecondPassInstruction(
                agent=inv.agent,
                instruction="Reformuler la réponse avec le format standard",
                priority="high",
            ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Check verdict divergence
    # ─────────────────────────────────────────────────────────────────────────
    
    verdicts = {r.agent: r.verdict.value for r in valid_results}
    unique_verdicts = set(verdicts.values())
    
    verdict_divergence = False
    if len(unique_verdicts) > 1:
        # Check if it's approve vs reject (serious) or just abstain mixed in
        has_approve = AgentVerdict.APPROVE.value in unique_verdicts
        has_reject = AgentVerdict.REJECT.value in unique_verdicts
        
        if has_approve and has_reject:
            verdict_divergence = True
            reasons.append("CRITICAL: Agents disagree (approve vs reject)")
            
            # Add instructions to resolve
            for agent, verdict in verdicts.items():
                if verdict == AgentVerdict.APPROVE.value:
                    second_pass.append(SecondPassInstruction(
                        agent=agent,
                        instruction="Un autre agent a rejeté. Vérifier les hypothèses et confirmer.",
                        priority="high",
                    ))
                elif verdict == AgentVerdict.REJECT.value:
                    second_pass.append(SecondPassInstruction(
                        agent=agent,
                        instruction="Un autre agent a approuvé. Préciser les raisons du rejet.",
                        priority="high",
                    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Detect numerical contradictions
    # ─────────────────────────────────────────────────────────────────────────
    
    numerical_contradictions = _detect_numerical_contradictions(valid_results)
    contradictions.extend(numerical_contradictions)
    
    for c in numerical_contradictions:
        reasons.append(f"Contradiction on '{c.topic}': {c.values}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Check for missing critical info
    # ─────────────────────────────────────────────────────────────────────────
    
    for result in valid_results:
        if result.what_i_need_next:
            missing_from_agents[result.agent] = result.what_i_need_next
            missing_info.extend(result.what_i_need_next)
            reasons.append(f"Agent {result.agent} needs: {result.what_i_need_next[:2]}")
    
    # Deduplicate missing info
    missing_info = list(set(missing_info))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Check assumption conflicts
    # ─────────────────────────────────────────────────────────────────────────
    
    assumption_conflicts = _detect_assumption_conflicts(valid_results)
    if assumption_conflicts:
        reasons.append(f"Assumption conflicts detected: {len(assumption_conflicts)}")
        for conflict in assumption_conflicts:
            second_pass.append(SecondPassInstruction(
                agent=conflict["agent"],
                instruction=f"Vérifier l'hypothèse: {conflict['assumption'][:100]}",
                priority="medium",
            ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Determine verdict
    # ─────────────────────────────────────────────────────────────────────────
    
    verdict = _determine_judge_verdict(
        contradictions=contradictions,
        missing_info=missing_info,
        verdict_divergence=verdict_divergence,
        is_board_level=route_decision.is_board_level,
        strict_mode=strict_mode,
    )
    
    # Calculate confidence
    if verdict == JudgeVerdict.PROCEED:
        confidence = 0.9 - (len(contradictions) * 0.1) - (len(missing_info) * 0.05)
    elif verdict == JudgeVerdict.NEEDS_SECOND_PASS:
        confidence = 0.5
    else:
        confidence = 0.2
    
    return JudgeResult(
        verdict=verdict,
        contradictions=contradictions,
        missing_info=missing_info,
        missing_from_agents=missing_from_agents,
        verdict_divergence=verdict_divergence,
        verdicts_by_agent=verdicts,
        second_pass_instructions=second_pass,
        reasons=reasons,
        confidence=max(confidence, 0.0),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_numerical_contradictions(results: List[AgentResult]) -> List[Contradiction]:
    """
    Detect contradictions in numerical values across agents.
    
    Looks for same concepts with different numbers.
    """
    contradictions = []
    
    # Extract numbers with context from key_points
    agent_numbers: Dict[str, Dict[str, str]] = {}  # agent -> {topic: value}
    
    number_pattern = re.compile(
        r'(\d+(?:[.,]\d+)?)\s*(%|€|M€|K€|millions?|milliards?|billions?|k|m|b)?',
        re.IGNORECASE
    )
    
    for result in results:
        agent_numbers[result.agent] = {}
        
        for point in result.key_points:
            # Find numbers in the key point
            matches = number_pattern.findall(point)
            if matches:
                # Use first 30 chars as topic
                topic = point[:30].lower().strip()
                value = matches[0][0] + (matches[0][1] or '')
                agent_numbers[result.agent][topic] = value
    
    # Compare across agents
    all_topics: Set[str] = set()
    for numbers in agent_numbers.values():
        all_topics.update(numbers.keys())
    
    for topic in all_topics:
        values_for_topic: Dict[str, str] = {}
        
        for agent, numbers in agent_numbers.items():
            if topic in numbers:
                values_for_topic[agent] = numbers[topic]
        
        # If multiple agents have this topic with different values
        if len(values_for_topic) > 1:
            unique_values = set(values_for_topic.values())
            if len(unique_values) > 1:
                # Check if difference is significant (>10%)
                try:
                    nums = [float(v.replace(',', '.').rstrip('%€MKmk')) 
                            for v in unique_values]
                    if max(nums) > 0:
                        diff_pct = (max(nums) - min(nums)) / max(nums)
                        if diff_pct > 0.1:  # >10% difference
                            contradictions.append(Contradiction(
                                agents=list(values_for_topic.keys()),
                                topic=topic,
                                values=values_for_topic,
                                severity="high" if diff_pct > 0.3 else "medium",
                            ))
                except (ValueError, ZeroDivisionError):
                    pass
    
    return contradictions


def _detect_assumption_conflicts(results: List[AgentResult]) -> List[Dict[str, str]]:
    """
    Detect conflicting assumptions across agents.
    """
    conflicts = []
    
    # Collect all assumptions
    all_assumptions: List[Tuple[str, str]] = []  # (agent, assumption_text)
    
    for result in results:
        for assumption in result.assumptions:
            all_assumptions.append((result.agent, assumption.text.lower()))
    
    # Simple conflict detection: opposite keywords
    opposites = [
        ("croissance", "décroissance"),
        ("augment", "diminu"),
        ("positif", "négatif"),
        ("hausse", "baisse"),
        ("increase", "decrease"),
        ("growth", "decline"),
        ("approve", "reject"),
    ]
    
    for i, (agent1, text1) in enumerate(all_assumptions):
        for agent2, text2 in all_assumptions[i+1:]:
            if agent1 == agent2:
                continue
            
            for word1, word2 in opposites:
                if (word1 in text1 and word2 in text2) or (word2 in text1 and word1 in text2):
                    conflicts.append({
                        "agent": agent1,
                        "assumption": text1,
                        "conflicting_agent": agent2,
                        "conflicting_assumption": text2,
                    })
                    break
    
    return conflicts


def _determine_judge_verdict(
    contradictions: List[Contradiction],
    missing_info: List[str],
    verdict_divergence: bool,
    is_board_level: bool,
    strict_mode: bool,
) -> JudgeVerdict:
    """Determine the final judge verdict."""
    
    # Strict mode: any issue = refuse
    if strict_mode:
        if contradictions or verdict_divergence:
            return JudgeVerdict.REFUSE_TO_CONCLUDE
        if missing_info:
            return JudgeVerdict.NEEDS_SECOND_PASS
        return JudgeVerdict.PROCEED
    
    # High severity contradictions on board-level
    high_severity = [c for c in contradictions if c.severity == "high"]
    if is_board_level and high_severity:
        return JudgeVerdict.REFUSE_TO_CONCLUDE
    
    # Verdict divergence = need second pass
    if verdict_divergence:
        return JudgeVerdict.NEEDS_SECOND_PASS
    
    # Multiple contradictions = need second pass
    if len(contradictions) >= 2:
        return JudgeVerdict.NEEDS_SECOND_PASS
    
    # Critical missing info
    critical_keywords = ["valuation", "valorisation", "risk", "risque", "legal", "juridique"]
    critical_missing = any(
        any(kw in info.lower() for kw in critical_keywords)
        for info in missing_info
    )
    if critical_missing and is_board_level:
        return JudgeVerdict.NEEDS_SECOND_PASS
    
    # Default: proceed
    return JudgeVerdict.PROCEED


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "JudgeVerdict",
    "JudgeResult",
    "SecondPassInstruction",
    "Contradiction",
    "judge_step",
]
