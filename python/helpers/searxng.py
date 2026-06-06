"""
SearXNG Search Helper — USER-SAFE mode compatible.

Configuration via environment variables:
- SEARCH_PROVIDER: "searxng" | "none" (default: "searxng")
- SEARXNG_URL: Base URL for SearXNG instance (default: "http://localhost:55510")

In user mode, this module performs direct HTTP calls without any RFC bridge dependency.
All errors are caught and returned as soft-fail results (never crashes the agent).
"""

import os
import aiohttp
import asyncio
from typing import Any
from python.helpers.print_style import PrintStyle

# Configuration
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SEARXNG_URL = "http://localhost:55510"
DEFAULT_TIMEOUT_SECONDS = 15


def get_search_provider() -> str:
    """Get configured search provider: 'searxng' or 'none'."""
    return os.environ.get("SEARCH_PROVIDER", "searxng").lower()


def get_searxng_url() -> str:
    """Get SearXNG instance URL from env."""
    url = os.environ.get("SEARXNG_URL", DEFAULT_SEARXNG_URL)
    # Ensure no trailing slash
    return url.rstrip("/")


def is_search_enabled() -> bool:
    """Check if search is configured and enabled."""
    provider = get_search_provider()
    return provider != "none" and provider != ""


# ─────────────────────────────────────────────────────────────────────────────
# Search Function (USER-SAFE)
# ─────────────────────────────────────────────────────────────────────────────
async def search(query: str) -> dict[str, Any]:
    """
    Perform a web search via SearXNG.
    
    Returns a dict with:
    - "results": list of search results (or empty list on failure)
    - "error": optional error message if search failed
    
    NEVER raises an exception — always returns a soft-fail result.
    """
    # Check if search is disabled by config
    if not is_search_enabled():
        return {
            "results": [],
            "error": "Web search disabled by configuration. Set SEARCH_PROVIDER=searxng and SEARXNG_URL to enable."
        }

    provider = get_search_provider()
    
    if provider == "searxng":
        return await _searxng_search(query)
    else:
        return {
            "results": [],
            "error": f"Unknown search provider: {provider}. Supported: searxng, none."
        }


async def _searxng_search(query: str) -> dict[str, Any]:
    """Direct HTTP call to SearXNG — no RFC bridge, with timeout and error handling."""
    url = get_searxng_url() + "/search"
    
    PrintStyle.debug(f"[Search] SearXNG query: {query[:50]}... -> {url}")
    
    timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT_SECONDS)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                data={"q": query, "format": "json"},
                headers={"Accept": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    PrintStyle.warning(f"[Search] SearXNG returned {response.status}: {error_text[:100]}")
                    return {
                        "results": [],
                        "error": f"Search service returned status {response.status}."
                    }
                
                data = await response.json()
                results = data.get("results", [])
                PrintStyle.debug(f"[Search] Got {len(results)} results.")
                return {"results": results}

    except aiohttp.ClientConnectorError as e:
        PrintStyle.warning(f"[Search] Cannot connect to SearXNG at {url}: {e}")
        return {
            "results": [],
            "error": f"Cannot connect to search service at {get_searxng_url()}. Check SEARXNG_URL configuration."
        }
    
    except asyncio.TimeoutError:
        PrintStyle.warning(f"[Search] Timeout connecting to SearXNG at {url}")
        return {
            "results": [],
            "error": f"Search service timed out after {DEFAULT_TIMEOUT_SECONDS}s."
        }
    
    except aiohttp.ContentTypeError as e:
        PrintStyle.warning(f"[Search] Invalid response from SearXNG: {e}")
        return {
            "results": [],
            "error": "Search service returned invalid response format."
        }
    
    except Exception as e:
        PrintStyle.warning(f"[Search] Unexpected error: {e}")
        return {
            "results": [],
            "error": f"Search failed: {str(e)}"
        }
