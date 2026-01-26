from python.helpers.tool import Tool, Response
from python.extensions.system_prompt._10_system_prompt import (
    get_tools_prompt,
    get_mcp_tools_prompt,
)


class Unknown(Tool):
    async def execute(self, **kwargs):
        # Get both standard tools AND MCP tools
        tools = get_tools_prompt(self.agent)
        mcp_tools = get_mcp_tools_prompt(self.agent)
        
        # Combine both tool lists
        all_tools = tools
        if mcp_tools:
            all_tools += "\n\n" + mcp_tools
        
        return Response(
            message=self.agent.read_prompt(
                "fw.tool_not_found.md", tool_name=self.name, tools_prompt=all_tools
            ),
            break_loop=False,
        )
