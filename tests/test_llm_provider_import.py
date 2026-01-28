"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LLM PROVIDER IMPORT STABILITY TESTS                       ║
║                                                                              ║
║  Tests for:                                                                  ║
║  1. Import stability regardless of working directory                         ║
║  2. Fail-fast behavior in production when provider missing                   ║
║  3. Simulation mode behavior in dev/test                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import importlib
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest


class TestLLMProviderImportStability:
    """Test that llm_provider imports correctly regardless of cwd."""
    
    def test_llm_provider_importable_from_workspace_root(self):
        """Import should work from normal workspace root."""
        # This test runs from project root (normal case)
        from python.helpers import llm_provider
        
        assert hasattr(llm_provider, 'get_provider')
        assert hasattr(llm_provider, 'validate_boot')
        assert hasattr(llm_provider, 'is_provider_available')
    
    def test_llm_provider_has_required_functions(self):
        """Verify all required API functions exist."""
        from python.helpers import llm_provider
        
        # Required public API
        assert callable(llm_provider.get_provider)
        assert callable(llm_provider.validate_boot)
        assert callable(llm_provider.is_provider_available)
        assert callable(llm_provider.is_production)
        assert callable(llm_provider.is_simulation_enabled)
    
    def test_provider_wrapper_has_generate_method(self):
        """ProviderWrapper must have async generate() method."""
        from python.helpers.llm_provider import ProviderWrapper
        
        assert hasattr(ProviderWrapper, 'generate')
        # Check it's async
        import inspect
        assert inspect.iscoroutinefunction(ProviderWrapper.generate)


class TestFailFastBehavior:
    """Test fail-fast behavior when provider is unavailable."""
    
    def test_validate_boot_returns_dict_when_provider_available(self):
        """validate_boot() should return status dict when models available."""
        # Don't trigger fail-fast during test
        with mock.patch.dict(os.environ, {"EVIDENCE_ENV": "development"}):
            from python.helpers import llm_provider
            importlib.reload(llm_provider)
            
            if llm_provider.is_provider_available():
                result = llm_provider.validate_boot()
                assert isinstance(result, dict)
                assert "status" in result
                assert "environment" in result
    
    def test_is_provider_available_returns_bool(self):
        """is_provider_available() should return boolean."""
        from python.helpers import llm_provider
        
        result = llm_provider.is_provider_available()
        assert isinstance(result, bool)
    
    def test_production_detection(self):
        """Test environment detection logic."""
        from python.helpers import llm_provider
        
        # Test production detection
        with mock.patch.dict(os.environ, {"EVIDENCE_ENV": "production"}):
            importlib.reload(llm_provider)
            assert llm_provider.is_production() is True
        
        # Test development detection
        with mock.patch.dict(os.environ, {"EVIDENCE_ENV": "development"}):
            importlib.reload(llm_provider)
            assert llm_provider.is_production() is False
    
    def test_simulation_detection(self):
        """Test simulation mode detection."""
        from python.helpers import llm_provider
        
        with mock.patch.dict(os.environ, {"CONSENSUS_SIMULATION": "true"}):
            importlib.reload(llm_provider)
            assert llm_provider.is_simulation_enabled() is True
        
        with mock.patch.dict(os.environ, {"CONSENSUS_SIMULATION": "false"}):
            importlib.reload(llm_provider)
            assert llm_provider.is_simulation_enabled() is False


class TestConsensusArbiterIntegration:
    """Test consensus_arbiter integration with llm_provider."""
    
    def test_consensus_arbiter_imports_llm_provider_at_module_level(self):
        """consensus_arbiter should import llm_provider at module level."""
        # Set development mode to avoid fail-fast
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "true"
        }):
            from python.helpers import consensus_arbiter
            importlib.reload(consensus_arbiter)
            
            # Should have the module-level flag
            assert hasattr(consensus_arbiter, '_LLM_PROVIDER_AVAILABLE')
            assert hasattr(consensus_arbiter, '_llm_provider')
    
    def test_arbiter_caller_uses_module_level_provider(self):
        """ArbiterCaller._call_llm should use module-level provider."""
        import inspect
        from python.helpers import consensus_arbiter
        
        # Get the source of _call_llm method
        source = inspect.getsource(consensus_arbiter.ArbiterCaller._call_llm)
        
        # Should NOT have dynamic import anymore
        assert "from python.helpers.llm_provider import" not in source
        
        # Should use module-level _llm_provider
        assert "_llm_provider" in source or "_LLM_PROVIDER_AVAILABLE" in source


class TestDevSimulationMode:
    """Test that dev mode with explicit simulation works."""
    
    def test_dev_with_simulation_allows_degraded_mode(self):
        """Dev + SIMULATION=true should allow mock voting."""
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "true"
        }):
            from python.helpers import llm_provider
            importlib.reload(llm_provider)
            
            # Should not raise even if models unavailable
            # because simulation is enabled
            assert llm_provider.is_simulation_enabled() is True
            assert llm_provider.is_production() is False


class TestModuleImportOrder:
    """Test that import order doesn't affect functionality."""
    
    def test_llm_provider_before_consensus_arbiter(self):
        """Importing llm_provider before consensus_arbiter should work."""
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "true"
        }):
            # Clear any cached imports
            for mod_name in list(sys.modules.keys()):
                if 'llm_provider' in mod_name or 'consensus_arbiter' in mod_name:
                    del sys.modules[mod_name]
            
            # Import in specific order
            from python.helpers import llm_provider
            from python.helpers import consensus_arbiter
            
            assert llm_provider is not None
            assert consensus_arbiter is not None
    
    def test_consensus_arbiter_standalone(self):
        """Importing consensus_arbiter alone should work."""
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development", 
            "CONSENSUS_SIMULATION": "true"
        }):
            from python.helpers import consensus_arbiter
            
            assert hasattr(consensus_arbiter, 'ConsensusOrchestrator')
            assert hasattr(consensus_arbiter, 'seek_consensus')


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS (more expensive, run in CI)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestBootValidation:
    """Integration tests for boot-time validation."""
    
    def test_full_boot_sequence_in_dev_mode(self):
        """Full boot sequence should work in dev mode."""
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "true"
        }):
            # Simulate full boot
            from python.helpers import llm_provider
            from python.helpers import consensus_arbiter
            
            # Both should be loaded without error
            assert llm_provider is not None
            assert consensus_arbiter is not None
            
            # Verify key attributes exist
            assert hasattr(llm_provider, 'get_provider')
            assert hasattr(consensus_arbiter, 'ConsensusOrchestrator')


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS: ACTUAL VOTING WITH STUB PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class TestActualVotingWithStubProvider:
    """Test that actual votes can be produced when provider is available."""
    
    @pytest.mark.asyncio
    async def test_call_llm_returns_response_with_stub_provider(self):
        """
        Monkeypatch models.get_chat_model() to return a stub.
        Run consensus_arbiter._call_llm() and assert it returns a real response.
        """
        from unittest.mock import AsyncMock, MagicMock
        
        # Create a stub chat model that returns a valid vote response
        stub_chat_model = MagicMock()
        stub_chat_model.unified_call = AsyncMock(return_value=(
            '{"approve": true, "reasoning": "Test approval", "confidence": 0.9}',
            ""  # reasoning (empty for this test)
        ))
        
        # Patch models.get_chat_model to return our stub
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "false"
        }):
            # Reload to pick up env changes
            import python.helpers.llm_provider as llm_provider_module
            
            # Patch the _models_module inside llm_provider
            original_models = llm_provider_module._models_module
            
            mock_models = MagicMock()
            mock_models.get_chat_model = MagicMock(return_value=stub_chat_model)
            llm_provider_module._models_module = mock_models
            
            try:
                # Get a provider wrapper
                wrapper = llm_provider_module.get_provider("openai", "gpt-4o")
                
                # Call generate
                response = await wrapper.generate(
                    prompt="Test prompt",
                    temperature=0.0,
                    max_tokens=500
                )
                
                # Assert we got a real response
                assert response is not None
                assert isinstance(response, str)
                assert "approve" in response or len(response) > 0
                
                # Verify the underlying model was called correctly
                stub_chat_model.unified_call.assert_called_once()
                call_kwargs = stub_chat_model.unified_call.call_args
                assert call_kwargs.kwargs["user_message"] == "Test prompt"
                assert call_kwargs.kwargs["temperature"] == 0.0
                assert call_kwargs.kwargs["max_tokens"] == 500
                
            finally:
                # Restore original models module
                llm_provider_module._models_module = original_models
    
    @pytest.mark.asyncio
    async def test_arbiter_caller_produces_real_vote_with_stub(self):
        """
        Test that ArbiterCaller._call_llm produces actual response (not UNAVAILABLE).
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        from python.helpers.consensus_arbiter import ArbiterCaller, ArbiterConfig, ConsensusConfig
        
        # Create stub that returns valid JSON vote
        stub_response = '{"approve": true, "reasoning": "Approved after review", "confidence": 0.85}'
        
        stub_chat_model = MagicMock()
        stub_chat_model.unified_call = AsyncMock(return_value=(stub_response, ""))
        
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "false"
        }):
            import python.helpers.llm_provider as llm_provider_module
            
            # Patch models module
            mock_models = MagicMock()
            mock_models.get_chat_model = MagicMock(return_value=stub_chat_model)
            
            original_models = llm_provider_module._models_module
            llm_provider_module._models_module = mock_models
            
            try:
                # Create caller with simulation disabled
                config = ConsensusConfig(simulation_enabled=False)
                caller = ArbiterCaller(config)
                
                arbiter = ArbiterConfig(
                    provider="openai",
                    model="gpt-4o",
                    timeout_ms=5000,
                    temperature=0.0,
                    max_tokens=500
                )
                
                # Call _call_llm directly
                response = await caller._call_llm(
                    arbiter=arbiter,
                    prompt="Should I approve this action?",
                    timeout_ms=5000
                )
                
                # Assert we got actual response, not an error
                assert response is not None
                assert isinstance(response, str)
                assert "approve" in response.lower()
                
            finally:
                llm_provider_module._models_module = original_models


class TestProductionSimulationGuard:
    """Test that production cannot start with CONSENSUS_SIMULATION=true."""
    
    def test_production_with_simulation_raises_simulation_error(self):
        """
        In production, CONSENSUS_SIMULATION=true must raise SimulationError.
        This guard is in consensus_arbiter.load_consensus_config().
        """
        from python.helpers.consensus_arbiter import SimulationError, load_consensus_config
        
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "production",
            "CONSENSUS_SIMULATION": "true"
        }):
            with pytest.raises(SimulationError) as exc_info:
                load_consensus_config()
            
            # Verify error message content
            assert "FORBIDDEN in production" in str(exc_info.value)
            assert "CONSENSUS_SIMULATION=true" in str(exc_info.value)
    
    def test_production_without_simulation_does_not_raise(self):
        """
        In production with CONSENSUS_SIMULATION=false, config should load.
        """
        from python.helpers.consensus_arbiter import load_consensus_config
        
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "production",
            "CONSENSUS_SIMULATION": "false"
        }):
            # Should not raise
            config = load_consensus_config()
            assert config is not None
            assert config.simulation_enabled is False
    
    def test_development_with_simulation_allowed(self):
        """
        In development, CONSENSUS_SIMULATION=true is allowed.
        """
        from python.helpers.consensus_arbiter import load_consensus_config
        
        with mock.patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "true"
        }):
            # Should not raise
            config = load_consensus_config()
            assert config is not None
            assert config.simulation_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
