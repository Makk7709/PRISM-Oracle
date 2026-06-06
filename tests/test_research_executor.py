"""
Tests for Research Executor.

Verifies:
- Intent detection → correct tools called
- Policy enforcement (disabled servers blocked)
- Fallback mechanism works
- Logging produces valid JSONL
- Integration with ReasoningEngine
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from python.helpers.research_executor import (
    ResearchExecutor,
    ResearchExecutorConfig,
    ResearchResult,
    ToolCallResult,
    MockMCPToolCaller,
    ResearchToolExecutor,
    create_research_executor,
    quick_research,
)
from python.helpers.research_tool_policy import (
    ResearchIntent,
    ToolPolicyViolation,
    ACTIVE_SERVERS,
    DISABLED_SERVERS,
)
from python.helpers.reasoning_engine import (
    ReasoningContext,
    Subtask,
)


# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_caller():
    """Mock MCP tool caller."""
    return MockMCPToolCaller()


@pytest.fixture
def executor(mock_caller):
    """Research executor with mock caller."""
    config = ResearchExecutorConfig(
        log_file=None,  # Disable file logging for tests
    )
    return ResearchExecutor(mock_caller, config)


@pytest.fixture
def context():
    """Minimal reasoning context."""
    return ReasoningContext(
        session_id="test_research",
        user_query="Test query",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTENT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntentDetection:
    """Test that queries map to correct intents."""
    
    @pytest.mark.asyncio
    async def test_paper_search_uses_semanticscholar(self, executor, mock_caller):
        """Paper search should call semanticscholar first."""
        result = await executor.execute("Find papers on machine learning")
        
        calls = mock_caller.get_calls()
        assert len(calls) >= 1
        # First call should be semanticscholar (highest priority for paper_search)
        assert calls[0]["server"] == "semanticscholar"
    
    @pytest.mark.asyncio
    async def test_latest_papers_uses_arxiv_first(self, executor, mock_caller):
        """Latest papers should use arXiv first."""
        result = await executor.execute(
            "Latest research on transformers",
            intent=ResearchIntent.PAPER_LATEST,
        )
        
        calls = mock_caller.get_calls()
        assert len(calls) >= 1
        assert calls[0]["server"] == "arxiv"
    
    @pytest.mark.asyncio
    async def test_doi_lookup_uses_crossref(self, executor, mock_caller):
        """DOI lookup should use crossref."""
        result = await executor.execute(
            "Get DOI 10.1234/test",
            intent=ResearchIntent.DOI_LOOKUP,
        )
        
        calls = mock_caller.get_calls()
        assert len(calls) == 1
        assert calls[0]["server"] == "crossref"
    
    @pytest.mark.asyncio
    async def test_eu_legislation_uses_eurlex(self, executor, mock_caller):
        """EU legislation should use eurlex only."""
        result = await executor.execute(
            "Find GDPR regulation",
            intent=ResearchIntent.EU_LEGISLATION,
        )
        
        calls = mock_caller.get_calls()
        # All calls should be to eurlex
        for call in calls:
            assert call["server"] == "eurlex"
    
    @pytest.mark.asyncio
    async def test_auto_detects_gdpr_as_eu_legislation(self, executor, mock_caller):
        """GDPR mention should auto-detect EU_LEGISLATION intent."""
        result = await executor.execute("What does GDPR say about consent?")
        
        assert result.intent == ResearchIntent.EU_LEGISLATION
        calls = mock_caller.get_calls()
        assert all(c["server"] == "eurlex" for c in calls)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: POLICY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyEnforcement:
    """Test that policy constraints are enforced."""
    
    @pytest.mark.asyncio
    async def test_patent_search_blocked(self, executor):
        """Patent search should be blocked."""
        result = await executor.execute(
            "Find patents on AI",
            intent=ResearchIntent.PATENT_SEARCH,
        )
        
        assert result.success is False
        assert "BLOCKED" in result.warnings[0]
        assert len(result.tools_called) == 0
    
    @pytest.mark.asyncio
    async def test_disabled_servers_never_called(self, executor, mock_caller):
        """Disabled servers should never be called."""
        # Run multiple queries
        await executor.execute("papers on ML")
        await executor.execute("author John Smith")
        await executor.execute("GDPR regulation")
        
        calls = mock_caller.get_calls()
        for call in calls:
            assert call["server"] not in DISABLED_SERVERS
            assert call["server"] in ACTIVE_SERVERS
    
    @pytest.mark.asyncio
    async def test_eurlex_not_used_for_paper_search(self, executor, mock_caller):
        """EUR-Lex should not be used for paper search."""
        result = await executor.execute(
            "papers on deep learning",
            intent=ResearchIntent.PAPER_SEARCH,
        )
        
        calls = mock_caller.get_calls()
        for call in calls:
            assert call["server"] != "eurlex"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FALLBACK MECHANISM
# ═══════════════════════════════════════════════════════════════════════════════

class TestFallbackMechanism:
    """Test fallback behavior."""
    
    @pytest.mark.asyncio
    async def test_fallback_used_on_empty_result(self):
        """Fallback should be used if primary returns empty."""
        # Create mock that returns empty for first tool
        mock = MockMCPToolCaller(responses={
            "semanticscholar.search_semantic_scholar": {"data": []},  # Empty
            "openalex.search_works": {"results": [{"title": "Fallback Paper"}]},
        })
        
        config = ResearchExecutorConfig(log_file=None, stop_on_success=True)
        executor = ResearchExecutor(mock, config)
        
        result = await executor.execute(
            "find papers",
            intent=ResearchIntent.PAPER_SEARCH,
        )
        
        # Should have tried multiple tools
        assert len(result.tools_called) >= 2
    
    @pytest.mark.asyncio
    async def test_stops_on_first_success(self, executor, mock_caller):
        """Should stop after first successful result if stop_on_success=True."""
        result = await executor.execute("find papers")
        
        calls = mock_caller.get_calls()
        # With stop_on_success, should stop after first valid result
        assert len(calls) == 1
        assert result.success is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RESULT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestResultValidation:
    """Test result structure and validation."""
    
    @pytest.mark.asyncio
    async def test_result_has_correlation_id(self, executor):
        """Result should have correlation_id."""
        result = await executor.execute("test query")
        
        assert result.correlation_id is not None
        assert result.correlation_id.startswith("re_")
    
    @pytest.mark.asyncio
    async def test_result_has_intent(self, executor):
        """Result should have detected intent."""
        result = await executor.execute("test query")
        
        assert result.intent is not None
        assert isinstance(result.intent, ResearchIntent)
    
    @pytest.mark.asyncio
    async def test_result_has_duration(self, executor):
        """Result should have duration (can be 0 for fast mocks)."""
        result = await executor.execute("test query")
        
        # Duration can be 0 for instant mocks, just verify it's non-negative
        assert result.total_duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_tool_call_result_validation(self, executor):
        """ToolCallResult.is_valid() should work correctly."""
        result = await executor.execute("test query")
        
        for tool_result in result.tools_called:
            if tool_result.success and tool_result.result:
                assert tool_result.is_valid() is True
    
    @pytest.mark.asyncio
    async def test_empty_result_is_invalid(self):
        """Empty results should be marked invalid."""
        result = ToolCallResult(
            server="test",
            tool="test",
            success=True,
            result=[],  # Empty list
            duration_ms=100,
        )
        assert result.is_valid() is False
        
        result2 = ToolCallResult(
            server="test",
            tool="test",
            success=True,
            result="",  # Empty string
            duration_ms=100,
        )
        assert result2.is_valid() is False


# TEST: LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogging:
    """Test JSONL logging."""
    
    @pytest.mark.asyncio
    async def test_log_file_created(self, mock_caller, tmp_path):
        """Log file should be created."""
        log_file = tmp_path / "test_logs.jsonl"
        config = ResearchExecutorConfig(log_file=str(log_file))
        executor = ResearchExecutor(mock_caller, config)
        
        await executor.execute("test query")
        
        assert log_file.exists()
    
    @pytest.mark.asyncio
    async def test_log_entries_are_valid_json(self, mock_caller, tmp_path):
        """Log entries should be valid JSON."""
        log_file = tmp_path / "test_logs.jsonl"
        config = ResearchExecutorConfig(log_file=str(log_file))
        executor = ResearchExecutor(mock_caller, config)
        
        await executor.execute("test query")
        
        with open(log_file) as f:
            for line in f:
                entry = json.loads(line)  # Should not raise
                assert "ts" in entry
                assert "correlation_id" in entry
                assert "server" in entry
                assert "tool" in entry
                assert "duration_ms" in entry
                assert "ok" in entry
    
    @pytest.mark.asyncio
    async def test_log_does_not_contain_args(self, mock_caller, tmp_path):
        """Log should not contain raw args (PII protection)."""
        log_file = tmp_path / "test_logs.jsonl"
        config = ResearchExecutorConfig(log_file=str(log_file), log_args=False)
        executor = ResearchExecutor(mock_caller, config)
        
        await executor.execute("sensitive query with email@example.com")
        
        with open(log_file) as f:
            content = f.read()
            assert "email@example.com" not in content
            assert "sensitive query" not in content


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTEGRATION WITH REASONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestReasoningEngineIntegration:
    """Test integration with ReasoningEngine."""
    
    @pytest.mark.asyncio
    async def test_research_tool_executor_works(self, mock_caller, context):
        """ResearchToolExecutor should work with Subtask."""
        executor = ResearchToolExecutor(mock_caller)
        
        subtask = Subtask(
            id="test_1",
            description="Find papers on neural networks",
            order=0,
        )
        
        result_text, confidence = await executor.execute(subtask, context)
        
        assert result_text is not None
        assert len(result_text) > 0
        assert 0 <= confidence <= 1
    
    @pytest.mark.asyncio
    async def test_executor_returns_formatted_text(self, mock_caller, context):
        """Executor should return human-readable text."""
        executor = ResearchToolExecutor(mock_caller)
        
        subtask = Subtask(
            id="test_2",
            description="Search for ML papers",
            order=0,
        )
        
        result_text, _ = await executor.execute(subtask, context)
        
        # Should mention "Found X papers" or similar
        assert "Found" in result_text or "papers" in result_text.lower()
    
    @pytest.mark.asyncio
    async def test_executor_handles_failure(self, context):
        """Executor should handle failures gracefully."""
        # Create mock that always fails
        failing_mock = MockMCPToolCaller(responses={
            "semanticscholar.search_semantic_scholar": None,
        })
        
        # Override call to raise exception
        async def failing_call(*args, **kwargs):
            raise Exception("Simulated failure")
        
        failing_mock.call = failing_call
        
        executor = ResearchToolExecutor(failing_mock)
        
        subtask = Subtask(
            id="test_3",
            description="Search papers",
            order=0,
        )
        
        result_text, confidence = await executor.execute(subtask, context)
        
        # Should return low confidence on failure
        assert confidence < 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_create_research_executor_with_mock(self):
        """create_research_executor with mock should work."""
        executor = create_research_executor(use_mock=True)
        assert executor is not None
    
    def test_create_research_executor_requires_caller(self):
        """create_research_executor without caller should fail."""
        with pytest.raises(ValueError):
            create_research_executor(use_mock=False)
    
    @pytest.mark.asyncio
    async def test_quick_research_works(self):
        """quick_research should return result."""
        result = await quick_research("test query", use_mock=True)
        
        assert result is not None
        assert isinstance(result, ResearchResult)
        assert result.intent is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: MOCK CALLER
# ═══════════════════════════════════════════════════════════════════════════════

class TestMockCaller:
    """Test MockMCPToolCaller."""
    
    @pytest.mark.asyncio
    async def test_mock_returns_default_responses(self):
        """Mock should return sensible defaults."""
        mock = MockMCPToolCaller()
        
        arxiv_result = await mock.call("arxiv", "search_papers", {"query": "test"})
        assert "papers" in arxiv_result
        
        ss_result = await mock.call("semanticscholar", "search_semantic_scholar", {"query": "test"})
        assert "data" in ss_result
        
        eurlex_result = await mock.call("eurlex", "search_eu_legislation", {"query": "test"})
        assert "documents" in eurlex_result
    
    @pytest.mark.asyncio
    async def test_mock_records_calls(self):
        """Mock should record all calls."""
        mock = MockMCPToolCaller()
        
        await mock.call("arxiv", "search_papers", {"query": "test1"})
        await mock.call("semanticscholar", "search_semantic_scholar", {"query": "test2"})
        
        calls = mock.get_calls()
        assert len(calls) == 2
        assert calls[0]["server"] == "arxiv"
        assert calls[1]["server"] == "semanticscholar"
    
    @pytest.mark.asyncio
    async def test_mock_custom_responses(self):
        """Mock should use custom responses."""
        custom_response = {"custom": "data"}
        mock = MockMCPToolCaller(responses={
            "arxiv.search_papers": custom_response,
        })
        
        result = await mock.call("arxiv", "search_papers", {"query": "test"})
        assert result == custom_response
    
    def test_mock_reset(self):
        """Mock reset should clear calls."""
        mock = MockMCPToolCaller()
        mock._calls.append({"test": "data"})
        
        mock.reset()
        
        assert len(mock.get_calls()) == 0


# TEST: STATS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStats:
    """Test executor stats."""
    
    @pytest.mark.asyncio
    async def test_stats_track_calls(self, executor):
        """Stats should track calls."""
        await executor.execute("query 1")
        await executor.execute("query 2")
        
        stats = executor.get_stats()
        assert stats["total_calls"] >= 2
    
    @pytest.mark.asyncio
    async def test_stats_track_success_rate(self, executor):
        """Stats should track success rate."""
        await executor.execute("query 1")
        
        stats = executor.get_stats()
        assert "success_rate" in stats
        assert 0 <= stats["success_rate"] <= 1
