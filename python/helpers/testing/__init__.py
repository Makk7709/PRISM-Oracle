# -*- coding: utf-8 -*-
"""
Testing utilities for Agent Zero / Korev Oracle.

This module provides:
- FakeLiteLLMProvider: Deterministic LLM responses from fixtures
- FakeTimeProvider: Injectable clock for timeout testing
- Fixture management: Load/validate/record fixtures

Usage in tests:
    from python.helpers.testing import (
        FakeLiteLLMProvider,
        FakeTimeProvider,
        install_fake_provider,
        MissingFixtureError,
    )
"""

from .fake_provider import (
    FakeLiteLLMProvider,
    FakeLiteLLMChatWrapper,
    install_fake_provider,
    uninstall_fake_provider,
    MissingFixtureError,
)
from .fixtures import (
    FixtureManager,
    normalize_messages,
    compute_fixture_key,
)
from .time_provider import (
    TimeProvider,
    FakeTimeProvider,
    RealTimeProvider,
    get_time_provider,
    set_time_provider,
    with_timeout,
    TimeoutExceeded,
)

__all__ = [
    # Fake provider
    "FakeLiteLLMProvider",
    "FakeLiteLLMChatWrapper",
    "install_fake_provider",
    "uninstall_fake_provider",
    "MissingFixtureError",
    # Fixtures
    "FixtureManager",
    "normalize_messages",
    "compute_fixture_key",
    # Time
    "TimeProvider",
    "FakeTimeProvider",
    "RealTimeProvider",
    "get_time_provider",
    "set_time_provider",
    "with_timeout",
    "TimeoutExceeded",
]
