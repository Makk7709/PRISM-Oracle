import asyncio
import json
import os

import httpx


def main() -> None:
    results: list[tuple[str, bool, str]] = []

    try:
        key = os.getenv("TAVILY_API_KEY")
        if key:
            with httpx.Client(timeout=20) as client:
                response = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": key,
                    "query": "AI Act trusted AI France",
                    "max_results": 3,
                },
            )
            body = response.json()
            ok = (
                response.status_code == 200
                and isinstance(body.get("results", []), list)
                and len(body.get("results", [])) > 0
            )
            results.append(
                (
                    "tavily",
                    ok,
                    f"status={response.status_code} results={len(body.get('results', []))}",
                )
            )
        else:
            results.append(("tavily", False, "missing key"))
    except Exception as exc:
        results.append(("tavily", False, str(exc)))

    try:
        key = os.getenv("FIRECRAWL_API_KEY")
        if key:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            payload = {"url": "https://example.com", "formats": ["markdown"]}
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers=headers,
                    json=payload,
                )
            body = (
                response.json()
                if "application/json" in response.headers.get("content-type", "")
                else {}
            )
            ok = response.status_code == 200 and body.get("success") is True
            results.append(
                (
                    "firecrawl",
                    ok,
                    f"status={response.status_code} success={body.get('success')}",
                )
            )
        else:
            results.append(("firecrawl", False, "missing key"))
    except Exception as exc:
        results.append(("firecrawl", False, str(exc)))

    try:
        from mcp_servers.pubmed.server import (
            get_pubmed_article_details,
            search_pubmed_articles,
        )

        async def _run_pubmed() -> tuple[bool, str]:
            items = await search_pubmed_articles("AI Act medical devices", max_results=3)
            if not items:
                return False, "no results"
            pmid = items[0].get("pmid", "")
            detail = await get_pubmed_article_details(pmid)
            return (
                bool(detail.get("found")),
                f"results={len(items)} pmid={pmid} found={detail.get('found')}",
            )

        ok, msg = asyncio.run(_run_pubmed())
        results.append(("pubmed", ok, msg))
    except Exception as exc:
        results.append(("pubmed", False, str(exc)))

    try:
        from mcp_servers.openalex.server_mcp import search_works

        async def _run_openalex() -> tuple[bool, str]:
            items = await search_works("AI Act", limit=3)
            return bool(items), f"results={len(items)}"

        ok, msg = asyncio.run(_run_openalex())
        results.append(("openalex", ok, msg))
    except Exception as exc:
        results.append(("openalex", False, str(exc)))

    results.append(
        (
            "brave",
            bool(os.getenv("BRAVE_API_KEY")),
            "key_present" if os.getenv("BRAVE_API_KEY") else "key_missing_expected_disabled",
        )
    )

    for name, ok, detail in results:
        print(json.dumps({"server": name, "ok": ok, "detail": detail}, ensure_ascii=False))


if __name__ == "__main__":
    main()
