"""
PRISM Consensus Engine — Single Entrypoint (v2).

POINT D'ENTRÉE UNIQUE pour TOUTE décision de consensus dans KOREV.
All consensus decisions MUST go through `run_consensus()` exposed here.

Callers DIRECTS autorisés (appellent `run_consensus` directement —
chemin actif vérifié par tests/test_consensus_entrypoint_delegation.py) :

    - python.helpers.consensus_arbiter.ConsensusOrchestrator.seek_consensus
        (wrapper de compat ascendante)
    - python.helpers.consensus_integration.ResearchPipeline
        .validate_with_consensus (pipeline de recherche)
    - python.helpers.consensus_mcp_integration.research_with_consensus
        (façade MCP)

Callers INDIRECTS autorisés (passent par un wrapper ci-dessus) :

    - python.helpers.research_consensus_integration (utilise
      ConsensusOrchestrator.seek_consensus)

Tout autre point d'appel direct des classes legacy (ConsensusManager,
ArbiterLLM, ConsensusOrchestrator._select_arbiters / _count_votes /
_create_no_arbiter_result / _log_audit) est considéré obsolète
(cf. ADR-008-consensus-v1-to-v2-migration.md).

Contrats :
    - Retour : ConsensusDecision (dataclass normalisée) avec
      proposal_id, decision_hash, status (ConsensusStatusEnum),
      approved (bool), votes, vote_count, decision_time_ms,
      correlation_id, warnings.
    - Fail-closed : `_ensure_real_votes_or_raise` interdit qu'une décision
      soit produite sans vote réel (sauf INFRA_FAILURE explicite).
    - Idempotence : run_consensus génère un proposal_id unique par appel.

Architecture v1 → v2 :
    L'ancien chemin (ConsensusManager.propose → submit_vote →
    check_consensus → _finalize_proposal) est conservé pour les helpers
    (build_vote_prompt, parse_llm_vote_response, generate_decision_hash)
    mais n'est plus le pipeline principal. Voir ADR-008.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from python.helpers.consensus_arbiter import (
    ArbiterCaller,
    ArbiterConfig,
    ConsensusConfig,
    load_consensus_config,
)
from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusResult,
    DecisionType,
    VoteCount,
    Vote,
    VoteType,
    generate_decision_hash,
)
from python.helpers.consensus_contracts import (
    ConsensusPolicySchema,
    ConsensusResultSchema,
    ConsensusStatusEnum,
    ResponseEnvelopeSchema,
    ReliabilityTierSchema,
    ReliabilityTierEnum,
    ConsensusSummarySchema,
    validate_strict,
)

logger = logging.getLogger("consensus_engine")


@dataclass
class ConsensusDecision:
    """Normalized consensus decision returned by the engine."""
    proposal_id: str
    decision_hash: str
    status: ConsensusStatusEnum
    approved: bool
    votes: Dict[str, Vote]
    vote_count: VoteCount
    decision_time_ms: int
    correlation_id: str
    warnings: List[str] = field(default_factory=list)


def _log_json(event: str, payload: Dict[str, Any]) -> None:
    logger.info(json.dumps({
        "event": event,
        **payload,
    }, ensure_ascii=False))


def _ensure_real_votes_or_raise(
    decision: ConsensusDecision,
    is_production: bool,
) -> None:
    if not is_production:
        return
    if decision.status != ConsensusStatusEnum.APPROVED:
        return
    has_real_votes = any(v.available for v in decision.votes.values())
    if not has_real_votes:
        logger.critical(
            "Consensus approved without real votes in production "
            f"(correlation_id={decision.correlation_id})"
        )
        raise RuntimeError("Approval without real votes is forbidden in production")


def _sanitize_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Remove raw or oversized fields before sending to arbiters."""
    blocked_keys = {"raw_content", "raw_html", "raw_markdown", "raw_text", "evidence_pack"}
    sanitized: Dict[str, Any] = {}
    for key, value in context.items():
        if key in blocked_keys:
            continue
        if isinstance(value, str) and len(value) > 2000:
            sanitized[key] = value[:2000] + "..."
        else:
            sanitized[key] = value
    return sanitized


class ConsensusEngine:
    """Authoritative PRISM consensus engine."""

    def __init__(self, config: Optional[ConsensusConfig] = None):
        self.config = config or load_consensus_config()
        self.manager = ConsensusManager(
            timeout_ms=self.config.global_timeout_ms,
            total_providers=self.config.total_providers,
        )
        self.caller = ArbiterCaller(self.config)

    async def run_consensus(
        self,
        evidence_pack: Optional[Dict[str, Any]],
        policy: Dict[str, Any],
    ) -> ConsensusDecision:
        if os.environ.get("CONSENSUS_ENGINE_V2", "true").lower() not in ("true", "1"):
            logger.warning("CONSENSUS_ENGINE_V2 disabled but engine is enforced")
        policy_obj: ConsensusPolicySchema = validate_strict(policy, ConsensusPolicySchema)
        correlation_id = policy_obj.correlation_id or str(uuid.uuid4())
        start_time = time.time()

        _log_json("router_to_engine", {
            "correlation_id": correlation_id,
            "decision_type": policy_obj.decision_type.value,
            "integrity_checks": policy_obj.integrity_checks,
        })

        arbiters = self._select_arbiters()
        if not arbiters:
            # ─────────────────────────────────────────────────────────────────
            # SIMULATION MODE: Generate simulated votes when no arbiters
            # ─────────────────────────────────────────────────────────────────
            if self.config.simulation_enabled:
                logger.warning(
                    "No arbiters configured but simulation enabled — "
                    "generating simulated approval votes"
                )
                sim_providers = [
                    "simulation/arbiter-1",
                    "simulation/arbiter-2",
                    "simulation/arbiter-3",
                ]
                sim_votes = {}
                for p in sim_providers:
                    sim_votes[p] = Vote(
                        provider=p,
                        vote=VoteType.APPROVE,
                        reasoning="Simulated approval (no arbiters configured)",
                        confidence=1.0,
                        timestamp=time.time(),
                        available=True,
                        availability_reason="simulation",
                    )
                decision = ConsensusDecision(
                    proposal_id=str(uuid.uuid4()),
                    decision_hash=generate_decision_hash(policy_obj.action, policy_obj.context),
                    status=ConsensusStatusEnum.APPROVED,
                    approved=True,
                    votes=sim_votes,
                    vote_count=VoteCount(
                        total=3,
                        approvals=3,
                        rejections=0,
                        abstentions=0,
                        unavailable=0,
                    ),
                    decision_time_ms=int((time.time() - start_time) * 1000),
                    correlation_id=correlation_id,
                    warnings=["simulation_mode_active", "no_arbiters_configured"],
                )
                _log_json("consensus_tally", {
                    "correlation_id": correlation_id,
                    "status": decision.status.value,
                    "warnings": decision.warnings,
                })
                return decision

            # ─────────────────────────────────────────────────────────────────
            # NO SIMULATION: Fail-closed — INFRA_FAILURE
            # ─────────────────────────────────────────────────────────────────
            warnings = ["no_arbiters_configured"]
            decision = ConsensusDecision(
                proposal_id=str(uuid.uuid4()),
                decision_hash=generate_decision_hash(policy_obj.action, policy_obj.context),
                status=ConsensusStatusEnum.INFRA_FAILURE,
                approved=False,
                votes={},
                vote_count=VoteCount(),
                decision_time_ms=0,
                correlation_id=correlation_id,
                warnings=warnings,
            )
            _log_json("consensus_tally", {
                "correlation_id": correlation_id,
                "status": decision.status.value,
                "warnings": warnings,
            })
            return decision

        decision_hash = generate_decision_hash(policy_obj.action, policy_obj.context)
        proposal_id = await self.manager.propose(
            decision_hash,
            {
                "action": policy_obj.action,
                "context": policy_obj.context,
                "evidence_pack": evidence_pack,
                "correlation_id": correlation_id,
            },
            policy_obj.decision_type,
        )

        arbiter_context = _sanitize_context(policy_obj.context)
        tasks = [
            self.caller.call_arbiter(arbiter, policy_obj.action, arbiter_context)
            for arbiter in arbiters
        ]
        votes = await asyncio.gather(*tasks, return_exceptions=True)

        arbiter_votes = []
        for i, vote_result in enumerate(votes):
            if isinstance(vote_result, Exception):
                arbiter_votes.append(Vote(
                    provider=f"{arbiters[i].provider}/{arbiters[i].model}",
                    vote=None,
                    reasoning=f"Exception: {str(vote_result)[:100]}",
                    confidence=0.0,
                    timestamp=time.time(),
                    available=False,
                    availability_reason="exception",
                ))
                _log_json("arbiter_call", {
                    "correlation_id": correlation_id,
                    "arbiter": f"{arbiters[i].provider}/{arbiters[i].model}",
                    "available": False,
                    "reason": "exception",
                })
            else:
                arbiter_votes.append(vote_result.to_vote())
                _log_json("arbiter_call", {
                    "correlation_id": correlation_id,
                    "arbiter": f"{vote_result.provider}/{vote_result.model}",
                    "available": vote_result.available,
                    "reason": vote_result.availability_reason or "ok",
                    "latency_ms": vote_result.latency_ms,
                })

        for vote in arbiter_votes:
            self.manager.submit_vote(
                proposal_id=proposal_id,
                provider=vote.provider,
                vote=vote.vote,
                reasoning=vote.reasoning,
                confidence=vote.confidence,
                risks=vote.risks_identified,
                available=vote.available,
                availability_reason=vote.availability_reason,
            )

        await self.manager.wait_for_consensus(
            proposal_id,
            max_wait_ms=policy_obj.timeout_ms or self.config.global_timeout_ms,
        )

        proposal = (
            self.manager.recent_proposals.get(proposal_id) or
            self.manager.proposals.get(proposal_id)
        )
        if not proposal:
            status = ConsensusStatusEnum.INFRA_FAILURE
        else:
            status = proposal.status

        decision_time_ms = int((time.time() - start_time) * 1000)
        votes_by_provider = {v.provider: v for v in arbiter_votes}
        vote_count = proposal.get_vote_count() if proposal else VoteCount()
        approved = status == ConsensusStatusEnum.APPROVED
        warnings: List[str] = []

        if status in (ConsensusStatusEnum.NO_CONSENSUS, ConsensusStatusEnum.INFRA_FAILURE):
            warnings.append("consensus_not_reached")

        decision = ConsensusDecision(
            proposal_id=proposal_id,
            decision_hash=decision_hash,
            status=status,
            approved=approved,
            votes=votes_by_provider,
            vote_count=vote_count,
            decision_time_ms=decision_time_ms,
            correlation_id=correlation_id,
            warnings=warnings,
        )

        _log_json("consensus_tally", {
            "correlation_id": correlation_id,
            "proposal_id": proposal_id,
            "status": status.value,
            "approvals": vote_count.approvals,
            "rejections": vote_count.rejections,
            "abstentions": vote_count.abstentions,
            "unavailable": vote_count.unavailable,
            "decision_time_ms": decision_time_ms,
        })

        _ensure_real_votes_or_raise(
            decision=decision,
            is_production=os.environ.get("EVIDENCE_ENV", "production").lower() == "production",
        )

        validate_strict({
            "proposal_id": decision.proposal_id,
            "status": decision.status,
            "approvals": decision.vote_count.approvals,
            "rejections": decision.vote_count.rejections,
            "abstentions": decision.vote_count.abstentions,
            "unavailable": decision.vote_count.unavailable,
            "total": decision.vote_count.total,
            "decision_time_ms": decision.decision_time_ms,
            "warnings": decision.warnings,
        }, ConsensusResultSchema)

        return decision

    def _select_arbiters(self) -> List[ArbiterConfig]:
        if self.config.offline_mode:
            if self.config.local_arbiters:
                return self.config.local_arbiters[:self.config.total_providers]
            return []
        return sorted(self.config.arbiters, key=lambda a: a.priority)[:self.config.total_providers]


_engine_instance: Optional[ConsensusEngine] = None


def get_consensus_engine() -> ConsensusEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ConsensusEngine()
    return _engine_instance


async def run_consensus(
    evidence_pack: Optional[Dict[str, Any]],
    policy: Dict[str, Any],
) -> ConsensusDecision:
    engine = get_consensus_engine()
    return await engine.run_consensus(evidence_pack, policy)


def build_fail_soft_envelope(
    answer: str,
    decision: ConsensusDecision,
    unknowns: Optional[List[str]] = None,
    recommended_next_steps: Optional[List[str]] = None,
    debug_trace: Optional[Dict[str, Any]] = None,
) -> ResponseEnvelopeSchema:
    unknowns = unknowns or []
    recommended_next_steps = recommended_next_steps or []

    tiers = [
        ReliabilityTierSchema(
            tier=ReliabilityTierEnum.MEDIUM if decision.status == ConsensusStatusEnum.APPROVED else ReliabilityTierEnum.LOW,
            claims=[],
            rationale="Consensus not reached or partially reliable output.",
            sources=[],
        )
    ]

    summary = ConsensusSummarySchema(
        status=decision.status,
        quorum="2/3",
        votes_summary={
            "approvals": decision.vote_count.approvals,
            "rejections": decision.vote_count.rejections,
            "abstentions": decision.vote_count.abstentions,
            "unavailable": decision.vote_count.unavailable,
            "total": decision.vote_count.total,
        },
        warnings=decision.warnings,
    )

    return ResponseEnvelopeSchema(
        answer=answer,
        reliability_tiers=tiers,
        unknowns=unknowns,
        recommended_next_steps=recommended_next_steps,
        consensus=summary,
        debug_trace=debug_trace,
    )
