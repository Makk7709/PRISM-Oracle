"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    STRATEGIC PIPELINE — ROUTER INTEGRATION                    ║
║                                                                              ║
║  Intègre le contrat stratégique dans le pipeline de routage Evidence.        ║
║                                                                              ║
║  FLOW:                                                                       ║
║  1. detect_strategic_request() → Classification CRITIQUE                     ║
║  2. enrich_route_decision() → Force agents requis                           ║
║  3. validate_strategic_response() → FAIL_CLOSED si sourcing insuffisant      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from python.helpers.router.routing_contract import (
    RouteDecision,
    RouteIntent,
    RouteVerdict,
    IntentName,
)
from python.helpers.strategic_contract import (
    StrategicDocumentType,
    SourceType,
    Criticality,
    StrategicDecision,
    StrategicValidationResult,
    detect_strategic_document_type,
    validate_strategic_output,
    create_strategic_fail_closed,
    is_strategic_request,
    get_required_agents,
    DOCUMENT_REQUIREMENTS,
)

logger = logging.getLogger("strategic_pipeline")


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGIC ROUTE CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategicRouteContext:
    """
    Context for strategic document requests.
    
    Attached to RouteDecision to carry strategic metadata through the pipeline.
    """
    is_strategic: bool = False
    document_types: List[StrategicDocumentType] = field(default_factory=list)
    criticality: Criticality = Criticality.LOW
    required_agents: List[str] = field(default_factory=list)
    source_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Validation state
    validation_enforced: bool = True  # If True, FAIL_CLOSED on sourcing failure
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_strategic": self.is_strategic,
            "document_types": [dt.value for dt in self.document_types],
            "criticality": self.criticality.value,
            "required_agents": self.required_agents,
            "source_requirements": self.source_requirements,
            "validation_enforced": self.validation_enforced,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN INTEGRATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def detect_strategic_context(query: str) -> StrategicRouteContext:
    """
    Detect if a query is a strategic document request.
    
    Called early in the routing pipeline to enrich the route decision.
    
    Args:
        query: User's request text
        
    Returns:
        StrategicRouteContext with detection results
    """
    is_strat, doc_types, criticality = is_strategic_request(query)
    
    if not is_strat:
        return StrategicRouteContext(is_strategic=False)
    
    # Get required agents for this document type
    required = get_required_agents(doc_types)
    
    # Get source requirements
    reqs = {}
    for dt in doc_types:
        if dt in DOCUMENT_REQUIREMENTS:
            req = DOCUMENT_REQUIREMENTS[dt]
            reqs[dt.value] = {
                "min_sources": req.min_sources,
                "min_public_sources": req.min_public_sources,
                "require_tam_sam_som": req.require_tam_sam_som,
                "require_competitor_data": req.require_competitor_data,
                "require_alternatives": req.require_alternatives,
            }
    
    logger.info(
        f"Strategic request detected: types={[dt.value for dt in doc_types]}, "
        f"criticality={criticality.value}, agents={required}"
    )
    
    return StrategicRouteContext(
        is_strategic=True,
        document_types=doc_types,
        criticality=criticality,
        required_agents=required,
        source_requirements=reqs,
        validation_enforced=True,
    )


def enrich_route_decision(
    decision: RouteDecision,
    strategic_context: StrategicRouteContext,
) -> RouteDecision:
    """
    Enrich a RouteDecision with strategic requirements.
    
    Called after initial routing to add strategic constraints:
    - Forces is_board_level = True for HIGH criticality
    - Adds required agents to intents if missing
    - Sets requires_contradictor = True for consensus
    
    Args:
        decision: Original RouteDecision from router
        strategic_context: Strategic context from detect_strategic_context
        
    Returns:
        Enriched RouteDecision
    """
    if not strategic_context.is_strategic:
        return decision
    
    # Create a copy of decision to modify
    new_intents = list(decision.intents)
    new_reasons = list(decision.reasons)
    
    # Map string agent names to IntentName
    agent_to_intent = {
        "finance": IntentName.FINANCE,
        "researcher": IntentName.RESEARCHER,
        "marketing": IntentName.MARKETING,
        "sales": IntentName.SALES,
        "legal_safe": IntentName.LEGAL_SAFE,
    }
    
    # Add missing required agents
    existing_intents = {i.name for i in new_intents}
    
    for agent in strategic_context.required_agents:
        intent_name = agent_to_intent.get(agent)
        if intent_name and intent_name not in existing_intents:
            new_intents.append(RouteIntent(
                name=intent_name,
                score=0.8,  # High score for required agents
                matched_keywords=["strategic-requirement"],
                is_required=True,  # Mark as required
                reason=f"Required for {[dt.value for dt in strategic_context.document_types]}",
            ))
            new_reasons.append(f"Added {agent} as required for strategic document")
    
    # Sort by score
    new_intents.sort(key=lambda x: (-x.score, x.name.value))
    
    # Force board-level for HIGH criticality
    new_is_board_level = decision.is_board_level
    if strategic_context.criticality == Criticality.HIGH:
        new_is_board_level = True
        if not decision.is_board_level:
            new_reasons.append("Forced board-level for HIGH criticality strategic document")
    
    # Force contradictor for strategic documents
    new_requires_contradictor = len(new_intents) >= 2
    
    # Create new decision
    return RouteDecision(
        verdict=decision.verdict,
        intents=new_intents,
        routing_strength=max(decision.routing_strength, 0.7),  # Boost strength
        is_board_level=new_is_board_level,
        requires_contradictor=new_requires_contradictor,
        reasons=new_reasons,
        policy_version=decision.policy_version,
        clarification_prompt=decision.clarification_prompt,
        missing_info=decision.missing_info,
        injection_blocked=decision.injection_blocked,
        injection_attempt=decision.injection_attempt,
        route_id=decision.route_id,
        input_hash=decision.input_hash,
    )


def validate_strategic_response(
    response: Union[Dict[str, Any], str],
    strategic_context: StrategicRouteContext,
    strict_mode: bool = True,
) -> Tuple[StrategicValidationResult, Optional[Dict[str, Any]]]:
    """
    Validate a strategic document response against Evidence standards.
    
    Called after agent response but before returning to user.
    
    Args:
        response: Agent response (dict or markdown string)
        strategic_context: Strategic context from routing
        strict_mode: If True, FAIL_CLOSED on insufficient sourcing
        
    Returns:
        (validation_result, fail_closed_response or None)
    """
    if not strategic_context.is_strategic:
        # Not a strategic request - skip validation
        return StrategicValidationResult(
            is_valid=True,
            decision=StrategicDecision.APPROVED,
        ), None
    
    # Get primary document type
    primary_type = strategic_context.document_types[0] if strategic_context.document_types else StrategicDocumentType.MARKET_STUDY
    
    # Validate
    result = validate_strategic_output(
        output=response,
        document_type=primary_type,
        criticality=strategic_context.criticality,
        strict_mode=strict_mode and strategic_context.validation_enforced,
    )
    
    if not result.is_valid:
        logger.warning(
            f"Strategic validation FAILED: decision={result.decision.value}, "
            f"errors={result.errors}, missing={result.missing_requirements}"
        )
        return result, result.fail_closed_response
    
    logger.info(
        f"Strategic validation PASSED: sources={result.source_count}, "
        f"public={result.public_source_count}, unverified={result.unverified_claim_count}"
    )
    return result, None


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategicPipelineResult:
    """Result of the full strategic pipeline."""
    
    # Context
    strategic_context: StrategicRouteContext
    enriched_route: Optional[RouteDecision] = None
    
    # Validation
    validation_result: Optional[StrategicValidationResult] = None
    
    # Final response
    final_response: Optional[Dict[str, Any]] = None
    is_fail_closed: bool = False
    fail_closed_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategic_context": self.strategic_context.to_dict(),
            "is_fail_closed": self.is_fail_closed,
            "fail_closed_reason": self.fail_closed_reason,
            "validation": {
                "is_valid": self.validation_result.is_valid if self.validation_result else None,
                "decision": self.validation_result.decision.value if self.validation_result else None,
                "source_count": self.validation_result.source_count if self.validation_result else 0,
                "missing": self.validation_result.missing_requirements if self.validation_result else [],
            } if self.validation_result else None,
        }


def run_strategic_pipeline(
    query: str,
    base_route_decision: RouteDecision,
    agent_response: Union[Dict[str, Any], str],
    strict_mode: bool = True,
) -> StrategicPipelineResult:
    """
    Run the full strategic pipeline.
    
    This is the main entry point for integrating strategic validation
    into the Evidence pipeline.
    
    Args:
        query: Original user query
        base_route_decision: RouteDecision from initial routing
        agent_response: Response from agents
        strict_mode: If True, enforce FAIL_CLOSED on failures
        
    Returns:
        StrategicPipelineResult with full context and validation
    """
    # Step 1: Detect strategic context
    context = detect_strategic_context(query)
    
    if not context.is_strategic:
        # Not strategic - passthrough
        return StrategicPipelineResult(
            strategic_context=context,
            enriched_route=base_route_decision,
            final_response=agent_response if isinstance(agent_response, dict) else {"content": agent_response},
            is_fail_closed=False,
        )
    
    # Step 2: Enrich route decision
    enriched = enrich_route_decision(base_route_decision, context)
    
    # Step 3: Validate response
    validation, fail_closed = validate_strategic_response(
        response=agent_response,
        strategic_context=context,
        strict_mode=strict_mode,
    )
    
    if fail_closed:
        return StrategicPipelineResult(
            strategic_context=context,
            enriched_route=enriched,
            validation_result=validation,
            final_response=fail_closed,
            is_fail_closed=True,
            fail_closed_reason=validation.errors[0] if validation.errors else "Sourcing requirements not met",
        )
    
    return StrategicPipelineResult(
        strategic_context=context,
        enriched_route=enriched,
        validation_result=validation,
        final_response=agent_response if isinstance(agent_response, dict) else {"content": agent_response},
        is_fail_closed=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS FOR ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

def should_enforce_strategic_validation(query: str) -> bool:
    """
    Quick check if a query should have strategic validation enforced.
    
    Use this early in the pipeline to decide if strategic pipeline
    should be activated.
    """
    is_strat, _, _ = is_strategic_request(query)
    return is_strat


def get_strategic_requirements_summary(query: str) -> Optional[Dict[str, Any]]:
    """
    Get a summary of strategic requirements for a query.
    
    Returns None if not a strategic request.
    """
    context = detect_strategic_context(query)
    if not context.is_strategic:
        return None
    
    return {
        "document_types": [dt.value for dt in context.document_types],
        "criticality": context.criticality.value,
        "required_agents": context.required_agents,
        "requirements": context.source_requirements,
    }


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Context
    "StrategicRouteContext",
    # Main functions
    "detect_strategic_context",
    "enrich_route_decision",
    "validate_strategic_response",
    # Pipeline
    "StrategicPipelineResult",
    "run_strategic_pipeline",
    # Convenience
    "should_enforce_strategic_validation",
    "get_strategic_requirements_summary",
]
