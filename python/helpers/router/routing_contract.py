"""
Routing Contract — Strict schemas for deterministic routing.

All routing decisions must conform to these contracts.
No ambiguity, no free-form LLM output.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import hashlib
import json


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class RouteVerdict(str, Enum):
    """Final routing decision."""
    PROCEED = "proceed"                     # Route to intents
    NEEDS_CLARIFICATION = "needs_clarification"  # Ask user for more info
    NO_ROUTE = "no_route"                   # Cannot determine route
    REFUSE = "refuse"                       # Critical agent unavailable, refuse to proceed


class IntentName(str, Enum):
    """Available agent intents (profiles)."""
    FINANCE = "finance"
    SALES = "sales"
    LEGAL_SAFE = "legal_safe"
    MEDICAL = "medical"
    DEVELOPER = "developer"
    RESEARCHER = "researcher"
    MARKETING = "marketing"
    MULTITASK = "multitask"  # Fallback/general
    CONTRADICTOR = "contradictor"  # Special: challenge assumptions


class ConfidenceLevel(str, Enum):
    """Confidence in routing decision."""
    HIGH = "high"       # >= 0.8
    MEDIUM = "medium"   # >= 0.5
    LOW = "low"         # < 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE INTENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RouteIntent:
    """A single detected intent."""
    
    name: IntentName
    score: float  # 0.0 - 1.0
    matched_keywords: List[str] = field(default_factory=list)
    is_required: bool = False  # True if board-level/critical
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "score": round(self.score, 3),
            "matched_keywords": self.matched_keywords[:5],
            "is_required": self.is_required,
            "reason": self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouteIntent":
        return cls(
            name=IntentName(data["name"]),
            score=data["score"],
            matched_keywords=data.get("matched_keywords", []),
            is_required=data.get("is_required", False),
            reason=data.get("reason", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE DECISION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RouteDecision:
    """
    Complete routing decision — deterministic and strict.
    
    This is the OUTPUT of decide_route().
    No LLM judgment allowed in producing this.
    """
    
    # Primary decision
    verdict: RouteVerdict
    intents: List[RouteIntent] = field(default_factory=list)
    
    # Confidence
    confidence: float = 0.0  # Overall confidence 0.0-1.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    
    # Board-level flags
    is_board_level: bool = False  # Strategic/critical request
    requires_contradictor: bool = False  # Needs challenge/second opinion
    
    # Metadata
    reasons: List[str] = field(default_factory=list)
    policy_version: str = "1.0.0"
    
    # Clarification (if verdict == NEEDS_CLARIFICATION)
    clarification_prompt: str = ""
    missing_info: List[str] = field(default_factory=list)
    
    # Anti-injection
    injection_blocked: bool = False
    injection_attempt: str = ""
    
    # Traceability
    route_id: str = ""
    input_hash: str = ""
    
    def __post_init__(self):
        """Set derived fields."""
        if self.confidence >= 0.8:
            self.confidence_level = ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            self.confidence_level = ConfidenceLevel.MEDIUM
        else:
            self.confidence_level = ConfidenceLevel.LOW
    
    @property
    def primary_intent(self) -> Optional[IntentName]:
        """Get the highest-scoring intent."""
        if not self.intents:
            return None
        return max(self.intents, key=lambda x: x.score).name
    
    @property
    def intent_names(self) -> List[str]:
        """Get list of intent names for logging."""
        return [i.name.value for i in self.intents]
    
    @property
    def required_intents(self) -> List[RouteIntent]:
        """Get intents marked as required."""
        return [i for i in self.intents if i.is_required]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/storage."""
        return {
            "verdict": self.verdict.value,
            "intents": [i.to_dict() for i in self.intents],
            "confidence": round(self.confidence, 3),
            "confidence_level": self.confidence_level.value,
            "is_board_level": self.is_board_level,
            "requires_contradictor": self.requires_contradictor,
            "reasons": self.reasons,
            "policy_version": self.policy_version,
            "clarification_prompt": self.clarification_prompt,
            "missing_info": self.missing_info,
            "injection_blocked": self.injection_blocked,
            "route_id": self.route_id,
            "input_hash": self.input_hash,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouteDecision":
        """Deserialize from dict."""
        return cls(
            verdict=RouteVerdict(data["verdict"]),
            intents=[RouteIntent.from_dict(i) for i in data.get("intents", [])],
            confidence=data.get("confidence", 0.0),
            is_board_level=data.get("is_board_level", False),
            requires_contradictor=data.get("requires_contradictor", False),
            reasons=data.get("reasons", []),
            policy_version=data.get("policy_version", "1.0.0"),
            clarification_prompt=data.get("clarification_prompt", ""),
            missing_info=data.get("missing_info", []),
            injection_blocked=data.get("injection_blocked", False),
            injection_attempt=data.get("injection_attempt", ""),
            route_id=data.get("route_id", ""),
            input_hash=data.get("input_hash", ""),
        )
    
    def compute_hash(self) -> str:
        """
        Compute deterministic hash for snapshot testing.
        Excludes volatile fields (route_id).
        """
        stable_data = {
            "verdict": self.verdict.value,
            "intents": [(i.name.value, round(i.score, 2)) for i in self.intents],
            "is_board_level": self.is_board_level,
            "requires_contradictor": self.requires_contradictor,
            "injection_blocked": self.injection_blocked,
        }
        content = json.dumps(stable_data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT RESULT CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class AgentVerdict(str, Enum):
    """Agent's conclusion."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class RiskSeverity(str, Enum):
    """Risk level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AgentRisk:
    """A risk identified by an agent."""
    severity: RiskSeverity
    text: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"severity": self.severity.value, "text": self.text}


@dataclass
class AgentAssumption:
    """An assumption made by an agent."""
    id: Optional[str]
    text: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text}


@dataclass
class AgentArtifact:
    """An artifact produced by an agent."""
    type: str  # "pdf", "chart", "table", etc.
    ref: Optional[str] = None  # Path or ID
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "ref": self.ref}


@dataclass
class AgentResult:
    """
    Standardized output from any agent.
    
    All agents MUST return results conforming to this contract.
    This enables Judge step comparison and consensus.
    """
    
    # Identity
    agent: str  # Agent profile name
    
    # Verdict
    verdict: AgentVerdict
    confidence: float  # 0.0 - 1.0
    
    # Content
    key_points: List[str] = field(default_factory=list)  # 3-7 points
    assumptions: List[AgentAssumption] = field(default_factory=list)
    risks: List[AgentRisk] = field(default_factory=list)
    
    # Next steps
    what_i_need_next: List[str] = field(default_factory=list)
    
    # Artifacts
    artifacts: List[AgentArtifact] = field(default_factory=list)
    
    # Raw response (for fallback)
    raw_response: str = ""
    
    # Validation
    schema_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "verdict": self.verdict.value,
            "confidence": round(self.confidence, 3),
            "key_points": self.key_points,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "risks": [r.to_dict() for r in self.risks],
            "what_i_need_next": self.what_i_need_next,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "schema_valid": self.schema_valid,
            "validation_errors": self.validation_errors,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResult":
        """Parse from dict with validation."""
        try:
            return cls(
                agent=data.get("agent", "unknown"),
                verdict=AgentVerdict(data.get("verdict", "abstain")),
                confidence=float(data.get("confidence", 0.0)),
                key_points=data.get("key_points", [])[:7],
                assumptions=[
                    AgentAssumption(id=a.get("id"), text=a.get("text", ""))
                    for a in data.get("assumptions", [])
                ],
                risks=[
                    AgentRisk(
                        severity=RiskSeverity(r.get("severity", "low")),
                        text=r.get("text", "")
                    )
                    for r in data.get("risks", [])
                ],
                what_i_need_next=data.get("what_i_need_next", []),
                artifacts=[
                    AgentArtifact(type=a.get("type", ""), ref=a.get("ref"))
                    for a in data.get("artifacts", [])
                ],
                raw_response=data.get("raw_response", ""),
                schema_valid=True,
            )
        except Exception as e:
            # Return invalid result for logging
            return cls(
                agent=data.get("agent", "unknown"),
                verdict=AgentVerdict.ABSTAIN,
                confidence=0.0,
                schema_valid=False,
                validation_errors=[str(e)],
                raw_response=str(data)[:500],
            )
    
    @classmethod
    def create_abstain(cls, agent: str, reason: str) -> "AgentResult":
        """Create an abstain result when agent cannot process."""
        return cls(
            agent=agent,
            verdict=AgentVerdict.ABSTAIN,
            confidence=0.0,
            key_points=[f"Cannot process: {reason}"],
            what_i_need_next=[reason],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_route_decision(decision: RouteDecision) -> List[str]:
    """
    Validate a RouteDecision for completeness.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    if decision.verdict == RouteVerdict.PROCEED:
        if not decision.intents:
            errors.append("PROCEED verdict requires at least one intent")
        if decision.confidence < 0.3:
            errors.append("PROCEED verdict with very low confidence (<0.3)")
    
    if decision.verdict == RouteVerdict.NEEDS_CLARIFICATION:
        if not decision.clarification_prompt and not decision.missing_info:
            errors.append("NEEDS_CLARIFICATION requires clarification_prompt or missing_info")
    
    if decision.is_board_level:
        required = [i for i in decision.intents if i.is_required]
        if not required:
            errors.append("board_level=True but no required intents")
    
    for intent in decision.intents:
        if intent.score < 0.0 or intent.score > 1.0:
            errors.append(f"Intent {intent.name.value} has invalid score: {intent.score}")
    
    return errors


def validate_agent_result(result: AgentResult) -> List[str]:
    """
    Validate an AgentResult for completeness.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    if not result.agent:
        errors.append("agent field is required")
    
    if result.confidence < 0.0 or result.confidence > 1.0:
        errors.append(f"confidence must be 0.0-1.0, got {result.confidence}")
    
    if result.verdict != AgentVerdict.ABSTAIN:
        if len(result.key_points) < 1:
            errors.append("Non-abstain verdict requires at least 1 key point")
    
    for risk in result.risks:
        if not risk.text:
            errors.append("Risk must have text")
    
    return errors


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "RouteVerdict",
    "IntentName",
    "ConfidenceLevel",
    "AgentVerdict",
    "RiskSeverity",
    # Contracts
    "RouteIntent",
    "RouteDecision",
    "AgentResult",
    "AgentRisk",
    "AgentAssumption",
    "AgentArtifact",
    # Validation
    "validate_route_decision",
    "validate_agent_result",
]
