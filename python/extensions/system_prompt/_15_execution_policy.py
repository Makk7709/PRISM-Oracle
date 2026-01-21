"""
Execution Policy Extension — Injects mandatory execution rules into system prompt.

This extension enforces the "operator, not commentator" principle by adding
execution policy rules to every agent's system prompt.
"""

from typing import Any
from python.helpers.extension import Extension
from agent import Agent, LoopData


class ExecutionPolicy(Extension):
    """Injects execution policy into system prompt."""

    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any
    ):
        # Inject execution policy prompt
        policy = get_execution_policy_prompt(self.agent)
        if policy:
            system_prompt.append(policy)


def get_execution_policy_prompt(agent: Agent) -> str:
    """
    Load and return the execution policy prompt.
    This prompt enforces tool execution for actionable requests.
    """
    try:
        return agent.read_prompt("agent.system.policy.execution.md")
    except FileNotFoundError:
        # Fallback inline policy if file not found
        return """
## EXECUTION POLICY — MANDATORY

### Core Rules
1. **You are an OPERATOR, not a commentator.**
2. When a task can be advanced using a tool, you MUST call a tool.
3. You are FORBIDDEN to only describe a plan if execution is possible.
4. Do not explain what you will do. **DO IT.**
5. Long textual explanations before execution are FORBIDDEN.

### If No Tool Exists
Respond STRICTLY with:
```
MISSING_TOOL: <tool_name_needed>
REASON: <1 sentence maximum>
```

### Forbidden Patterns
- ❌ "I will now proceed to..."
- ❌ "Let me explain my approach..."
- ❌ "Here's what I plan to do..."
- ❌ Asking "Should I proceed?" when action is clearly requested

### Valid Patterns
- ✅ Direct tool call with minimal thoughts
- ✅ MISSING_TOOL when no tool exists
- ✅ Brief result summary AFTER execution
"""
