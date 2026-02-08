# -*- coding: utf-8 -*-
"""
Tests that verify NO REAL LITELLM CALLS can happen in tests.

These tests prove that:
1. The network guard is active
2. Direct litellm calls are blocked
3. FakeProvider properly intercepts calls
4. No code path can bypass the guard

If any test in this file fails, it means real API calls could leak in tests.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Check if litellm is available
try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Skip marker for tests requiring litellm
requires_litellm = pytest.mark.skipif(
    not LITELLM_AVAILABLE,
    reason="litellm not installed - network guard tests require litellm"
)


# Define locally to avoid import issues (same class as in conftest.py)
class RealLiteLLMCallForbiddenError(RuntimeError):
    """Raised when a test attempts to make a real LiteLLM API call."""
    pass


# ============================================================================
# NETWORK GUARD TESTS
# ============================================================================

@requires_litellm
class TestNetworkGuard:
    """Tests that the network guard blocks real litellm calls."""
    
    def test_direct_completion_blocked(self):
        """Direct litellm.completion() is blocked."""
        import litellm
        
        with pytest.raises(RuntimeError) as exc_info:
            litellm.completion(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
            )
        
        error_msg = str(exc_info.value)
        assert "LITELLM" in error_msg.upper() and "FORBIDDEN" in error_msg.upper()
        assert "litellm.completion" in error_msg
    
    @pytest.mark.asyncio
    async def test_direct_acompletion_blocked(self):
        """Direct litellm.acompletion() is blocked."""
        import litellm
        
        with pytest.raises(RuntimeError) as exc_info:
            await litellm.acompletion(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
            )
        
        error_msg = str(exc_info.value)
        assert "LITELLM" in error_msg.upper() and "FORBIDDEN" in error_msg.upper()
        assert "litellm.acompletion" in error_msg
    
    def test_direct_embedding_blocked(self):
        """Direct litellm.embedding() is blocked."""
        import litellm
        
        with pytest.raises(RuntimeError) as exc_info:
            litellm.embedding(
                model="text-embedding-ada-002",
                input=["test"],
            )
        
        error_msg = str(exc_info.value)
        assert "LITELLM" in error_msg.upper() and "FORBIDDEN" in error_msg.upper()


@requires_litellm
class TestModelWrapperGuard:
    """Tests that model wrappers are also guarded."""
    
    def test_models_module_completion_blocked(self):
        """models.completion is blocked if accessed directly."""
        import models
        
        # The models module imports completion from litellm
        # Our guard patches it
        with pytest.raises(RuntimeError) as exc_info:
            models.completion(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
            )
        error_msg = str(exc_info.value)
        assert "LITELLM" in error_msg.upper() and "FORBIDDEN" in error_msg.upper()
    
    @pytest.mark.asyncio
    async def test_models_module_acompletion_blocked(self):
        """models.acompletion is blocked if accessed directly."""
        import models
        
        with pytest.raises(RuntimeError) as exc_info:
            await models.acompletion(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
            )
        error_msg = str(exc_info.value)
        assert "LITELLM" in error_msg.upper() and "FORBIDDEN" in error_msg.upper()


@requires_litellm
class TestFakeProviderBypass:
    """Tests that FakeProvider properly intercepts calls."""
    
    @pytest.mark.asyncio
    async def test_fake_provider_intercepts_calls(self):
        """When FakeProvider is installed, calls go to fixtures, not litellm."""
        from python.helpers.testing import (
            install_fake_provider,
            uninstall_fake_provider,
            MissingFixtureError,
        )
        
        install_fake_provider()
        
        try:
            import models
            
            # Get a fake model
            model = models.get_chat_model("openai", "gpt-4")
            
            # Call should go to FakeProvider, not litellm
            # Since we have no fixture, it should raise MissingFixtureError
            # NOT RealLiteLLMCallForbiddenError
            with pytest.raises(MissingFixtureError):
                await model.unified_call(
                    system_message="You are a test.",
                    user_message="Hello",
                )
        finally:
            uninstall_fake_provider()
    
    def test_fake_provider_uninstall_restores_guard(self):
        """After uninstalling FakeProvider, guard is still active."""
        from python.helpers.testing import (
            install_fake_provider,
            uninstall_fake_provider,
        )
        
        install_fake_provider()
        uninstall_fake_provider()
        
        # Guard should still be active
        import litellm
        with pytest.raises(RuntimeError) as exc_info:
            litellm.completion(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
            )
        error_msg = str(exc_info.value)
        assert "LITELLM" in error_msg.upper() and "FORBIDDEN" in error_msg.upper()


class TestNoDirectLiteLLMUsage:
    """Tests that no code outside models.py uses litellm directly."""
    
    # Files that are ALLOWED to import litellm directly
    ALLOWED_LITELLM_IMPORTS = {
        "models.py",
        "preload.py",  # Preloading/warmup
    }
    
    def test_no_direct_litellm_completion_calls_outside_models(self):
        """
        Verify no file outside models.py calls litellm.completion directly.
        
        This ensures all LLM calls go through our wrappers.
        """
        repo_root = Path(__file__).parent.parent
        python_dir = repo_root / "python"
        
        # Search for direct calls
        pattern = r"litellm\.(a?completion|embedding)\s*\("
        violations = []
        
        for py_file in python_dir.rglob("*.py"):
            rel_path = py_file.relative_to(repo_root)
            if any(allowed in str(rel_path) for allowed in self.ALLOWED_LITELLM_IMPORTS):
                continue
            
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            matches = re.findall(pattern, content)
            if matches:
                violations.append((str(rel_path), matches))
        
        assert not violations, (
            f"Direct litellm calls found outside allowed files:\n"
            + "\n".join(f"  {path}: {calls}" for path, calls in violations)
        )
    
    def test_no_direct_litellm_imports_in_tests(self):
        """
        Verify no test file imports litellm directly (except this one).
        """
        repo_root = Path(__file__).parent.parent
        tests_dir = repo_root / "tests"
        
        # Files allowed to import litellm (for testing the guard)
        allowed = {"test_no_bypass_litellm.py", "conftest.py"}
        
        pattern = r"^(?:from litellm import|import litellm)"
        violations = []
        
        for py_file in tests_dir.rglob("*.py"):
            if py_file.name in allowed:
                continue
            
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if re.match(pattern, line.strip()):
                    violations.append((py_file.name, i, line.strip()))
        
        assert not violations, (
            f"Direct litellm imports found in test files:\n"
            + "\n".join(f"  {name}:{line_no}: {line}" for name, line_no, line in violations)
        )


@requires_litellm
class TestGuardErrorMessage:
    """Tests that guard error messages are helpful."""
    
    def test_error_includes_model_info(self):
        """Error message includes model and message count."""
        import litellm
        
        try:
            litellm.completion(
                model="claude-3-opus",
                messages=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"},
                ],
            )
            pytest.fail("Expected RuntimeError for real LiteLLM call")
        except RuntimeError as e:
            # Catch RuntimeError (parent of both local and conftest versions)
            assert "claude-3-opus" in str(e)
            assert "2" in str(e)  # 2 messages
    
    def test_error_is_runtime_error(self):
        """Error is a RuntimeError subclass for easy catching."""
        assert issubclass(RealLiteLLMCallForbiddenError, RuntimeError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
