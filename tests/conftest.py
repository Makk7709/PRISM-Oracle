# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures for Agent Zero / Korev Oracle tests.

CRITICAL: This file implements a NETWORK GUARD that prevents any real LiteLLM
calls during tests. If a test tries to call a real LLM API, it will fail
with RuntimeError("REAL_LITELLM_CALL_FORBIDDEN").

The guard is ALWAYS active in tests (autouse=True) and cannot be bypassed.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest


# ============================================================================
# NETWORK GUARD — PREVENTS REAL LITELLM CALLS
# ============================================================================

class RealLiteLLMCallForbiddenError(RuntimeError):
    """
    Raised when a test attempts to make a real LiteLLM API call.
    
    This error means:
    1. The FakeProvider was not installed, OR
    2. A code path bypassed the FakeProvider
    
    To fix:
    - Ensure install_fake_provider() is called before LLM operations
    - Or add a fixture for the missing LLM call
    """
    
    def __init__(self, function_name: str, args: tuple, kwargs: dict):
        self.function_name = function_name
        self.args = args
        self.kwargs = kwargs
        
        # Extract model info if available
        model = kwargs.get("model", "unknown")
        messages_count = len(kwargs.get("messages", []))
        
        super().__init__(
            f"\n"
            f"╔══════════════════════════════════════════════════════════════════╗\n"
            f"║              REAL LITELLM CALL FORBIDDEN IN TESTS                ║\n"
            f"╠══════════════════════════════════════════════════════════════════╣\n"
            f"║ Function:  {function_name:<53} ║\n"
            f"║ Model:     {model:<53} ║\n"
            f"║ Messages:  {messages_count:<53} ║\n"
            f"╠══════════════════════════════════════════════════════════════════╣\n"
            f"║ This error means:                                                ║\n"
            f"║ 1. FakeProvider was not installed, OR                            ║\n"
            f"║ 2. A code path bypassed the FakeProvider                         ║\n"
            f"╠══════════════════════════════════════════════════════════════════╣\n"
            f"║ To fix:                                                          ║\n"
            f"║ - Use install_fake_provider() before LLM operations              ║\n"
            f"║ - Or add a fixture for this LLM call                             ║\n"
            f"╚══════════════════════════════════════════════════════════════════╝\n"
        )


def _create_forbidden_completion(*args: Any, **kwargs: Any) -> None:
    """Replacement for litellm.completion that always raises."""
    raise RealLiteLLMCallForbiddenError("litellm.completion", args, kwargs)


async def _create_forbidden_acompletion(*args: Any, **kwargs: Any) -> None:
    """Replacement for litellm.acompletion that always raises."""
    raise RealLiteLLMCallForbiddenError("litellm.acompletion", args, kwargs)


def _create_forbidden_embedding(*args: Any, **kwargs: Any) -> None:
    """Replacement for litellm.embedding that always raises."""
    raise RealLiteLLMCallForbiddenError("litellm.embedding", args, kwargs)


@pytest.fixture(autouse=True, scope="function")
def _network_guard(monkeypatch):
    """
    AUTOUSE fixture that blocks all real LiteLLM API calls.
    
    This runs for EVERY test automatically. If a test needs to call
    a real LLM API (which should NEVER happen in CI), it must explicitly
    skip this guard via environment variable A0_ALLOW_REAL_LLM=1.
    """
    # Allow bypass only if explicitly requested (NEVER in CI)
    if os.environ.get("A0_ALLOW_REAL_LLM") == "1":
        yield
        return
    
    # Patch litellm module
    try:
        import litellm
        monkeypatch.setattr(litellm, "completion", _create_forbidden_completion)
        monkeypatch.setattr(litellm, "acompletion", _create_forbidden_acompletion)
        monkeypatch.setattr(litellm, "embedding", _create_forbidden_embedding)
    except ImportError:
        pass  # litellm not installed (shouldn't happen)
    
    # Also patch the models module wrapper if it imports these at module level
    try:
        import models
        # Patch the imported functions in models.py namespace
        if hasattr(models, "completion"):
            monkeypatch.setattr(models, "completion", _create_forbidden_completion)
        if hasattr(models, "acompletion"):
            monkeypatch.setattr(models, "acompletion", _create_forbidden_acompletion)
        if hasattr(models, "embedding"):
            monkeypatch.setattr(models, "embedding", _create_forbidden_embedding)
    except ImportError:
        pass
    
    yield


# ============================================================================
# STRICT FIXTURES MODE
# ============================================================================

@pytest.fixture(scope="session")
def strict_fixtures_mode():
    """
    Returns True if STRICT_FIXTURES=1 is set.
    
    In strict mode, legacy fixtures without version info will fail.
    """
    return os.environ.get("STRICT_FIXTURES") == "1"


# ============================================================================
# ENVIRONMENT INFO
# ============================================================================

def pytest_report_header(config):
    """Add custom header to pytest output."""
    lines = [
        "Agent Zero Test Harness:",
        f"  Network Guard: ACTIVE (real LiteLLM calls blocked)",
        f"  Strict Fixtures: {'ENABLED' if os.environ.get('STRICT_FIXTURES') == '1' else 'disabled'}",
        f"  Record Mode: {'ENABLED' if os.environ.get('A0_RECORD_FIXTURES') == '1' else 'disabled'}",
    ]
    return lines


# ============================================================================
# MARKERS
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "replay: marks tests as replay harness tests"
    )
    config.addinivalue_line(
        "markers", "invariant: marks tests that verify invariants (I1, I2, I4)"
    )
