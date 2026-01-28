"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PRISM CONSENSUS CONTRACTS                            ║
║                                                                              ║
║  Schémas Pydantic pour validation fail-closed.                               ║
║  Toute entrée non conforme est rejetée immédiatement.                        ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator
import json
import re


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class DecisionTypeEnum(str, Enum):
    """Types de décisions valides."""
    SECURITY = "security"
    CRITICAL = "critical"
    SELF_IMPROVEMENT = "self_improvement"
    SYSTEM_MODIFICATION = "system_modification"
    DATA_ACCESS = "data_access"
    RESEARCH_VALIDATION = "research_validation"


class VoteVerdictEnum(str, Enum):
    """Types de verdicts valides."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


# Backward-compatible alias (single enum object)
VoteTypeEnum = VoteVerdictEnum


class ConsensusStatusEnum(str, Enum):
    """Statuts de consensus valides."""
    # NOTE: PENDING is internal-only and should not be exposed to user output.
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NO_CONSENSUS = "NO_CONSENSUS"
    INFRA_FAILURE = "INFRA_FAILURE"
    SKIPPED = "SKIPPED"


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class DecisionProposalSchema(BaseModel):
    """Schéma pour une proposition de décision."""
    decision_hash: str = Field(..., min_length=1, max_length=256)
    payload: Dict[str, Any]
    type: DecisionTypeEnum
    
    class Config:
        extra = "forbid"  # Rejeter les champs inconnus


class VoteSchema(BaseModel):
    """Schéma pour un vote."""
    vote: Optional[VoteVerdictEnum] = None
    reasoning: str = Field(default="", max_length=5000)
    timestamp: float = Field(..., gt=0)
    provider: str = Field(..., min_length=1, max_length=128)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risks_identified: List[str] = Field(default_factory=list)
    available: bool = True
    availability_reason: Optional[str] = None
    
    class Config:
        extra = "forbid"
    
    @root_validator(skip_on_failure=True)
    def enforce_availability(cls, values):
        available = values.get("available", True)
        vote = values.get("vote")
        if not available and vote is not None:
            raise ValueError("Unavailable votes must not include a verdict")
        if available and vote is None:
            raise ValueError("Available votes must include a verdict")
        return values


class ConsensusResultSchema(BaseModel):
    """Schéma pour le résultat d'un consensus."""
    proposal_id: str
    status: ConsensusStatusEnum
    approvals: int = Field(..., ge=0)
    rejections: int = Field(..., ge=0)
    abstentions: int = Field(..., ge=0)
    unavailable: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    decision_time_ms: Optional[int] = Field(None, ge=0)
    warnings: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"


class LLMVoteResponseSchema(BaseModel):
    """Schéma pour la réponse d'un LLM (vote)."""
    approve: bool
    reasoning: str = Field(..., max_length=2000)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risks_identified: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "ignore"  # Ignorer les champs supplémentaires du LLM
    
    @validator("reasoning")
    def reasoning_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Reasoning cannot be empty")
        return v.strip()


class ResearchDataSchema(BaseModel):
    """Schéma pour les données de recherche à valider."""
    source: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    results: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    collector: str = Field(..., description="MCP server who collected data")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    class Config:
        extra = "allow"


class ConsensusConfigSchema(BaseModel):
    """Schéma pour la configuration du consensus."""
    enabled: bool = True
    timeout_ms: int = Field(default=10000, ge=1000, le=60000)
    total_providers: int = Field(default=3, ge=2, le=10)
    quorum_ratio: float = Field(default=0.67, ge=0.5, le=1.0)
    
    # Modèles arbitres
    arbiter_model_1: str = Field(default="openrouter/anthropic/claude-3.5-sonnet")
    arbiter_model_2: str = Field(default="openrouter/openai/gpt-4o")
    arbiter_model_3: str = Field(default="openrouter/google/gemini-pro-1.5")
    
    # Actions critiques
    critical_action_patterns: List[str] = Field(default_factory=lambda: [
        "conclusion", "recommendation", "publish",
        "validate", "approve", "final", "decision"
    ])
    
    # Logging
    enable_audit_log: bool = True
    log_votes: bool = True
    
    class Config:
        extra = "forbid"


class ConsensusPolicySchema(BaseModel):
    """Schéma pour policy d'appel consensus."""
    action: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    decision_type: DecisionTypeEnum = DecisionTypeEnum.CRITICAL
    correlation_id: Optional[str] = None
    integrity_checks: bool = False
    timeout_ms: Optional[int] = Field(None, ge=1000, le=60000)
    
    class Config:
        extra = "forbid"


class ReliabilityTierEnum(str, Enum):
    """Reliability tiers for user-facing envelopes."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReliabilityTierSchema(BaseModel):
    """Reliability tier details."""
    tier: ReliabilityTierEnum
    claims: List[str] = Field(default_factory=list)
    rationale: str = Field(default="", max_length=2000)
    sources: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"


class ConsensusSummarySchema(BaseModel):
    """Consensus summary for the user envelope."""
    status: ConsensusStatusEnum
    quorum: Optional[str] = None
    votes_summary: Dict[str, int] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"


class ResponseEnvelopeSchema(BaseModel):
    """Fail-soft response envelope for critical outputs."""
    answer: str
    reliability_tiers: List[ReliabilityTierSchema] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    consensus: ConsensusSummarySchema
    debug_trace: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_strict(data: Any, schema: type) -> Any:
    """
    Valide strictement une entrée contre un schéma Pydantic.
    
    Args:
        data: Données à valider
        schema: Classe Pydantic
        
    Returns:
        Données validées (instance du schéma)
        
    Raises:
        ValueError: Si validation échoue (fail-closed)
    """
    try:
        if isinstance(data, dict):
            return schema(**data)
        elif isinstance(data, schema):
            return data
        else:
            raise ValueError(f"Expected dict or {schema.__name__}, got {type(data)}")
    except Exception as e:
        raise ValueError(f"Schema validation failed: {str(e)}")


def parse_llm_vote_response(json_string: str) -> LLMVoteResponseSchema:
    """
    Valide et parse une réponse JSON de LLM.
    
    Args:
        json_string: Réponse JSON du LLM
        
    Returns:
        Objet validé LLMVoteResponseSchema
        
    Raises:
        ValueError: Si parsing ou validation échoue (fail-closed)
    """
    try:
        # Extraire JSON si entouré de texte
        json_match = re.search(r'\{[\s\S]*\}', json_string)
        if not json_match:
            raise ValueError("No valid JSON object found in response")
        
        parsed = json.loads(json_match.group())
        return LLMVoteResponseSchema(**parsed)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse LLM vote response: {str(e)}")


def validate_research_data(data: Dict[str, Any]) -> ResearchDataSchema:
    """
    Valide des données de recherche collectées par un MCP.
    
    Args:
        data: Données de recherche
        
    Returns:
        ResearchDataSchema validé
        
    Raises:
        ValueError: Si validation échoue
    """
    return validate_strict(data, ResearchDataSchema)


def validate_consensus_config(config: Dict[str, Any]) -> ConsensusConfigSchema:
    """
    Valide la configuration du consensus.
    
    Args:
        config: Configuration
        
    Returns:
        ConsensusConfigSchema validé
    """
    return validate_strict(config, ConsensusConfigSchema)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

class AuditLogEntry(BaseModel):
    """Entrée de log d'audit pour traçabilité."""
    timestamp: float
    event_type: str
    proposal_id: Optional[str] = None
    provider: Optional[str] = None
    vote: Optional[VoteTypeEnum] = None
    status: Optional[ConsensusStatusEnum] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convertit en JSON pour logging."""
        return self.json(exclude_none=True)


class ResearchPipelineStep(BaseModel):
    """Étape du pipeline de recherche."""
    step_id: str
    step_name: str
    mcp_server: str
    input_query: str
    output_data: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> Optional[int]:
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return None


class ResearchDossier(BaseModel):
    """
    Dossier de recherche complet.
    
    "Evidence ne cherche pas, Evidence instruit un dossier."
    """
    dossier_id: str
    query: str
    created_at: float
    
    # Pipeline steps
    collection_steps: List[ResearchPipelineStep] = Field(default_factory=list)
    
    # Données collectées
    firecrawl_data: List[Dict[str, Any]] = Field(default_factory=list)
    playwright_data: List[Dict[str, Any]] = Field(default_factory=list)
    tavily_data: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Consensus
    consensus_proposals: List[str] = Field(default_factory=list)
    consensus_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Résultat final
    final_conclusion: Optional[str] = None
    confidence_score: float = 0.0
    status: str = "open"  # open, validating, closed
    
    def add_collection_data(self, source: str, data: Dict[str, Any]):
        """Ajoute des données collectées au dossier."""
        if source == "firecrawl":
            self.firecrawl_data.append(data)
        elif source == "playwright":
            self.playwright_data.append(data)
        elif source == "tavily":
            self.tavily_data.append(data)
        else:
            # Generic: add to tavily_data as catch-all
            self.tavily_data.append(data)
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Retourne toutes les données collectées."""
        return self.firecrawl_data + self.playwright_data + self.tavily_data
