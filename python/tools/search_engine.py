"""
Search Engine Tool — USER-SAFE mode compatible.

Uses SearXNG for web search with DuckDuckGo fallback.
Never crashes the agent — returns soft-fail messages on error.
"""

from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle
from python.helpers.searxng import search as searxng_search

SEARCH_ENGINE_RESULTS = 10


class SearchEngine(Tool):
    async def execute(self, query="", **kwargs):
        """Execute a web search query with fallback providers."""
        if not query or not query.strip():
            return Response(
                message="Search query is empty. Please provide a search term.",
                break_loop=False
            )

        try:
            # Try SearXNG first
            result = await self.searxng_search(query)
            
            # If SearXNG failed, try DuckDuckGo fallback
            if "[Search Engine unavailable]" in result or "Cannot connect" in result:
                PrintStyle.hint("[SearchEngine] SearXNG unavailable, trying DuckDuckGo fallback...")
                result = await self.duckduckgo_search(query)
                
        except Exception as e:
            # Catch-all for any unexpected errors — never crash the agent
            PrintStyle.error(f"[SearchEngine] Unexpected error: {e}")
            # Try DuckDuckGo as last resort
            try:
                result = await self.duckduckgo_search(query)
            except Exception as e2:
                result = f"Search failed: {str(e)}. Fallback also failed: {str(e2)}"

        await self.agent.handle_intervention()

        return Response(message=result, break_loop=False)

    async def searxng_search(self, question: str) -> str:
        """Perform SearXNG search with soft-fail handling."""
        result = await searxng_search(question)
        return self.format_result_searxng(result, "Search Engine")

    async def duckduckgo_search(self, question: str) -> str:
        """Perform DuckDuckGo search as fallback."""
        try:
            from python.helpers.duckduckgo_search import search as ddg_search
            
            results = ddg_search(question, results=SEARCH_ENGINE_RESULTS)
            
            if not results:
                return "[DuckDuckGo] No results found for the query."
            
            # Format results
            outputs = []
            for item in results:
                # Results come as string representations of dicts
                if isinstance(item, str):
                    try:
                        import ast
                        item_dict = ast.literal_eval(item)
                        title = item_dict.get("title", "No title")
                        url = item_dict.get("href", item_dict.get("link", ""))
                        content = item_dict.get("body", item_dict.get("snippet", ""))
                        outputs.append(f"{title}\n{url}\n{content}")
                    except:
                        outputs.append(item)
                else:
                    outputs.append(str(item))
            
            PrintStyle.hint("[SearchEngine] Using DuckDuckGo fallback - results retrieved successfully")
            return "\n\n".join(outputs).strip()
            
        except ImportError:
            return self._suggest_browser_fallback(question, "DuckDuckGo module not found")
        except Exception as e:
            return self._suggest_browser_fallback(question, str(e))
    
    def _suggest_browser_fallback(self, query: str, error: str) -> str:
        """Return error message with explicit browser_agent fallback suggestion."""
        # Detect query type to suggest appropriate URL
        query_lower = query.lower()
        
        if any(w in query_lower for w in ["météo", "meteo", "weather", "temps"]):
            suggested_url = "https://meteofrance.com"
            suggested_action = f"search for the city/location in the query"
        elif any(w in query_lower for w in ["juridique", "legal", "loi", "article", "code"]):
            suggested_url = "https://www.legifrance.gouv.fr"
            suggested_action = "search for the legal reference"
        elif any(w in query_lower for w in ["actualité", "news", "actu"]):
            suggested_url = "https://news.google.com"
            suggested_action = "search for the topic"
        else:
            suggested_url = "https://www.google.com"
            suggested_action = f"search for: {query}"
        
        return (
            f"[Search unavailable] {error}\n\n"
            f"**ACTION REQUIRED**: Use browser_agent with:\n"
            f'- message: "Go to {suggested_url}, {suggested_action}, extract relevant information, end task with summary"\n'
            f'- reset: "true"'
        )

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
