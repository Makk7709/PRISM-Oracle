"""
Extension monologue_end — capture automatique du snapshot de replay.

S'execute apres chaque monologue pour persister un snapshot complet
de la session, utilisable pour replay deterministe et verification d'integrite.
"""

from python.helpers.extension import Extension
from agent import Agent, LoopData
import logging

logger = logging.getLogger("ext.replay_snapshot")


class ReplaySnapshot(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if self.agent is None:
            return

        agent: Agent = self.agent
        ctx = agent.context

        if not hasattr(agent, "history") or not agent.history:
            return

        try:
            from python.helpers.replay_engine import capture_snapshot, save_snapshot

            query = ""
            response = ""
            if hasattr(loop_data, "user_message") and loop_data.user_message:
                query = str(loop_data.user_message)
            if hasattr(loop_data, "last_response"):
                response = str(loop_data.last_response or "")

            system_prompt = ""
            if hasattr(loop_data, "system") and loop_data.system:
                system_prompt = "\n\n".join(str(s) for s in loop_data.system)

            history_text = ""
            if hasattr(agent, "concat_messages"):
                try:
                    history_text = agent.concat_messages(agent.history)
                except Exception:
                    history_text = str(agent.history.output()) if agent.history else ""

            model_provider = "unknown"
            model_name = "unknown"
            model_temperature = None
            model_kwargs: dict = {}
            try:
                mc = agent.config.chat_model
                model_provider = mc.provider
                model_name = mc.name
                model_kwargs = mc.kwargs.copy() if mc.kwargs else {}
                model_temperature = model_kwargs.pop("temperature", None)
            except Exception:
                pass

            delegation_chain = []
            try:
                budget_state = agent.get_data("_execution_budget_state")
                if budget_state and hasattr(budget_state, "delegation_chain"):
                    delegation_chain = list(budget_state.delegation_chain)
            except Exception:
                pass

            execution_budget = {}
            try:
                budget_state = agent.get_data("_execution_budget_state")
                if budget_state and hasattr(budget_state, "to_dict"):
                    execution_budget = budget_state.to_dict()
            except Exception:
                pass

            tokens_in = agent.get_data("_llm_tokens_input") or 0
            tokens_out = agent.get_data("_llm_tokens_output") or 0

            from flask import g
            correlation_id = ""
            try:
                correlation_id = getattr(g, "request_id", "")
            except RuntimeError:
                pass

            snapshot = capture_snapshot(
                context_id=ctx.id,
                session_id=ctx.get_data("_session_id") or "",
                query=query,
                response=response,
                system_prompt=system_prompt,
                history_text=history_text,
                agent_profile=agent.agent_name if hasattr(agent, "agent_name") else "unknown",
                model_provider=model_provider,
                model_name=model_name,
                model_temperature=model_temperature,
                model_kwargs=model_kwargs,
                delegation_chain=delegation_chain,
                execution_budget=execution_budget,
                tokens_input=int(tokens_in) if tokens_in else 0,
                tokens_output=int(tokens_out) if tokens_out else 0,
                username=ctx.username,
                organization=ctx.organization,
                correlation_id=correlation_id,
            )

            save_snapshot(snapshot)
            logger.info("Replay snapshot captured for context %s", ctx.id)

        except Exception as exc:
            logger.warning("Replay snapshot capture failed: %s", exc)
