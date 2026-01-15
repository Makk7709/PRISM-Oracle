"""
Search Engine Tool — USER-SAFE mode compatible.

Uses SearXNG for web search with graceful error handling.
Never crashes the agent — returns soft-fail messages on error.
"""

from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle
from python.helpers.searxng import search as searxng_search

SEARCH_ENGINE_RESULTS = 10


class SearchEngine(Tool):
    async def execute(self, query="", **kwargs):
        """Execute a web search query."""
        if not query or not query.strip():
            return Response(
                message="Search query is empty. Please provide a search term.",
                break_loop=False
            )

        try:
            result = await self.searxng_search(query)
        except Exception as e:
            # Catch-all for any unexpected errors — never crash the agent
            PrintStyle.error(f"[SearchEngine] Unexpected error: {e}")
            result = f"Search failed unexpectedly: {str(e)}"

        await self.agent.handle_intervention()

        return Response(message=result, break_loop=False)

    async def searxng_search(self, question: str) -> str:
        """Perform SearXNG search with soft-fail handling."""
        result = await searxng_search(question)
        return self.format_result_searxng(result, "Search Engine")

    def format_result_searxng(self, result: dict, source: str) -> str:
        """Format search results or error message."""
        
        # Check for error in result
        error = result.get("error")
        if error:
            PrintStyle.hint(f"[{source}] {error}")
            return f"[{source} unavailable] {error}"

        # Extract results
        results_list = result.get("results", [])
        
        if not results_list:
            return f"[{source}] No results found for the query."

        # Format results
        outputs = []
        for item in results_list[:SEARCH_ENGINE_RESULTS]:
            title = item.get("title", "No title")
            url = item.get("url", "")
            content = item.get("content", "")
            outputs.append(f"{title}\n{url}\n{content}")

        return "\n\n".join(outputs).strip()
