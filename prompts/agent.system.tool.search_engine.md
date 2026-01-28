### search_engine:
provide query arg get search results
returns list urls titles descriptions

**FALLBACK RULE**: if search_engine returns error (unavailable, ratelimit, connection error):
→ IMMEDIATELY use browser_agent to navigate directly to relevant website
→ NEVER give up on a simple search request

**Example usage**:
~~~json
{
    "thoughts": ["Searching for weather information"],
    "headline": "Searching web",
    "tool_name": "search_engine",
    "tool_args": {
        "query": "météo Paris aujourd'hui"
    }
}
~~~

**If search_engine fails, use browser_agent**:
~~~json
{
    "thoughts": ["search_engine failed, using browser fallback"],
    "headline": "Navigating directly to weather site",
    "tool_name": "browser_agent",
    "tool_args": {
        "message": "Go to https://meteofrance.com, search for Paris weather, extract current conditions (temperature, sky, wind). End task with weather summary.",
        "reset": "true"
    }
}
~~~
