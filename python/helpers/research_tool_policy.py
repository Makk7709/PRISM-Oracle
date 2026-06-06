"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RESEARCH TOOL POLICY                                      ║
║                                                                              ║
║  Constrains Evidence to use the RIGHT tools for each research intent.          ║
║  Transforms "intelligent when it wants" → "constrained to be intelligent"    ║
║                                                                              ║
║  Architecture:                                                               ║
║  1. Agent declares INTENT (not tools)                                        ║
║  2. Policy selects ALLOWED TOOLS for that intent                             ║
║  3. Policy enforces ORDER and FALLBACK                                       ║
║  4. Blocked tools raise clear exceptions                                     ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger("research_tool_policy")


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH INTENTS
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchIntent(str, Enum):
    """Declared research intentions that Evidence can express."""
    
    # Paper/Publication searches
    PAPER_SEARCH = "paper_search"
    PAPER_LATEST = "paper_latest"           # Emphasis on recency
    PAPER_INFLUENTIAL = "paper_influential"  # Emphasis on citations
    
    # Author research
    AUTHOR_FIND = "author_find"
    AUTHOR_PROFILE = "author_profile"
    AUTHOR_WORKS = "author_works"
    
    # Citation analysis
    CITATION_ANALYSIS = "citation_analysis"
    CITATION_NETWORK = "citation_network"
    
    # DOI/Metadata
    DOI_LOOKUP = "doi_lookup"
    METADATA_VERIFY = "metadata_verify"
    
    # EU Legal
    EU_LEGISLATION = "eu_legislation"
    EU_CASE_LAW = "eu_case_law"
    EU_LEGAL_FULL = "eu_legal_full"
    
    # Combined/Complex
    LITERATURE_REVIEW = "literature_review"
    EXPERT_DISCOVERY = "expert_discovery"
    
    # Forbidden (disabled servers)
    PATENT_SEARCH = "patent_search"         # BLOCKED


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AllowedTool:
    """A tool allowed for a specific intent."""
    server: str
    tool: str
    priority: int = 1           # Lower = higher priority (called first)
    is_fallback: bool = False   # True = only if primary fails
    
    @property
    def full_name(self) -> str:
        return f"{self.server}.{self.tool}"


@dataclass
class IntentPolicy:
    """Policy for a specific intent."""
    intent: ResearchIntent
    allowed_tools: list[AllowedTool]
    description: str
    max_tools_per_run: int = 3
    require_cross_reference: bool = False
    
    def get_primary_tools(self) -> list[AllowedTool]:
        """Get non-fallback tools sorted by priority."""
        return sorted(
            [t for t in self.allowed_tools if not t.is_fallback],
            key=lambda t: t.priority
        )
    
    def get_fallback_tools(self) -> list[AllowedTool]:
        """Get fallback tools."""
        return [t for t in self.allowed_tools if t.is_fallback]
    
    def is_tool_allowed(self, server: str, tool: str) -> bool:
        """Check if a tool is allowed for this intent."""
        full_name = f"{server}.{tool}"
        return any(t.full_name == full_name for t in self.allowed_tools)


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

# Active servers (no API key required)
ACTIVE_SERVERS = {"arxiv", "semanticscholar", "openalex", "crossref", "eurlex"}

# Disabled servers (require API keys)
DISABLED_SERVERS = {"lens", "espacenet"}

# Intent → Allowed Tools mapping
INTENT_POLICIES: dict[ResearchIntent, IntentPolicy] = {
    
    # ─────────────────────────────────────────────────────────────────────────
    # PAPER SEARCHES
    # ─────────────────────────────────────────────────────────────────────────
    
    ResearchIntent.PAPER_SEARCH: IntentPolicy(
        intent=ResearchIntent.PAPER_SEARCH,
        description="General paper/publication search",
        allowed_tools=[
            AllowedTool("semanticscholar", "search_semantic_scholar", priority=1),
            AllowedTool("openalex", "search_works", priority=2),
            AllowedTool("arxiv", "search_papers", priority=3),
            AllowedTool("crossref", "search_by_title", priority=4, is_fallback=True),
        ],
        max_tools_per_run=2,
    ),
    
    ResearchIntent.PAPER_LATEST: IntentPolicy(
        intent=ResearchIntent.PAPER_LATEST,
        description="Find latest/recent papers (preprints)",
        allowed_tools=[
            AllowedTool("arxiv", "search_papers", priority=1),  # arXiv first for recency
            AllowedTool("semanticscholar", "search_semantic_scholar", priority=2, is_fallback=True),
        ],
        max_tools_per_run=2,
    ),
    
    ResearchIntent.PAPER_INFLUENTIAL: IntentPolicy(
        intent=ResearchIntent.PAPER_INFLUENTIAL,
        description="Find highly-cited/influential papers",
        allowed_tools=[
            AllowedTool("semanticscholar", "search_semantic_scholar", priority=1),
            AllowedTool("openalex", "search_works", priority=2, is_fallback=True),
        ],
        max_tools_per_run=2,
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # AUTHOR RESEARCH
    # ─────────────────────────────────────────────────────────────────────────
    
    ResearchIntent.AUTHOR_FIND: IntentPolicy(
        intent=ResearchIntent.AUTHOR_FIND,
        description="Find/disambiguate an author",
        allowed_tools=[
            AllowedTool("openalex", "autocomplete_authors", priority=1),
            AllowedTool("openalex", "search_authors", priority=2),
            AllowedTool("semanticscholar", "get_author_details", priority=3, is_fallback=True),
        ],
        max_tools_per_run=2,
    ),
    
    ResearchIntent.AUTHOR_PROFILE: IntentPolicy(
        intent=ResearchIntent.AUTHOR_PROFILE,
        description="Get author profile/metrics (h-index, etc.)",
        allowed_tools=[
            AllowedTool("openalex", "search_authors", priority=1),
            AllowedTool("semanticscholar", "get_author_details", priority=2),
        ],
        max_tools_per_run=2,
        require_cross_reference=True,  # Get from both for accuracy
    ),
    
    ResearchIntent.AUTHOR_WORKS: IntentPolicy(
        intent=ResearchIntent.AUTHOR_WORKS,
        description="Get publications by an author",
        allowed_tools=[
            AllowedTool("openalex", "retrieve_author_works", priority=1),
            AllowedTool("arxiv", "search_papers", priority=2, is_fallback=True),  # For preprints
        ],
        max_tools_per_run=2,
    ),
    
    # CITATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    ResearchIntent.CITATION_ANALYSIS: IntentPolicy(
        intent=ResearchIntent.CITATION_ANALYSIS,
        description="Analyze citations of a paper",
        allowed_tools=[
            AllowedTool("semanticscholar", "get_citations_and_references", priority=1),
            AllowedTool("semanticscholar", "get_paper_details", priority=2),
        ],
        max_tools_per_run=2,
    ),
    
    ResearchIntent.CITATION_NETWORK: IntentPolicy(
        intent=ResearchIntent.CITATION_NETWORK,
        description="Build citation network/graph",
        allowed_tools=[
            AllowedTool("semanticscholar", "get_citations_and_references", priority=1),
            AllowedTool("semanticscholar", "get_paper_details", priority=2),
        ],
        max_tools_per_run=3,
    ),
    
    # DOI / METADATA
    # ─────────────────────────────────────────────────────────────────────────
    
    ResearchIntent.DOI_LOOKUP: IntentPolicy(
        intent=ResearchIntent.DOI_LOOKUP,
        description="Look up paper by DOI",
        allowed_tools=[
            AllowedTool("crossref", "get_work_by_doi", priority=1),  # Authoritative
        ],
        max_tools_per_run=1,
    ),
    
    ResearchIntent.METADATA_VERIFY: IntentPolicy(
        intent=ResearchIntent.METADATA_VERIFY,
        description="Verify/get publication metadata",
        allowed_tools=[
            AllowedTool("crossref", "get_work_by_doi", priority=1),
            AllowedTool("crossref", "search_by_title", priority=2),
            AllowedTool("semanticscholar", "get_paper_details", priority=3, is_fallback=True),
        ],
        max_tools_per_run=2,
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # EU LEGAL
    # ─────────────────────────────────────────────────────────────────────────
    
    ResearchIntent.EU_LEGISLATION: IntentPolicy(
        intent=ResearchIntent.EU_LEGISLATION,
        description="Search EU legislation (regulations, directives)",
        allowed_tools=[
            AllowedTool("eurlex", "search_eu_legislation", priority=1),
            AllowedTool("eurlex", "get_document_by_celex", priority=2),
            AllowedTool("eurlex", "search_by_subject", priority=3),
        ],
        max_tools_per_run=2,
    ),
    
    ResearchIntent.EU_CASE_LAW: IntentPolicy(
        intent=ResearchIntent.EU_CASE_LAW,
        description="Search EU case law (CJEU judgments)",
        allowed_tools=[
            AllowedTool("eurlex", "search_eu_case_law", priority=1),
            AllowedTool("eurlex", "get_document_by_celex", priority=2),
        ],
        max_tools_per_run=2,
    ),
    
    ResearchIntent.EU_LEGAL_FULL: IntentPolicy(
        intent=ResearchIntent.EU_LEGAL_FULL,
        description="Comprehensive EU legal research",
        allowed_tools=[
            AllowedTool("eurlex", "search_eu_legislation", priority=1),
            AllowedTool("eurlex", "search_eu_case_law", priority=2),
            AllowedTool("eurlex", "get_document_citations", priority=3),
            AllowedTool("eurlex", "get_legislation_timeline", priority=4),
        ],
        max_tools_per_run=4,
    ),
    
    # COMPLEX / COMBINED
    # ─────────────────────────────────────────────────────────────────────────
    
    ResearchIntent.LITERATURE_REVIEW: IntentPolicy(
        intent=ResearchIntent.LITERATURE_REVIEW,
        description="Comprehensive literature review",
        allowed_tools=[
            AllowedTool("arxiv", "search_papers", priority=1),
            AllowedTool("semanticscholar", "search_semantic_scholar", priority=2),
            AllowedTool("openalex", "search_works", priority=3),
            AllowedTool("crossref", "search_by_title", priority=4, is_fallback=True),
        ],
        max_tools_per_run=3,
        require_cross_reference=True,
    ),
    
    ResearchIntent.EXPERT_DISCOVERY: IntentPolicy(
        intent=ResearchIntent.EXPERT_DISCOVERY,
        description="Find experts in a field",
        allowed_tools=[
            AllowedTool("openalex", "autocomplete_authors", priority=1),
            AllowedTool("openalex", "search_authors", priority=2),
            AllowedTool("openalex", "retrieve_author_works", priority=3),
            AllowedTool("semanticscholar", "get_author_details", priority=4),
        ],
        max_tools_per_run=3,
    ),
    
    # BLOCKED
    # ─────────────────────────────────────────────────────────────────────────
    
    ResearchIntent.PATENT_SEARCH: IntentPolicy(
        intent=ResearchIntent.PATENT_SEARCH,
        description="⛔ BLOCKED - Patent servers not configured",
        allowed_tools=[],  # Empty = blocked
        max_tools_per_run=0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class ToolPolicyViolation(Exception):
    """Raised when a tool call violates the policy."""
    pass


class IntentNotAllowed(Exception):
    """Raised when an intent is blocked."""
    pass


@dataclass
class PolicyDecision:
    """Result of policy check."""
    allowed: bool
    intent: ResearchIntent
    tools_to_use: list[AllowedTool]
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionLog:
    """Log of tool execution under policy."""
    intent: ResearchIntent
    tool_called: str
    success: bool
    fallback_used: bool
    duration_ms: int
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class ResearchToolPolicy:
    """
    Enforces tool selection based on declared intent.
    
    Usage:
    ```python
    policy = ResearchToolPolicy()
    
    # Agent declares intent
    decision = policy.get_tools_for_intent(ResearchIntent.PAPER_SEARCH)
    
    # Check if specific tool is allowed
    if policy.is_tool_allowed(ResearchIntent.PAPER_SEARCH, "arxiv", "search_papers"):
        # Execute tool
        pass
    else:
        # Blocked
        pass
    ```
    """
    
    def __init__(self):
        self.execution_log: list[ExecutionLog] = []
        self._blocked_intents = {ResearchIntent.PATENT_SEARCH}
    
    def get_tools_for_intent(self, intent: ResearchIntent) -> PolicyDecision:
        """
        Get allowed tools for a declared intent.
        
        Returns PolicyDecision with tools to use in order.
        """
        if intent in self._blocked_intents:
            return PolicyDecision(
                allowed=False,
                intent=intent,
                tools_to_use=[],
                reason=f"Intent {intent.value} is BLOCKED. Patent servers are not configured."
            )
        
        policy = INTENT_POLICIES.get(intent)
        if not policy:
            return PolicyDecision(
                allowed=False,
                intent=intent,
                tools_to_use=[],
                reason=f"Unknown intent: {intent.value}"
            )
        
        # Filter to only active servers
        active_tools = [
            t for t in policy.allowed_tools 
            if t.server in ACTIVE_SERVERS
        ]
        
        if not active_tools:
            return PolicyDecision(
                allowed=False,
                intent=intent,
                tools_to_use=[],
                reason=f"No active servers available for intent {intent.value}"
            )
        
        return PolicyDecision(
            allowed=True,
            intent=intent,
            tools_to_use=active_tools[:policy.max_tools_per_run],
            reason=f"Allowed: {[t.full_name for t in active_tools[:policy.max_tools_per_run]]}"
        )
    
    def is_tool_allowed(self, intent: ResearchIntent, server: str, tool: str) -> bool:
        """Check if a specific tool is allowed for an intent."""
        if intent in self._blocked_intents:
            return False
        
        if server in DISABLED_SERVERS:
            return False
        
        policy = INTENT_POLICIES.get(intent)
        if not policy:
            return False
        
        return policy.is_tool_allowed(server, tool)
    
    def validate_tool_call(self, intent: ResearchIntent, server: str, tool: str) -> None:
        """
        Validate a tool call. Raises exception if not allowed.
        
        Use this as a guard before executing any MCP tool.
        """
        if intent in self._blocked_intents:
            raise IntentNotAllowed(
                f"Intent '{intent.value}' is BLOCKED. "
                f"Patent search is not available in this instance."
            )
        
        if server in DISABLED_SERVERS:
            raise ToolPolicyViolation(
                f"Server '{server}' is DISABLED (requires API key). "
                f"Cannot call {server}.{tool}"
            )
        
        if not self.is_tool_allowed(intent, server, tool):
            policy = INTENT_POLICIES.get(intent)
            allowed = [t.full_name for t in policy.allowed_tools] if policy else []
            raise ToolPolicyViolation(
                f"Tool '{server}.{tool}' is NOT ALLOWED for intent '{intent.value}'. "
                f"Allowed tools: {allowed}"
            )
    
    def log_execution(
        self, 
        intent: ResearchIntent, 
        tool: str, 
        success: bool,
        fallback_used: bool = False,
        duration_ms: int = 0,
        error: Optional[str] = None
    ):
        """Log a tool execution."""
        self.execution_log.append(ExecutionLog(
            intent=intent,
            tool_called=tool,
            success=success,
            fallback_used=fallback_used,
            duration_ms=duration_ms,
            error=error
        ))
        
        # Log to standard logger
        if success:
            logger.info(f"[{intent.value}] {tool} executed successfully in {duration_ms}ms")
        else:
            logger.warning(f"[{intent.value}] {tool} FAILED: {error}")
    
    def get_fallback_for_intent(self, intent: ResearchIntent) -> list[AllowedTool]:
        """Get fallback tools for an intent."""
        policy = INTENT_POLICIES.get(intent)
        if not policy:
            return []
        
        return [
            t for t in policy.get_fallback_tools()
            if t.server in ACTIVE_SERVERS
        ]
    
    def suggest_intent(self, user_query: str) -> Optional[ResearchIntent]:
        """
        Suggest an intent based on user query keywords.
        
        This is a helper - the agent should still declare the intent.
        """
        query_lower = user_query.lower()
        
        # EU Legal
        if any(kw in query_lower for kw in ["gdpr", "rgpd", "directive", "regulation eu", "eurlex", "celex", "cjeu", "european court"]):
            if any(kw in query_lower for kw in ["case", "judgment", "ruling", "cjeu", "court"]):
                return ResearchIntent.EU_CASE_LAW
            return ResearchIntent.EU_LEGISLATION
        
        # Patents - BLOCKED
        if any(kw in query_lower for kw in ["patent", "brevet", "invention", "claims"]):
            return ResearchIntent.PATENT_SEARCH  # Will be blocked
        
        # DOI
        if "doi" in query_lower or "10." in query_lower:
            return ResearchIntent.DOI_LOOKUP
        
        # Author
        if any(kw in query_lower for kw in ["author", "researcher", "professor", "h-index", "publications of"]):
            if "find" in query_lower or "who" in query_lower:
                return ResearchIntent.AUTHOR_FIND
            if "h-index" in query_lower or "profile" in query_lower or "metrics" in query_lower:
                return ResearchIntent.AUTHOR_PROFILE
            return ResearchIntent.AUTHOR_WORKS
        
        # Citations
        if any(kw in query_lower for kw in ["citation", "cited by", "references", "citing"]):
            return ResearchIntent.CITATION_ANALYSIS
        
        # Papers
        if any(kw in query_lower for kw in ["latest", "recent", "new papers", "preprint"]):
            return ResearchIntent.PAPER_LATEST
        if any(kw in query_lower for kw in ["influential", "important", "seminal", "most cited"]):
            return ResearchIntent.PAPER_INFLUENTIAL
        if any(kw in query_lower for kw in ["literature review", "comprehensive", "survey"]):
            return ResearchIntent.LITERATURE_REVIEW
        
        # Default to paper search
        return ResearchIntent.PAPER_SEARCH


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_policy_instance: Optional[ResearchToolPolicy] = None


def get_research_policy() -> ResearchToolPolicy:
    """Get the singleton policy instance."""
    global _policy_instance
    if _policy_instance is None:
        _policy_instance = ResearchToolPolicy()
    return _policy_instance


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_research_tool(intent: str, server: str, tool: str) -> None:
    """
    Validate a research tool call.
    
    Args:
        intent: String intent name (e.g., "paper_search")
        server: MCP server name (e.g., "arxiv")
        tool: Tool name (e.g., "search_papers")
    
    Raises:
        IntentNotAllowed: If intent is blocked
        ToolPolicyViolation: If tool not allowed for intent
        ValueError: If intent is unknown
    """
    try:
        research_intent = ResearchIntent(intent)
    except ValueError:
        raise ValueError(f"Unknown research intent: {intent}")
    
    policy = get_research_policy()
    policy.validate_tool_call(research_intent, server, tool)


def get_tools_for_query(user_query: str) -> PolicyDecision:
    """
    Get allowed tools for a user query.
    
    Suggests intent and returns allowed tools.
    """
    policy = get_research_policy()
    suggested_intent = policy.suggest_intent(user_query)
    
    if suggested_intent is None:
        suggested_intent = ResearchIntent.PAPER_SEARCH
    
    return policy.get_tools_for_intent(suggested_intent)
