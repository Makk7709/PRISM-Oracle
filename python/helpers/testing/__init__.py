# -*- coding: utf-8 -*-
"""
Testing utilities for KOREV Evidence.

This module provides:
- FakeLiteLLMProvider: Deterministic LLM responses from fixtures
- FakeTimeProvider: Injectable clock for timeout testing
- Fixture management: Load/validate/record fixtures (VERSIONED)
- Version constants for fixture key computation

Usage in tests:
    from python.helpers.testing import (
        FakeLiteLLMProvider,
        FakeTimeProvider,
        install_fake_provider,
        MissingFixtureError,
        PROMPT_VERSION,
        TOOL_SCHEMA_VERSION,
    )
"""

from .fake_provider import (
    FakeLiteLLMProvider,
    FakeLiteLLMChatWrapper,
    install_fake_provider,
    uninstall_fake_provider,
    MissingFixtureError,
    is_fake_provider_installed,
)
from .fixtures import (
    FixtureManager,
    Fixture,
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
    check_timeout,
)
from .versions import (
    PROMPT_VERSION,
    TOOL_SCHEMA_VERSION,
    EVIDENCE_LOGIC_VERSION,
    get_version_suffix,
    get_all_versions,
)

__all__ = [
    # Fake provider
    "FakeLiteLLMProvider",
    "FakeLiteLLMChatWrapper",
    "install_fake_provider",
    "uninstall_fake_provider",
    "is_fake_provider_installed",
    "MissingFixtureError",
    # Fixtures
    "FixtureManager",
    "Fixture",
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
    "check_timeout",
    # Versions
    "PROMPT_VERSION",
    "TOOL_SCHEMA_VERSION",
    "EVIDENCE_LOGIC_VERSION",
    "get_version_suffix",
    "get_all_versions",
]
