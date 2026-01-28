"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   PRISM CONSENSUS - MCP INTEGRATION                          ║
║                                                                              ║
║  Intégration du système de consensus avec les MCP servers de recherche.      ║
║                                                                              ║
║  MCP Servers supportés:                                                      ║
║  - firecrawl: Collecte brute (scraping web)                                  ║
║  - playwright: Preuves & interactions                                        ║
║  - tavily: Signaux faibles & orientation                                     ║
║  - arxiv: Recherche académique                                               ║
║  - semanticscholar: Citations & auteurs                                      ║
║  - openalex: Données académiques                                             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("consensus_mcp")


# ═══════════════════════════════════════════════════════════════════════════════
# MCP TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

MCP_RESEARCH_TOOLS = {
    "firecrawl": {
        "scrape": {
            "description": "Scrape a webpage and extract clean markdown content",
            "params": {
                "url": "URL to scrape",
                "formats": ["markdown", "html"],
            }
        },
        "crawl": {
            "description": "Crawl a website starting from a URL",
            "params": {
                "url": "Starting URL",
                "limit": 10,
                "scrapeOptions": {"formats": ["markdown"]}
            }
        },
        "search": {
            "description": "Search the web and return results",
            "params": {
                "query": "Search query",
                "limit": 10
            }
        }
    },
    "playwright": {
        "navigate": {
            "description": "Navigate to a URL in browser",
            "params": {
                "url": "URL to navigate to"
            }
        },
        "screenshot": {
            "description": "Take screenshot as evidence",
            "params": {
                "path": "Path to save screenshot"
            }
        },
        "evaluate": {
            "description": "Execute JavaScript in page context",
            "params": {
                "expression": "JavaScript expression"
            }
        }
    },
    "tavily": {
        "search": {
            "description": "Search for recent web content",
            "params": {
                "query": "Search query",
                "search_depth": "advanced",
                "include_answer": True,
                "max_results": 10
            }
        }
    },
    "arxiv": {
        "search": {
            "description": "Search arXiv papers",
            "params": {
                "query": "Search query",
                "max_results": 10,
                "sort_by": "relevance"
            }
        }
    },
    "semanticscholar": {
        "search_papers": {
            "description": "Search Semantic Scholar papers",
            "params": {
                "query": "Search query",
                "limit": 10
            }
        },
        "get_paper": {
            "description": "Get paper details by ID",
            "params": {
                "paper_id": "Paper ID or DOI"
            }
        },
        "get_citations": {
            "description": "Get paper citations",
            "params": {
                "paper_id": "Paper ID"
            }
        }
    },
    "openalex": {
        "search_works": {
            "description": "Search OpenAlex works",
            "params": {
                "query": "Search query",
                "per_page": 10
            }
        },
        "search_authors": {
            "description": "Search authors",
            "params": {
                "query": "Author name"
            }
        }
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# MCP WRAPPER FOR CONSENSUS
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusMCPWrapper:
    """
    Wrapper pour intégrer les MCP servers avec le système de consensus.
    
    Toutes les données collectées sont tracées et peuvent être validées
    par le consensus avant utilisation dans la conclusion finale.
    """
    
    def __init__(self, mcp_handler: Any):
        """
        Args:
            mcp_handler: MCPConfig instance from mcp_handler.py
        """
        self.mcp = mcp_handler
        self.collection_log: List[Dict[str, Any]] = []
    
    async def collect(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any],
        trace: bool = True,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Collecte des données via MCP avec traçabilité.
        
        Args:
            server: Nom du serveur MCP
            tool: Nom de l'outil
            params: Paramètres de l'outil
            trace: Enregistrer dans le log
            
        Returns:
            Résultat de la collecte
        """
        import time
        
        start_time = time.time()
        result = {
            "server": server,
            "tool": tool,
            "params": params,
            "timestamp": start_time,
            "success": False,
            "data": None,
            "error": None
        }
        if correlation_id:
            result["correlation_id"] = correlation_id
        
        try:
            # Appeler le MCP
            if self.mcp:
                data = await self.mcp.call_tool(server, tool, params)
                result["data"] = data
                result["success"] = True
            else:
                result["error"] = "No MCP handler configured"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"MCP call failed: {server}/{tool}: {e}")
        
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        
        if trace:
            self.collection_log.append(result)
        
        logger.info(json.dumps({
            "event": "adapter_collect",
            "correlation_id": correlation_id,
            "server": server,
            "tool": tool,
            "success": result["success"],
            "duration_ms": result["duration_ms"],
        }, ensure_ascii=False))
        
        return result
    
    async def search_web(self, query: str, limit: int = 10, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Recherche web via Tavily ou Firecrawl."""
        # Essayer Tavily d'abord (meilleur pour les signaux faibles)
        result = await self.collect(
            "tavily", "search",
            {"query": query, "max_results": limit},
            correlation_id=correlation_id,
        )
        
        if not result["success"]:
            # Fallback sur Firecrawl
            result = await self.collect(
                "firecrawl", "search",
                {"query": query, "limit": limit},
                correlation_id=correlation_id,
            )
        
        return result
    
    async def scrape_url(self, url: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Scrape une URL via Firecrawl."""
        return await self.collect(
            "firecrawl", "scrape",
            {"url": url, "formats": ["markdown"]},
            correlation_id=correlation_id,
        )
    
    async def search_papers(self, query: str, sources: List[str] = None, correlation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recherche académique multi-sources.
        
        Args:
            query: Requête de recherche
            sources: Sources à interroger (default: all)
            
        Returns:
            Liste des résultats par source
        """
        if sources is None:
            sources = ["arxiv", "semanticscholar", "openalex"]
        
        tasks = []
        
        for source in sources:
            if source == "arxiv":
                tasks.append(self.collect("arxiv", "search", {"query": query}, correlation_id=correlation_id))
            elif source == "semanticscholar":
                tasks.append(self.collect("semanticscholar", "search_papers", {"query": query}, correlation_id=correlation_id))
            elif source == "openalex":
                tasks.append(self.collect("openalex", "search_works", {"query": query}, correlation_id=correlation_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, dict)]
    
    async def get_evidence(self, url: str, screenshot: bool = False, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Collecte de preuves via Playwright.
        
        Args:
            url: URL à capturer
            screenshot: Prendre un screenshot
            
        Returns:
            Données de preuve
        """
        # Navigate to page
        result = await self.collect(
            "playwright", "navigate",
            {"url": url},
            correlation_id=correlation_id,
        )
        
        if screenshot and result["success"]:
            # Take screenshot as evidence
            ss_result = await self.collect(
                "playwright", "screenshot",
                {"path": f"/tmp/evidence_{hash(url)}.png"},
                correlation_id=correlation_id,
            )
            result["screenshot"] = ss_result
        
        return result
    
    def get_collection_log(self) -> List[Dict[str, Any]]:
        """Retourne le log de collecte complet."""
        return self.collection_log.copy()
    
    def clear_log(self):
        """Efface le log de collecte."""
        self.collection_log.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH DATA AGGREGATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchDataAggregator:
    """
    Agrège et structure les données de recherche pour le consensus.
    """
    
    def __init__(self):
        self.raw_data: List[Dict[str, Any]] = []
        self.structured_data: Dict[str, Any] = {}
    
    def add_data(self, source: str, data: Any):
        """Ajoute des données brutes."""
        self.raw_data.append({
            "source": source,
            "data": data,
            "timestamp": __import__("time").time()
        })
    
    def structure_for_consensus(self) -> Dict[str, Any]:
        """
        Structure les données pour soumission au consensus.
        
        Returns:
            Données structurées pour les arbitres
        """
        sources = {}
        for item in self.raw_data:
            source = item["source"]
            if source not in sources:
                sources[source] = []
            sources[source].append(item["data"])
        
        self.structured_data = {
            "total_sources": len(sources),
            "sources": sources,
            "data_points": len(self.raw_data),
            "timestamp": __import__("time").time()
        }
        
        return self.structured_data
    
    def generate_summary(self) -> str:
        """Génère un résumé textuel des données."""
        if not self.structured_data:
            self.structure_for_consensus()
        
        lines = [
            f"Données collectées: {self.structured_data['data_points']} points",
            f"Sources: {', '.join(self.structured_data['sources'].keys())}",
        ]
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

async def research_with_consensus(
    query: str,
    mcp_handler: Any,
    consensus_manager: Any,
    call_llm_func: Callable = None,
    sources: List[str] = None
) -> Dict[str, Any]:
    """
    Fonction principale de recherche avec validation par consensus.
    
    Args:
        query: Requête de recherche
        mcp_handler: Handler MCP
        consensus_manager: ConsensusManager instance
        call_llm_func: Fonction d'appel LLM pour les arbitres
        sources: Sources MCP à utiliser
        
    Returns:
        Résultat de la recherche validé
    """
    from python.helpers.consensus_manager import (
        DecisionType, VoteType, generate_decision_hash
    )
    
    import uuid

    # 1. Initialiser le wrapper MCP
    mcp = ConsensusMCPWrapper(mcp_handler)
    aggregator = ResearchDataAggregator()
    correlation_id = str(uuid.uuid4())
    
    # 2. Collecter les données
    logger.info(f"🔍 Recherche: {query[:50]}...")
    
    # Web search
    web_result = await mcp.search_web(query, correlation_id=correlation_id)
    if web_result["success"]:
        aggregator.add_data("web", web_result["data"])
    
    # Academic search
    if sources is None or any(s in ["arxiv", "semanticscholar", "openalex"] for s in sources):
        paper_results = await mcp.search_papers(query, correlation_id=correlation_id)
        for result in paper_results:
            if result.get("success"):
                aggregator.add_data(result["server"], result["data"])
    
    # 3. Structurer pour consensus
    structured = aggregator.structure_for_consensus()
    summary = aggregator.generate_summary()
    
    # 4. Soumettre au consensus via engine (no simulated votes)
    from python.consensus.engine import run_consensus

    decision = await run_consensus(
        evidence_pack=structured,
        policy={
            "action": summary,
            "context": {"query": query, "summary": summary},
            "decision_type": DecisionType.RESEARCH_VALIDATION,
            "correlation_id": correlation_id,
        },
    )

    return {
        "query": query,
        "proposal_id": decision.proposal_id,
        "approved": decision.approved,
        "status": decision.status.value,
        "decision_time_ms": decision.decision_time_ms,
        "data": structured,
        "collection_log": mcp.get_collection_log(),
        "correlation_id": correlation_id,
        "warnings": decision.warnings,
    }
