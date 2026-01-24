"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RESEARCH EXECUTOR                                         ║
║                                                                              ║
║  Câblage entre ResearchToolPolicy et ReasoningEngine.                        ║
║  Exécute les outils MCP de recherche sous contrainte de policy.              ║
║                                                                              ║
║  Architecture:                                                               ║
║  1. Détecte l'intention depuis la query                                      ║
║  2. Valide les outils autorisés via ResearchToolPolicy                       ║
║  3. Exécute dans l'ordre (primary → fallback)                                ║
║  4. Retourne résultat structuré avec audit                                   ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

from python.helpers.research_tool_policy import (
    ResearchToolPolicy,
    ResearchIntent,
    IntentPolicy,
    AllowedTool,
    PolicyDecision,
    ToolPolicyViolation,
    IntentNotAllowed,
    get_research_policy,
    ACTIVE_SERVERS,
    DISABLED_SERVERS,
    INTENT_POLICIES,
)

from python.helpers.reasoning_engine import (
    ReasoningContext,
    ReasoningOutcome,
    ReasoningFlag,
    Subtask,
    TraceStep,
    ExecutionStatus,
    sanitize_exception,
)


logger = logging.getLogger("research_executor")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ResearchExecutorConfig:
    """Configuration de l'exécuteur de recherche."""
    # Timeouts
    default_timeout_ms: int = 10000       # 10s par appel
    total_budget_ms: int = 30000          # 30s total
    
    # Limites
    max_tools_per_query: int = 3
    max_fallback_attempts: int = 2
    
    # Logs
    log_file: Optional[str] = "logs/research_tool_calls.jsonl"
    log_args: bool = False                # Ne pas logger les args (PII)
    
    # Comportement
    stop_on_success: bool = True          # Arrêter dès qu'on a un résultat
    require_non_empty: bool = True        # Résultat doit être non-vide


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolCallResult:
    """Résultat d'un appel tool."""
    server: str
    tool: str
    success: bool
    result: Any
    duration_ms: int
    error: Optional[str] = None
    is_fallback: bool = False
    
    def is_valid(self) -> bool:
        """Vérifie si le résultat est valide (non-vide)."""
        if not self.success:
            return False
        if self.result is None:
            return False
        if isinstance(self.result, str) and not self.result.strip():
            return False
        if isinstance(self.result, list) and len(self.result) == 0:
            return False
        if isinstance(self.result, dict):
            if len(self.result) == 0:
                return False
            # Check for common empty data patterns
            for key in ("data", "results", "items", "papers", "documents", "works"):
                if key in self.result:
                    val = self.result[key]
                    if isinstance(val, list) and len(val) == 0:
                        return False
        return True


@dataclass
class ResearchResult:
    """Résultat complet d'une recherche."""
    intent: ResearchIntent
    query: str
    success: bool
    data: Any
    tools_called: List[ToolCallResult]
    total_duration_ms: int
    correlation_id: str
    warnings: List[str] = field(default_factory=list)
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Export sans PII pour logging."""
        return {
            "correlation_id": self.correlation_id,
            "intent": self.intent.value,
            "success": self.success,
            "tools_count": len(self.tools_called),
            "duration_ms": self.total_duration_ms,
            "warnings_count": len(self.warnings),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MCP TOOL CALLER PROTOCOL
# ═══════════════════════════════════════════════════════════════════════════════

class MCPToolCaller(Protocol):
    """
    Protocol pour appeler les outils MCP.
    
    Doit être implémenté par l'intégration avec agent-zero.
    """
    
    async def call(
        self,
        server: str,
        tool: str,
        args: Dict[str, Any],
        timeout_ms: int = 10000,
    ) -> Any:
        """
        Appelle un outil MCP.
        
        Args:
            server: Nom du serveur MCP (ex: "arxiv", "semanticscholar")
            tool: Nom de l'outil (ex: "search_papers")
            args: Arguments de l'outil
            timeout_ms: Timeout en millisecondes
        
        Returns:
            Résultat de l'outil (JSON-compatible)
        
        Raises:
            TimeoutError: Si timeout
            Exception: Si erreur d'exécution
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK TOOL CALLER (pour tests)
# ═══════════════════════════════════════════════════════════════════════════════

class MockMCPToolCaller:
    """
    Mock pour tests sans vrais serveurs MCP.
    
    Retourne des données simulées selon le serveur/tool.
    """
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self._responses = responses or {}
        self._calls: List[Dict[str, Any]] = []
    
    async def call(
        self,
        server: str,
        tool: str,
        args: Dict[str, Any],
        timeout_ms: int = 10000,
    ) -> Any:
        """Mock call - retourne données simulées."""
        call_key = f"{server}.{tool}"
        
        # Enregistrer l'appel
        self._calls.append({
            "server": server,
            "tool": tool,
            "args": args,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Vérifier si réponse personnalisée
        if call_key in self._responses:
            return self._responses[call_key]
        
        # Réponses par défaut selon le serveur
        if server == "arxiv":
            return {
                "papers": [
                    {"title": "Sample Paper 1", "arxiv_id": "2401.00001"},
                    {"title": "Sample Paper 2", "arxiv_id": "2401.00002"},
                ]
            }
        
        if server == "semanticscholar":
            return {
                "data": [
                    {"title": "Semantic Paper 1", "paperId": "abc123", "citationCount": 42},
                    {"title": "Semantic Paper 2", "paperId": "def456", "citationCount": 17},
                ]
            }
        
        if server == "openalex":
            return {
                "results": [
                    {"title": "OpenAlex Work 1", "id": "W123"},
                    {"title": "OpenAlex Work 2", "id": "W456"},
                ]
            }
        
        if server == "crossref":
            return {
                "message": {
                    "items": [
                        {"title": ["Crossref Paper 1"], "DOI": "10.1234/test1"},
                    ]
                }
            }
        
        if server == "eurlex":
            return {
                "documents": [
                    {"celex": "32016R0679", "title": "GDPR", "type": "Regulation"},
                ]
            }
        
        # Serveurs désactivés
        if server in DISABLED_SERVERS:
            raise ToolPolicyViolation(f"Server {server} is DISABLED")
        
        return {"status": "ok", "server": server, "tool": tool}
    
    def get_calls(self) -> List[Dict[str, Any]]:
        """Retourne l'historique des appels."""
        return self._calls.copy()
    
    def reset(self):
        """Reset l'historique."""
        self._calls.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchExecutor:
    """
    Exécuteur de recherche avec contraintes de policy.
    
    Câble ResearchToolPolicy avec les appels MCP réels.
    
    Usage:
    ```python
    executor = ResearchExecutor(tool_caller, config)
    result = await executor.execute("Find papers on RAG evaluation")
    ```
    """
    
    def __init__(
        self,
        tool_caller: MCPToolCaller,
        config: Optional[ResearchExecutorConfig] = None,
        policy: Optional[ResearchToolPolicy] = None,
    ):
        self.tool_caller = tool_caller
        self.config = config or ResearchExecutorConfig()
        self.policy = policy or get_research_policy()
        
        # Stats
        self._total_calls = 0
        self._successful_calls = 0
        
        # Log file
        self._log_path: Optional[Path] = None
        if self.config.log_file:
            self._log_path = Path(self.config.log_file)
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def execute(
        self,
        query: str,
        intent: Optional[ResearchIntent] = None,
        params: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> ResearchResult:
        """
        Exécute une recherche sous contrainte de policy.
        
        Args:
            query: Requête utilisateur
            intent: Intent explicite (si None, détecté automatiquement)
            params: Paramètres additionnels pour les tools
            correlation_id: ID de corrélation pour logs
        
        Returns:
            ResearchResult avec données et audit
        """
        start_time = time.time()
        correlation_id = correlation_id or f"re_{uuid.uuid4().hex[:12]}"
        params = params or {}
        warnings: List[str] = []
        
        # 1. Détecter l'intention si non fournie
        if intent is None:
            intent = self.policy.suggest_intent(query)
            if intent is None:
                intent = ResearchIntent.PAPER_SEARCH
        
        # 2. Obtenir les outils autorisés
        decision = self.policy.get_tools_for_intent(intent)
        
        if not decision.allowed:
            return ResearchResult(
                intent=intent,
                query=query,
                success=False,
                data=None,
                tools_called=[],
                total_duration_ms=int((time.time() - start_time) * 1000),
                correlation_id=correlation_id,
                warnings=[decision.reason],
            )
        
        # 3. Construire les arguments pour chaque tool
        tool_args = self._build_tool_args(query, intent, params)
        
        # 4. Exécuter les tools dans l'ordre
        tools_called: List[ToolCallResult] = []
        final_result = None
        budget_remaining_ms = self.config.total_budget_ms
        
        # Primary tools first
        primary_tools = [t for t in decision.tools_to_use if not t.is_fallback]
        fallback_tools = [t for t in decision.tools_to_use if t.is_fallback]
        
        for tool in primary_tools:
            if budget_remaining_ms <= 0:
                warnings.append("Budget exhausted before completing all tools")
                break
            
            tool_result = await self._call_tool(
                tool,
                tool_args.get(tool.tool, {"query": query}),
                min(self.config.default_timeout_ms, budget_remaining_ms),
                correlation_id,
                is_fallback=False,
            )
            
            tools_called.append(tool_result)
            budget_remaining_ms -= tool_result.duration_ms
            
            if tool_result.is_valid():
                final_result = tool_result.result
                if self.config.stop_on_success:
                    break
            elif tool_result.success:
                # Result returned but was empty - continue to next tool
                pass
        
        # Fallback if no valid result
        if final_result is None and fallback_tools:
            for i, tool in enumerate(fallback_tools):
                if i >= self.config.max_fallback_attempts:
                    break
                if budget_remaining_ms <= 0:
                    break
                
                tool_result = await self._call_tool(
                    tool,
                    tool_args.get(tool.tool, {"query": query}),
                    min(self.config.default_timeout_ms, budget_remaining_ms),
                    correlation_id,
                    is_fallback=True,
                )
                
                tools_called.append(tool_result)
                budget_remaining_ms -= tool_result.duration_ms
                
                if tool_result.is_valid():
                    final_result = tool_result.result
                    warnings.append(f"Used fallback: {tool.full_name}")
                    break
        
        # 5. Vérifier le résultat
        success = final_result is not None
        if not success:
            warnings.append("No valid result from any tool")
        
        total_duration_ms = int((time.time() - start_time) * 1000)
        
        result = ResearchResult(
            intent=intent,
            query=query,
            success=success,
            data=final_result,
            tools_called=tools_called,
            total_duration_ms=total_duration_ms,
            correlation_id=correlation_id,
            warnings=warnings,
        )
        
        # Log résumé
        self._log_execution(result)
        
        return result
    
    async def _call_tool(
        self,
        tool: AllowedTool,
        args: Dict[str, Any],
        timeout_ms: int,
        correlation_id: str,
        is_fallback: bool,
    ) -> ToolCallResult:
        """Appelle un outil avec timeout et logging."""
        start_time = time.time()
        self._total_calls += 1
        
        try:
            # Valider via policy
            # (déjà validé par get_tools_for_intent, mais double-check)
            if tool.server in DISABLED_SERVERS:
                raise ToolPolicyViolation(f"Server {tool.server} is DISABLED")
            
            # Appeler le tool
            result = await asyncio.wait_for(
                self.tool_caller.call(
                    server=tool.server,
                    tool=tool.tool,
                    args=args,
                    timeout_ms=timeout_ms,
                ),
                timeout=timeout_ms / 1000,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            self._successful_calls += 1
            
            # Log l'appel
            self._log_tool_call(
                correlation_id=correlation_id,
                server=tool.server,
                tool=tool.tool,
                args_hash=self._hash_args(args),
                duration_ms=duration_ms,
                ok=True,
                error_type=None,
                response_size=self._estimate_size(result),
            )
            
            return ToolCallResult(
                server=tool.server,
                tool=tool.tool,
                success=True,
                result=result,
                duration_ms=duration_ms,
                is_fallback=is_fallback,
            )
            
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_tool_call(
                correlation_id=correlation_id,
                server=tool.server,
                tool=tool.tool,
                args_hash=self._hash_args(args),
                duration_ms=duration_ms,
                ok=False,
                error_type="timeout",
                response_size=0,
            )
            return ToolCallResult(
                server=tool.server,
                tool=tool.tool,
                success=False,
                result=None,
                duration_ms=duration_ms,
                error="Timeout",
                is_fallback=is_fallback,
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            safe_error = sanitize_exception(e)
            self._log_tool_call(
                correlation_id=correlation_id,
                server=tool.server,
                tool=tool.tool,
                args_hash=self._hash_args(args),
                duration_ms=duration_ms,
                ok=False,
                error_type=safe_error["error_type"],
                response_size=0,
            )
            return ToolCallResult(
                server=tool.server,
                tool=tool.tool,
                success=False,
                result=None,
                duration_ms=duration_ms,
                error=safe_error["message"],
                is_fallback=is_fallback,
            )
    
    def _build_tool_args(
        self,
        query: str,
        intent: ResearchIntent,
        params: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Construit les arguments pour chaque tool selon l'intent."""
        args: Dict[str, Dict[str, Any]] = {}
        
        # Arguments communs
        base_args = {"query": query, **params}
        
        # Arguments spécifiques par tool
        if intent in (ResearchIntent.PAPER_SEARCH, ResearchIntent.PAPER_LATEST, ResearchIntent.PAPER_INFLUENTIAL):
            args["search_semantic_scholar"] = {"query": query, "limit": params.get("limit", 10)}
            args["search_works"] = {"query": query, "per_page": params.get("limit", 10)}
            args["search_papers"] = {"query": query, "max_results": params.get("limit", 10)}
            args["search_by_title"] = {"title": query}
        
        elif intent == ResearchIntent.DOI_LOOKUP:
            doi = params.get("doi") or self._extract_doi(query)
            args["get_work_by_doi"] = {"doi": doi} if doi else {"doi": query}
        
        elif intent in (ResearchIntent.AUTHOR_FIND, ResearchIntent.AUTHOR_PROFILE):
            args["autocomplete_authors"] = {"query": query}
            args["search_authors"] = {"query": query}
            args["get_author_details"] = {"author_id": params.get("author_id", query)}
        
        elif intent == ResearchIntent.AUTHOR_WORKS:
            args["retrieve_author_works"] = {"author_id": params.get("author_id", query)}
            args["search_papers"] = {"query": f"author:{query}"}
        
        elif intent in (ResearchIntent.CITATION_ANALYSIS, ResearchIntent.CITATION_NETWORK):
            paper_id = params.get("paper_id", query)
            args["get_citations_and_references"] = {"paper_id": paper_id}
            args["get_paper_details"] = {"paper_id": paper_id}
        
        elif intent == ResearchIntent.EU_LEGISLATION:
            args["search_eu_legislation"] = {"query": query}
            args["search_by_subject"] = {"subject": query}
            celex = params.get("celex") or self._extract_celex(query)
            if celex:
                args["get_document_by_celex"] = {"celex": celex}
        
        elif intent == ResearchIntent.EU_CASE_LAW:
            args["search_eu_case_law"] = {"query": query}
            celex = params.get("celex") or self._extract_celex(query)
            if celex:
                args["get_document_by_celex"] = {"celex": celex}
        
        elif intent == ResearchIntent.EU_LEGAL_FULL:
            args["search_eu_legislation"] = {"query": query}
            args["search_eu_case_law"] = {"query": query}
            celex = params.get("celex") or self._extract_celex(query)
            if celex:
                args["get_document_citations"] = {"celex": celex}
                args["get_legislation_timeline"] = {"celex": celex}
        
        elif intent == ResearchIntent.LITERATURE_REVIEW:
            args["search_papers"] = {"query": query, "max_results": 20}
            args["search_semantic_scholar"] = {"query": query, "limit": 20}
            args["search_works"] = {"query": query, "per_page": 20}
        
        elif intent == ResearchIntent.EXPERT_DISCOVERY:
            args["autocomplete_authors"] = {"query": query}
            args["search_authors"] = {"query": query}
        
        return args
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """Extrait un DOI d'un texte."""
        import re
        match = re.search(r'10\.\d{4,}/[^\s]+', text)
        return match.group(0) if match else None
    
    def _extract_celex(self, text: str) -> Optional[str]:
        """Extrait un numéro CELEX d'un texte."""
        import re
        # Format: 3YYYYLNNNN ou 6YYYYJNNNN
        match = re.search(r'[36]\d{4}[A-Z]\d{4}', text.upper())
        return match.group(0) if match else None
    
    def _hash_args(self, args: Dict[str, Any]) -> str:
        """Hash des arguments (pas de PII dans logs)."""
        return hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16]
    
    def _estimate_size(self, result: Any) -> int:
        """Estime la taille du résultat."""
        try:
            return len(json.dumps(result))
        except:
            return 0
    
    def _log_tool_call(
        self,
        correlation_id: str,
        server: str,
        tool: str,
        args_hash: str,
        duration_ms: int,
        ok: bool,
        error_type: Optional[str],
        response_size: int,
    ):
        """Log un appel tool en JSONL."""
        if not self._log_path:
            return
        
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "server": server,
            "tool": tool,
            "args_hash": args_hash,
            "duration_ms": duration_ms,
            "ok": ok,
            "error_type": error_type,
            "response_size": response_size,
        }
        
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write log: {e}")
    
    def _log_execution(self, result: ResearchResult):
        """Log un résumé d'exécution."""
        logger.info(json.dumps({
            "event": "research_execution",
            **result.to_safe_dict(),
        }))
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les stats."""
        return {
            "total_calls": self._total_calls,
            "successful_calls": self._successful_calls,
            "success_rate": self._successful_calls / max(self._total_calls, 1),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION WITH REASONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchToolExecutor:
    """
    Adaptateur pour intégrer ResearchExecutor dans ReasoningEngine.
    
    Implémente le protocol Executor de reasoning_engine.py.
    
    Usage:
    ```python
    from python.helpers.reasoning_engine import ReasoningEngine
    from python.helpers.research_executor import ResearchToolExecutor, MockMCPToolCaller
    
    tool_caller = MockMCPToolCaller()  # ou vrai caller MCP
    research_executor = ResearchToolExecutor(tool_caller)
    
    engine = ReasoningEngine(
        tool_executor=research_executor,
    )
    ```
    """
    
    def __init__(
        self,
        tool_caller: MCPToolCaller,
        config: Optional[ResearchExecutorConfig] = None,
    ):
        self._executor = ResearchExecutor(tool_caller, config)
    
    async def execute(
        self,
        subtask: Subtask,
        context: ReasoningContext,
    ) -> tuple[str, float]:
        """
        Exécute une sous-tâche de recherche.
        
        Compatible avec le protocol Executor de ReasoningEngine.
        
        Returns:
            (result_text, confidence)
        """
        # Déterminer l'intent depuis la description de la subtask
        query = subtask.description
        
        # Exécuter la recherche
        result = await self._executor.execute(query)
        
        if result.success and result.data:
            # Formater le résultat
            result_text = self._format_result(result)
            confidence = 0.85 if not result.warnings else 0.7
            return result_text, confidence
        else:
            # Échec
            error_msg = "; ".join(result.warnings) if result.warnings else "No results found"
            return error_msg, 0.3
    
    def _format_result(self, result: ResearchResult) -> str:
        """Formate le résultat pour affichage."""
        data = result.data
        
        # Extraire les éléments pertinents
        if isinstance(data, dict):
            # Semantic Scholar format
            if "data" in data:
                items = data["data"]
                if isinstance(items, list) and items:
                    return f"Found {len(items)} papers: " + ", ".join(
                        item.get("title", "Untitled")[:50] for item in items[:3]
                    )
            
            # arXiv format
            if "papers" in data:
                items = data["papers"]
                if isinstance(items, list) and items:
                    return f"Found {len(items)} papers: " + ", ".join(
                        item.get("title", "Untitled")[:50] for item in items[:3]
                    )
            
            # OpenAlex format
            if "results" in data:
                items = data["results"]
                if isinstance(items, list) and items:
                    return f"Found {len(items)} works: " + ", ".join(
                        item.get("title", "Untitled")[:50] for item in items[:3]
                    )
            
            # EUR-Lex format
            if "documents" in data:
                items = data["documents"]
                if isinstance(items, list) and items:
                    return f"Found {len(items)} documents: " + ", ".join(
                        item.get("title", item.get("celex", "Unknown"))[:50] for item in items[:3]
                    )
        
        # Fallback
        return json.dumps(data)[:200] if data else "No data"


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_research_executor(
    tool_caller: Optional[MCPToolCaller] = None,
    use_mock: bool = False,
) -> ResearchExecutor:
    """
    Crée un ResearchExecutor configuré.
    
    Args:
        tool_caller: Caller MCP (si None et use_mock=True, utilise mock)
        use_mock: Utiliser le mock pour tests
    
    Returns:
        ResearchExecutor configuré
    """
    if tool_caller is None and use_mock:
        tool_caller = MockMCPToolCaller()
    elif tool_caller is None:
        raise ValueError("tool_caller required when use_mock=False")
    
    return ResearchExecutor(tool_caller)


async def quick_research(
    query: str,
    intent: Optional[ResearchIntent] = None,
    use_mock: bool = True,
) -> ResearchResult:
    """
    Recherche rapide (principalement pour tests/démo).
    
    Args:
        query: Requête
        intent: Intent (auto-détecté si None)
        use_mock: Utiliser le mock
    
    Returns:
        ResearchResult
    """
    executor = create_research_executor(use_mock=use_mock)
    return await executor.execute(query, intent=intent)
