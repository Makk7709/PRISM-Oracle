"""
Tests for Research Tool Policy.

Verifies that:
- Tools are correctly restricted by intent
- Blocked intents raise exceptions
- Disabled servers are blocked
- Fallbacks are correctly identified
"""

import pytest
from python.helpers.research_tool_policy import (
    ResearchToolPolicy,
    ResearchIntent,
    ToolPolicyViolation,
    IntentNotAllowed,
    get_research_policy,
    validate_research_tool,
    get_tools_for_query,
    ACTIVE_SERVERS,
    DISABLED_SERVERS,
)


class TestIntentPolicies:
    """Test intent → tool mappings."""
    
    def test_paper_search_allows_correct_tools(self):
        """Paper search should allow arxiv, semanticscholar, openalex."""
        policy = ResearchToolPolicy()
        decision = policy.get_tools_for_intent(ResearchIntent.PAPER_SEARCH)
        
        assert decision.allowed is True
        tool_names = [t.full_name for t in decision.tools_to_use]
        
        # Should include main search tools
        assert any("semanticscholar" in t for t in tool_names)
    
    def test_paper_latest_prioritizes_arxiv(self):
        """Latest papers should use arXiv first."""
        policy = ResearchToolPolicy()
        decision = policy.get_tools_for_intent(ResearchIntent.PAPER_LATEST)
        
        assert decision.allowed is True
        # First tool should be arxiv
        assert decision.tools_to_use[0].server == "arxiv"
    
    def test_doi_lookup_uses_crossref(self):
        """DOI lookup should use crossref only."""
        policy = ResearchToolPolicy()
        decision = policy.get_tools_for_intent(ResearchIntent.DOI_LOOKUP)
        
        assert decision.allowed is True
        assert len(decision.tools_to_use) == 1
        assert decision.tools_to_use[0].server == "crossref"
    
    def test_eu_legislation_uses_eurlex(self):
        """EU legislation should use eurlex only."""
        policy = ResearchToolPolicy()
        decision = policy.get_tools_for_intent(ResearchIntent.EU_LEGISLATION)
        
        assert decision.allowed is True
        # All tools should be eurlex
        for tool in decision.tools_to_use:
            assert tool.server == "eurlex"


class TestBlockedIntents:
    """Test that blocked intents are properly rejected."""
    
    def test_patent_search_is_blocked(self):
        """Patent search should be blocked."""
        policy = ResearchToolPolicy()
        decision = policy.get_tools_for_intent(ResearchIntent.PATENT_SEARCH)
        
        assert decision.allowed is False
        assert len(decision.tools_to_use) == 0
        assert "BLOCKED" in decision.reason
    
    def test_patent_search_raises_on_validate(self):
        """Validating patent tool should raise IntentNotAllowed."""
        policy = ResearchToolPolicy()
        
        with pytest.raises(IntentNotAllowed) as exc_info:
            policy.validate_tool_call(
                ResearchIntent.PATENT_SEARCH, 
                "espacenet", 
                "search_patents"
            )
        
        assert "BLOCKED" in str(exc_info.value)


class TestDisabledServers:
    """Test that disabled servers are blocked."""
    
    def test_disabled_servers_list(self):
        """Verify disabled servers are configured."""
        assert "lens" in DISABLED_SERVERS
        assert "espacenet" in DISABLED_SERVERS
    
    def test_lens_tool_blocked(self):
        """Any lens tool should be blocked."""
        policy = ResearchToolPolicy()
        
        with pytest.raises(ToolPolicyViolation) as exc_info:
            policy.validate_tool_call(
                ResearchIntent.PAPER_SEARCH,
                "lens",
                "search_patents"
            )
        
        assert "DISABLED" in str(exc_info.value)
    
    def test_espacenet_tool_blocked(self):
        """Any espacenet tool should be blocked."""
        policy = ResearchToolPolicy()
        
        with pytest.raises(ToolPolicyViolation) as exc_info:
            policy.validate_tool_call(
                ResearchIntent.PAPER_SEARCH,
                "espacenet",
                "search_patents_espacenet"
            )
        
        assert "DISABLED" in str(exc_info.value)


class TestToolValidation:
    """Test tool validation."""
    
    def test_allowed_tool_passes(self):
        """Allowed tool should pass validation."""
        policy = ResearchToolPolicy()
        
        # Should not raise
        policy.validate_tool_call(
            ResearchIntent.PAPER_SEARCH,
            "arxiv",
            "search_papers"
        )
    
    def test_wrong_tool_for_intent_fails(self):
        """Using wrong tool for intent should fail."""
        policy = ResearchToolPolicy()
        
        with pytest.raises(ToolPolicyViolation) as exc_info:
            policy.validate_tool_call(
                ResearchIntent.DOI_LOOKUP,  # DOI lookup
                "arxiv",                     # But using arxiv
                "search_papers"
            )
        
        assert "NOT ALLOWED" in str(exc_info.value)
    
    def test_eurlex_not_allowed_for_paper_search(self):
        """EUR-Lex should not be allowed for paper search."""
        policy = ResearchToolPolicy()
        
        assert policy.is_tool_allowed(
            ResearchIntent.PAPER_SEARCH,
            "eurlex",
            "search_eu_legislation"
        ) is False


class TestIntentSuggestion:
    """Test intent suggestion from user queries."""
    
    def test_suggests_eu_legislation_for_gdpr(self):
        """GDPR query should suggest EU legislation."""
        policy = ResearchToolPolicy()
        intent = policy.suggest_intent("What does GDPR say about data retention?")
        
        assert intent == ResearchIntent.EU_LEGISLATION
    
    def test_suggests_case_law_for_cjeu(self):
        """CJEU query should suggest case law."""
        policy = ResearchToolPolicy()
        intent = policy.suggest_intent("Find CJEU judgment on privacy")
        
        assert intent == ResearchIntent.EU_CASE_LAW
    
    def test_suggests_patent_for_patent_query(self):
        """Patent query should suggest patent (even though blocked)."""
        policy = ResearchToolPolicy()
        intent = policy.suggest_intent("Find patents on machine learning")
        
        assert intent == ResearchIntent.PATENT_SEARCH
        # Verify it will be blocked
        decision = policy.get_tools_for_intent(intent)
        assert decision.allowed is False
    
    def test_suggests_doi_lookup(self):
        """DOI mention should suggest DOI lookup."""
        policy = ResearchToolPolicy()
        intent = policy.suggest_intent("Get paper with DOI 10.1234/example")
        
        assert intent == ResearchIntent.DOI_LOOKUP
    
    def test_suggests_author_find(self):
        """Author query should suggest author find."""
        policy = ResearchToolPolicy()
        intent = policy.suggest_intent("Find researcher John Smith at MIT")
        
        assert intent == ResearchIntent.AUTHOR_FIND
    
    def test_suggests_paper_latest_for_recent(self):
        """Recent papers query should suggest paper_latest."""
        policy = ResearchToolPolicy()
        intent = policy.suggest_intent("Latest research on transformers")
        
        assert intent == ResearchIntent.PAPER_LATEST
    
    def test_default_to_paper_search(self):
        """Generic query should default to paper search."""
        policy = ResearchToolPolicy()
        intent = policy.suggest_intent("machine learning optimization")
        
        assert intent == ResearchIntent.PAPER_SEARCH


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_validate_research_tool_valid(self):
        """validate_research_tool should pass for valid combination."""
        # Should not raise
        validate_research_tool("paper_search", "arxiv", "search_papers")
    
    def test_validate_research_tool_invalid_intent(self):
        """validate_research_tool should fail for unknown intent."""
        with pytest.raises(ValueError) as exc_info:
            validate_research_tool("unknown_intent", "arxiv", "search_papers")
        
        assert "Unknown research intent" in str(exc_info.value)
    
    def test_get_tools_for_query(self):
        """get_tools_for_query should return decision."""
        decision = get_tools_for_query("Find latest papers on AI")
        
        assert decision.allowed is True
        assert len(decision.tools_to_use) > 0


class TestFallbackTools:
    """Test fallback mechanism."""
    
    def test_paper_search_has_fallback(self):
        """Paper search should have fallback tools."""
        policy = ResearchToolPolicy()
        fallbacks = policy.get_fallback_for_intent(ResearchIntent.PAPER_SEARCH)
        
        assert len(fallbacks) > 0
        # Crossref should be fallback
        assert any(t.server == "crossref" for t in fallbacks)
    
    def test_fallback_tools_are_active(self):
        """Fallback tools should only be from active servers."""
        policy = ResearchToolPolicy()
        
        for intent in ResearchIntent:
            if intent == ResearchIntent.PATENT_SEARCH:
                continue  # Skip blocked
            
            fallbacks = policy.get_fallback_for_intent(intent)
            for tool in fallbacks:
                assert tool.server in ACTIVE_SERVERS


class TestExecutionLogging:
    """Test execution logging."""
    
    def test_log_successful_execution(self):
        """Successful execution should be logged."""
        policy = ResearchToolPolicy()
        policy.log_execution(
            ResearchIntent.PAPER_SEARCH,
            "arxiv.search_papers",
            success=True,
            duration_ms=150
        )
        
        assert len(policy.execution_log) == 1
        assert policy.execution_log[0].success is True
    
    def test_log_failed_execution(self):
        """Failed execution should be logged with error."""
        policy = ResearchToolPolicy()
        policy.log_execution(
            ResearchIntent.PAPER_SEARCH,
            "arxiv.search_papers",
            success=False,
            error="Timeout"
        )
        
        assert len(policy.execution_log) == 1
        assert policy.execution_log[0].success is False
        assert policy.execution_log[0].error == "Timeout"


class TestSingletonPolicy:
    """Test singleton pattern."""
    
    def test_get_research_policy_returns_same_instance(self):
        """get_research_policy should return same instance."""
        policy1 = get_research_policy()
        policy2 = get_research_policy()
        
        assert policy1 is policy2
