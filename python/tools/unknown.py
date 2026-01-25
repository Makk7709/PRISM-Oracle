"""
Unknown Tool Handler — Routes unknown tools with Graph Policy enforcement.

SECURITY:
- NEVER expose tool lists to users
- Auto-route graph requests to code_execution guidance
- Provide clean error messages without internal debug info
"""

from python.helpers.tool import Tool, Response
from python.helpers.graph_runner import is_graph_request, generate_graph_code, ALL_GRAPH_KEYWORDS


# Graph-related tool names that should be routed to code_execution
GRAPH_TOOL_PATTERNS = [
    "graph", "plot", "chart", "draw", "visualize", "visualise",
    "diagram", "figure", "curve", "histogram", "pie", "bar",
    "scatter", "line_chart", "bar_chart", "pie_chart",
]


def is_graph_tool_request(tool_name: str) -> bool:
    """Check if the requested tool is graph-related."""
    if not tool_name:
        return False
    
    tool_lower = tool_name.lower()
    
    for pattern in GRAPH_TOOL_PATTERNS:
        if pattern in tool_lower:
            return True
    
    return False


class Unknown(Tool):
    """
    Handles unknown tool requests.
    
    GRAPH POLICY:
    - If tool name is graph-related → return code_execution guidance
    - NEVER expose the full tool list to prevent debug leaks
    """
    
    async def execute(self, **kwargs):
        tool_name = self.name or "unknown"
        
        # ═══════════════════════════════════════════════════════════════════
        # GRAPH POLICY: Route graph requests to code_execution
        # ═══════════════════════════════════════════════════════════════════
        if is_graph_tool_request(tool_name):
            return Response(
                message=self._get_graph_guidance(tool_name),
                break_loop=False,
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # CLEAN ERROR: No tool list exposure
        # ═══════════════════════════════════════════════════════════════════
        return Response(
            message=self._get_clean_error(tool_name),
            break_loop=False,
        )
    
    def _get_graph_guidance(self, tool_name: str) -> str:
        """
        Returns guidance to use code_execution for graphs.
        NO tool list exposed.
        """
        return f"""GRAPH_POLICY_REDIRECT

The tool "{tool_name}" is not available. 
For ALL graph/chart/plot requests, use `code_execution` with Python/matplotlib.

REQUIRED ACTION:
Use code_execution with this template:

{{
    "tool_name": "code_execution",
    "tool_args": {{
        "runtime": "python",
        "code": "import pandas as pd\\nimport matplotlib\\nmatplotlib.use('Agg')\\nimport matplotlib.pyplot as plt\\nimport os\\n\\n# Load data\\ndf = pd.read_excel('tmp/uploads/YOUR_FILE.xlsx')\\nprint(f'Loaded: {{len(df)}} rows')\\n\\n# Create chart\\nfig, ax = plt.subplots(figsize=(12, 8))\\n# ... plot code ...\\nos.makedirs('tmp/generated', exist_ok=True)\\nplt.savefig('tmp/generated/graph.png', dpi=100)\\nprint('Graph saved: tmp/generated/graph.png')"
    }}
}}

IMPORTANT:
- Replace YOUR_FILE.xlsx with the actual file path
- Use matplotlib only (not seaborn)
- Save to tmp/generated/
- Print the output path for the user
"""

    def _get_clean_error(self, tool_name: str) -> str:
        """
        Returns a clean error without exposing tool list.
        """
        return f"""TOOL_UNAVAILABLE

The tool "{tool_name}" is not available.

If you need to:
- Generate a graph/chart → Use `code_execution` with matplotlib
- Read Excel/CSV files → Use `code_execution` with pandas  
- Create PDF reports → Use `code_execution` with reportlab
- Process images → Use `code_execution` with PIL

For ANY data processing task, use `code_execution`:

{{
    "tool_name": "code_execution",
    "tool_args": {{
        "runtime": "python",
        "code": "# Your Python code here"
    }}
}}

Do NOT tell the user that a tool is missing. Execute the task with code_execution.
"""
