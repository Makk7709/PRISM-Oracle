"""
Extension monologue_end — evaluation de risque dynamique + declenchement human review.

Apres chaque monologue, calcule un score de risque.
Si HIGH ou CRITICAL, cree automatiquement une demande de review humain.
"""

from python.helpers.extension import Extension
from agent import Agent, LoopData
import logging

logger = logging.getLogger("ext.risk_assessment")


class RiskAssessment(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if self.agent is None:
            return

        agent: Agent = self.agent
        ctx = agent.context

        try:
            from python.helpers.dynamic_risk_register import assess_session_risk

            consensus_achieved = True
            consensus_rounds = 0
            try:
                consensus_data = agent.get_data("_consensus_result")
                if consensus_data and isinstance(consensus_data, dict):
                    consensus_achieved = consensus_data.get("achieved", True)
                    consensus_rounds = consensus_data.get("rounds", 0)
            except Exception:
                pass

            confidence_score = None
            try:
                cs = agent.get_data("_confidence_score")
                if cs is not None:
                    confidence_score = float(cs)
            except Exception:
                pass

            error_count = 0
            timeout_count = 0
            delegation_depth = 0
            tool_call_count = 0
            execution_time_ms = 0
            try:
                budget_state = agent.get_data("_execution_budget_state")
                if budget_state:
                    delegation_depth = getattr(budget_state, "current_depth", 0)
                    tool_call_count = getattr(budget_state, "current_tool_calls", 0)
                    execution_time_ms = int(getattr(budget_state, "elapsed_ms", 0))
            except Exception:
                pass

            query = ""
            response = ""
            if hasattr(loop_data, "user_message") and loop_data.user_message:
                query = str(loop_data.user_message)
            if hasattr(loop_data, "last_response"):
                response = str(loop_data.last_response or "")

            from flask import g
            correlation_id = ""
            try:
                correlation_id = getattr(g, "request_id", "")
            except RuntimeError:
                pass

            assessment = assess_session_risk(
                context_id=ctx.id,
                session_id=ctx.get_data("_session_id") or "",
                correlation_id=correlation_id,
                query=query,
                consensus_achieved=consensus_achieved,
                consensus_rounds=consensus_rounds,
                confidence_score=confidence_score,
                error_count=error_count,
                timeout_count=timeout_count,
                delegation_depth=delegation_depth,
                tool_call_count=tool_call_count,
                execution_time_ms=execution_time_ms,
                username=ctx.username,
                organization=ctx.organization,
            )

            ctx.set_data("_risk_assessment", {
                "id": assessment.assessment_id,
                "score": assessment.risk_score,
                "level": assessment.risk_level,
                "requires_review": assessment.requires_human_review,
            })

            if assessment.requires_human_review:
                from python.helpers.human_review import (
                    ReviewTrigger,
                    create_review,
                )

                review = create_review(
                    context_id=ctx.id,
                    session_id=ctx.get_data("_session_id") or "",
                    query=query,
                    response=response,
                    trigger=ReviewTrigger.RISK_ENGINE,
                    risk_level=assessment.risk_level,
                    risk_score=assessment.risk_score,
                    username=ctx.username,
                    organization=ctx.organization,
                    correlation_id=correlation_id,
                    metadata={
                        "assessment_id": assessment.assessment_id,
                        "top_factors": [
                            f.name for f in sorted(
                                assessment.factors,
                                key=lambda f: f.weight * f.normalized_value,
                                reverse=True,
                            )[:3]
                        ],
                    },
                )

                ctx.set_data("_human_review_pending", {
                    "review_id": review.review_id,
                    "risk_level": assessment.risk_level,
                })

                logger.info(
                    "Human review %s triggered for context %s (risk=%s, score=%.2f)",
                    review.review_id, ctx.id, assessment.risk_level, assessment.risk_score,
                )

        except Exception as exc:
            logger.warning("Risk assessment failed for context %s: %s", ctx.id, exc)
