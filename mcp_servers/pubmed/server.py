#!/usr/bin/env python3
"""
PubMed MCP Server (STDIO transport).

Reliable MCP wrapper around NCBI E-utilities:
- search_pubmed_articles
- get_pubmed_article_details
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import httpx
from mcp.server import FastMCP

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "").strip()
NCBI_TOOL = os.getenv("NCBI_TOOL", "korev-evidence-mcp")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "support@korev.ai")

app = FastMCP("PubMed Biomedical MCP Server")
http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)


def _base_params() -> Dict[str, str]:
    params: Dict[str, str] = {"tool": NCBI_TOOL, "email": NCBI_EMAIL}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


def _pubmed_url(pmid: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _find_first(root: ET.Element, local_names: List[str]) -> ET.Element | None:
    wanted = set(local_names)
    for elem in root.iter():
        if _local_name(elem.tag) in wanted:
            return elem
    return None


def _find_text(root: ET.Element, local_name: str, default: str = "") -> str:
    for elem in root.iter():
        if _local_name(elem.tag) == local_name and (elem.text or "").strip():
            return (elem.text or "").strip()
    return default


def _collect_texts(root: ET.Element, local_name: str) -> List[ET.Element]:
    return [elem for elem in root.iter() if _local_name(elem.tag) == local_name]


@app.tool()
async def search_pubmed_articles(
    query: str,
    max_results: int = 10,
    sort: str = "relevance",
) -> List[Dict[str, Any]]:
    """
    Search PubMed and return structured article metadata.

    Args:
        query: PubMed query syntax (keywords, boolean operators, MeSH terms).
        max_results: Number of results to return (1-50).
        sort: "relevance" or "pub+date".
    """
    limit = min(max(max_results, 1), 50)
    sort_value = "pub+date" if sort == "pub+date" else "relevance"

    logger.info("PubMed search: query=%s limit=%s sort=%s", query, limit, sort_value)

    esearch_params = {
        **_base_params(),
        "db": "pubmed",
        "retmode": "json",
        "retmax": str(limit),
        "sort": sort_value,
        "term": query,
    }
    esearch_url = f"{PUBMED_BASE}/esearch.fcgi"
    esearch_resp = await http_client.get(esearch_url, params=esearch_params)
    esearch_resp.raise_for_status()
    esearch_json = esearch_resp.json()

    id_list = (
        esearch_json.get("esearchresult", {}).get("idlist", [])
        if isinstance(esearch_json, dict)
        else []
    )
    if not id_list:
        return []

    esummary_params = {
        **_base_params(),
        "db": "pubmed",
        "retmode": "json",
        "id": ",".join(id_list),
        "version": "2.0",
    }
    esummary_url = f"{PUBMED_BASE}/esummary.fcgi"
    esummary_resp = await http_client.get(esummary_url, params=esummary_params)
    esummary_resp.raise_for_status()
    esummary_json = esummary_resp.json()

    result = esummary_json.get("result", {}) if isinstance(esummary_json, dict) else {}
    ordered_ids = result.get("uids", [])
    articles: List[Dict[str, Any]] = []
    for uid in ordered_ids:
        item = result.get(uid, {})
        article_ids = item.get("articleids", []) if isinstance(item, dict) else []
        doi = ""
        for aid in article_ids:
            if isinstance(aid, dict) and aid.get("idtype") == "doi":
                doi = aid.get("value", "")
                break
        articles.append(
            {
                "pmid": uid,
                "title": item.get("title", ""),
                "journal": item.get("fulljournalname", ""),
                "pubdate": item.get("pubdate", ""),
                "authors": [
                    a.get("name", "")
                    for a in item.get("authors", [])
                    if isinstance(a, dict) and a.get("name")
                ],
                "doi": doi,
                "url": _pubmed_url(uid),
            }
        )
    return articles


@app.tool()
async def get_pubmed_article_details(pmid: str) -> Dict[str, Any]:
    """
    Get article details from PubMed by PMID, including abstract text when available.
    """
    pmid_clean = pmid.strip()
    if not pmid_clean:
        raise ValueError("pmid is required")

    logger.info("PubMed details: pmid=%s", pmid_clean)

    efetch_params = {
        **_base_params(),
        "db": "pubmed",
        "retmode": "xml",
        "id": pmid_clean,
    }
    efetch_url = f"{PUBMED_BASE}/efetch.fcgi"
    efetch_resp = await http_client.get(efetch_url, params=efetch_params)
    efetch_resp.raise_for_status()
    xml_text = efetch_resp.text

    root = ET.fromstring(xml_text)
    article = _find_first(root, ["PubmedArticle", "PubmedBookArticle", "MedlineCitation"])
    if article is None:
        return {"pmid": pmid_clean, "url": _pubmed_url(pmid_clean), "found": False}

    title = _find_text(article, "ArticleTitle", default="")
    journal = _find_text(article, "Title", default="")
    pub_year = _find_text(article, "Year", default="")

    abstract_parts: List[str] = []
    for node in _collect_texts(article, "AbstractText"):
        text = "".join(node.itertext()).strip()
        label = node.attrib.get("Label", "").strip()
        if text:
            abstract_parts.append(f"{label}: {text}" if label else text)

    authors: List[str] = []
    for author in _collect_texts(article, "Author"):
        last = _find_text(author, "LastName", default="")
        fore = _find_text(author, "ForeName", default="")
        collective = _find_text(author, "CollectiveName", default="")
        if collective:
            authors.append(collective)
        elif last or fore:
            authors.append(f"{fore} {last}".strip())

    doi = ""
    for id_node in _collect_texts(article, "ArticleId"):
        id_type = id_node.attrib.get("IdType", "").lower()
        if id_type == "doi" and (id_node.text or "").strip():
            doi = (id_node.text or "").strip()
            break

    found = bool(title or abstract_parts or authors or doi)

    return {
        "found": found,
        "pmid": pmid_clean,
        "title": title,
        "journal": journal,
        "publication_year": pub_year,
        "authors": authors,
        "doi": doi,
        "abstract": "\n\n".join(abstract_parts).strip(),
        "url": _pubmed_url(pmid_clean),
    }


if __name__ == "__main__":
    logger.info("Starting PubMed MCP Server (STDIO transport)")
    app.run(transport="stdio")
