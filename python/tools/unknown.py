"""
Unknown Tool Handler — Silent fallback to code_execution.

CRITICAL: This tool NEVER returns user-visible messages.
All unknown tools are silently routed to code_execution.
"""

from python.helpers.tool import Tool, Response


class Unknown(Tool):
    """
    Handles unknown tool requests by returning a minimal internal instruction.
    
    The message returned here goes to the LLM's context, NOT to the user.
    The LLM should interpret this and use code_execution.
    """
    
    async def execute(self, **kwargs):
        tool_name = self.name or "unknown"
        
        # Return a MINIMAL internal instruction
        # This should NOT be forwarded to the user
        return Response(
            message=f'[SYSTEM] Use code_execution tool instead of "{tool_name}".',
            break_loop=False,
        )
