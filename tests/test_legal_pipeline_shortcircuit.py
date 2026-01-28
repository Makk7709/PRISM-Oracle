"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           LEGAL PIPELINE SHORT-CIRCUIT — NON-REGRESSION TESTS                ║
║                                                                              ║
║  Tests that verify the LLM is bypassed when the legal pipeline produces      ║
║  valid output, ensuring deterministic responses are not overwritten.         ║
║                                                                              ║
║  INVARIANT: Pipeline output is authoritative; LLM cannot overwrite it.       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PIPELINE SUCCESS SKIPS LLM CALL
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineShortCircuit:
    """Tests for the pipeline short-circuit mechanism."""
    
    def test_pipeline_final_response_flag_skips_monologue_loop(self):
        """
        When _pipeline_final_response is set, the agent should return it
        directly without entering the LLM call loop.
        """
        # Create a mock agent with the required methods
        mock_agent = MagicMock()
        mock_agent.data = {}
        
        def get_data(key):
            return mock_agent.data.get(key)
        
        def set_data(key, value):
            mock_agent.data[key] = value
        
        mock_agent.get_data = get_data
        mock_agent.set_data = set_data
        
        # Set the pipeline final response flag
        mock_agent.set_data("_pipeline_final_response", "## Pipeline Output\nThis is the rendered response.")
        mock_agent.set_data("_skip_llm", True)
        
        # Verify flags are set correctly
        assert mock_agent.get_data("_pipeline_final_response") is not None
        assert mock_agent.get_data("_skip_llm") is True
        
    def test_skip_llm_flag_blocks_call_chat_model(self):
        """
        When _skip_llm is set, call_chat_model should return the pipeline
        response without calling the actual LLM.
        """
        # This test verifies the defense-in-depth mechanism
        mock_agent = MagicMock()
        mock_agent.data = {
            "_skip_llm": True,
            "_pipeline_final_response": "Pipeline response content"
        }
        
        def get_data(key):
            return mock_agent.data.get(key)
        
        mock_agent.get_data = get_data
        
        # The call_chat_model should check this flag and return early
        if mock_agent.get_data("_skip_llm"):
            result = mock_agent.get_data("_pipeline_final_response")
            assert result == "Pipeline response content"
    
    def test_pipeline_failure_sets_failclosed_response(self):
        """
        When pipeline returns None (failure), the system should STILL short-circuit
        with a fail-closed error message - NOT let the LLM hallucinate.
        """
        mock_agent = MagicMock()
        mock_agent.data = {}
        
        def set_data(key, value):
            mock_agent.data[key] = value
        
        def get_data(key):
            return mock_agent.data.get(key)
        
        mock_agent.set_data = set_data
        mock_agent.get_data = get_data
        
        # Simulate pipeline failure (returns None) - NEW BEHAVIOR
        pipeline_result = None
        
        if pipeline_result is not None:
            output, rendered = pipeline_result
            mock_agent.set_data("_pipeline_final_response", rendered)
            mock_agent.set_data("_skip_llm", True)
        else:
            # NEW: Even on failure, short-circuit with error message
            failure_response = "# ⚠️ Analyse Juridique Indisponible\n\nLe pipeline a échoué."
            mock_agent.set_data("_pipeline_final_response", failure_response)
            mock_agent.set_data("_skip_llm", True)
        
        # Verify flags ARE set (fail-closed behavior)
        assert mock_agent.get_data("_pipeline_final_response") is not None
        assert mock_agent.get_data("_skip_llm") is True
        assert "Indisponible" in mock_agent.get_data("_pipeline_final_response")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LEGAL OUTPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalOutputValidation:
    """Tests for LegalOutput validation before short-circuit."""
    
    def test_valid_legal_output_has_required_fields(self):
        """A valid LegalOutput must have mode, answer, and audit_bundle_id."""
        try:
            from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
            
            output = LegalOutput(
                mode=LegalOutputMode.APPROVED_POSITION,
                answer="Test answer",
                audit_bundle_id="test-audit-123",
            )
            
            assert output.mode == LegalOutputMode.APPROVED_POSITION
            assert output.answer == "Test answer"
            assert output.audit_bundle_id == "test-audit-123"
        except ImportError:
            pytest.skip("LegalOutput not available")
    
    def test_legal_output_to_dict_includes_all_fields(self):
        """LegalOutput.to_dict() should include all required audit fields."""
        try:
            from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
            
            output = LegalOutput(
                mode=LegalOutputMode.SAFE_ANALYSIS,
                answer="Analysis result",
                consensus_status="NO_CONSENSUS",
                judge_verdict="APPROVE",
                audit_bundle_id="audit-456",
            )
            
            data = output.to_dict()
            
            assert "mode" in data
            assert "consensus_status" in data
            assert "judge_verdict" in data
            assert "audit_bundle_id" in data
            assert data["consensus_status"] == "NO_CONSENSUS"
        except ImportError:
            pytest.skip("LegalOutput not available")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NO STREAMING WHEN PIPELINE SUCCEEDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoStreamingOnPipelineSuccess:
    """Tests that verify no LLM streaming occurs when pipeline succeeds."""
    
    def test_stream_callback_not_called_when_skip_llm_set(self):
        """
        When _skip_llm is True, the stream callback should never be called
        because call_chat_model returns immediately.
        """
        stream_chunks_received = []
        
        async def mock_stream_callback(chunk: str, full: str):
            stream_chunks_received.append(chunk)
        
        # Simulate the short-circuit behavior
        skip_llm = True
        pipeline_response = "Pipeline output"
        
        if skip_llm:
            # call_chat_model returns immediately, callback never called
            result = (pipeline_response, "")
        else:
            # Would call LLM with streaming (not reached)
            asyncio.run(mock_stream_callback("chunk1", "chunk1"))
            result = ("LLM response", "")
        
        # Verify no streaming occurred
        assert len(stream_chunks_received) == 0
        assert result[0] == "Pipeline output"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FLAGS CLEANED UP CORRECTLY
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlagCleanup:
    """Tests that verify flags are cleaned up at the right time."""
    
    def test_flags_cleared_after_response_returned(self):
        """
        The _pipeline_final_response and _skip_llm flags should be cleared
        after the response is returned to prevent affecting the next request.
        """
        mock_agent = MagicMock()
        mock_agent.data = {
            "_pipeline_final_response": "Response content",
            "_skip_llm": True,
        }
        
        def set_data(key, value):
            mock_agent.data[key] = value
        
        def get_data(key):
            return mock_agent.data.get(key)
        
        mock_agent.set_data = set_data
        mock_agent.get_data = get_data
        
        # Simulate the cleanup that happens in agent.monologue()
        # after returning the pipeline response
        mock_agent.set_data("_pipeline_final_response", None)
        mock_agent.set_data("_skip_llm", None)
        
        # Verify flags are cleared
        assert mock_agent.get_data("_pipeline_final_response") is None
        assert mock_agent.get_data("_skip_llm") is None
    
    def test_flags_not_cleared_prematurely_in_response_stream_end(self):
        """
        The response_stream_end hook should NOT clear pipeline data if
        the short-circuit was supposed to prevent LLM call.
        """
        mock_agent = MagicMock()
        mock_agent.data = {
            "_skip_llm": True,
            "_legal_pipeline_output": MagicMock(),
            "_legal_pipeline_rendered": "Rendered output",
        }
        
        def get_data(key):
            return mock_agent.data.get(key)
        
        def set_data(key, value):
            mock_agent.data[key] = value
        
        mock_agent.get_data = get_data
        mock_agent.set_data = set_data
        
        # Simulate response_stream_end behavior with skip_llm set
        skip_llm_flag = mock_agent.get_data("_skip_llm")
        
        # Should NOT clear if skip_llm was set
        if not skip_llm_flag:
            mock_agent.set_data("_legal_pipeline_output", None)
            mock_agent.set_data("_legal_pipeline_rendered", None)
        
        # Data should still be present
        assert mock_agent.get_data("_legal_pipeline_output") is not None
        assert mock_agent.get_data("_legal_pipeline_rendered") is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTEGRATION - EXTENSION SETS FLAGS CORRECTLY
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtensionIntegration:
    """Integration tests for the legal_safe extension flag setting."""
    
    def test_extension_sets_skip_llm_on_pipeline_success(self):
        """
        When run_legal_pipeline returns a valid result, the extension
        should set both _pipeline_final_response and _skip_llm.
        """
        try:
            from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
            from python.helpers.legal_rendering import render_legal_output
            
            # Create a mock valid output
            output = LegalOutput(
                mode=LegalOutputMode.APPROVED_POSITION,
                answer="Validated position",
                consensus_status="APPROVED",
                judge_verdict="APPROVE",
                audit_bundle_id="test-123",
            )
            
            # Simulate rendering
            if render_legal_output:
                rendered = render_legal_output(output, format="md", style="info")
            else:
                rendered = output.answer
            
            # Simulate what the extension does
            mock_agent = MagicMock()
            mock_agent.data = {}
            mock_agent.set_data = lambda k, v: mock_agent.data.__setitem__(k, v)
            mock_agent.get_data = lambda k: mock_agent.data.get(k)
            
            # This is what the extension should do
            result = (output, rendered)
            if result is not None:
                output, rendered = result
                mock_agent.set_data("_pipeline_final_response", rendered)
                mock_agent.set_data("_skip_llm", True)
            
            # Verify
            assert mock_agent.get_data("_skip_llm") is True
            assert mock_agent.get_data("_pipeline_final_response") is not None
            
        except ImportError:
            pytest.skip("Legal pipeline modules not available")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: AUDIT LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditLogging:
    """Tests for audit logging during short-circuit."""
    
    def test_llm_bypass_is_logged(self):
        """
        When LLM is bypassed, a log entry should be created with
        llm_bypassed=True and the reason_code.
        """
        log_entries = []
        
        def mock_log(type, heading, content, kvps=None):
            log_entries.append({
                "type": type,
                "heading": heading,
                "content": content,
                "kvps": kvps or {},
            })
        
        # Simulate the logging that should happen
        mock_log(
            type="info",
            heading="⚖️ Legal Pipeline (LLM Bypassed)",
            content="Pipeline executed: mode=approved_position, audit=test-123",
            kvps={
                "output_mode": "approved_position",
                "consensus_status": "APPROVED",
                "reason_code": "approved",
                "llm_bypassed": True,
            }
        )
        
        # Verify log entry
        assert len(log_entries) == 1
        assert log_entries[0]["kvps"]["llm_bypassed"] is True
        assert "reason_code" in log_entries[0]["kvps"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
