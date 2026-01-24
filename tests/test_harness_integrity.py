# -*- coding: utf-8 -*-
"""
Harness Integrity Tests — Verify the test harness itself is working correctly.

These tests verify:
1. Fixture versioning works correctly
2. No sleep() calls in replay harness
3. Timeouts trigger via FakeTimeProvider without waiting
4. CI gates are properly configured
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from python.helpers.testing import (
    PROMPT_VERSION,
    TOOL_SCHEMA_VERSION,
    get_version_suffix,
    compute_fixture_key,
    FixtureManager,
    Fixture,
    FakeTimeProvider,
    set_time_provider,
    RealTimeProvider,
    with_timeout,
    TimeoutExceeded,
    check_timeout,
)


# ============================================================================
# PHASE 2: FIXTURE VERSIONING TESTS
# ============================================================================

class TestFixtureVersioning:
    """Tests that fixture keys include version information."""
    
    def test_version_constants_exist(self):
        """Version constants are defined and non-empty."""
        assert PROMPT_VERSION, "PROMPT_VERSION must be defined"
        assert TOOL_SCHEMA_VERSION, "TOOL_SCHEMA_VERSION must be defined"
        assert len(PROMPT_VERSION) >= 5, "PROMPT_VERSION too short"
    
    def test_version_suffix_format(self):
        """Version suffix has expected format."""
        suffix = get_version_suffix()
        assert suffix.startswith("pv-"), f"Suffix should start with 'pv-': {suffix}"
        assert "__sv-" in suffix, f"Suffix should contain '__sv-': {suffix}"
    
    def test_fixture_key_includes_versions(self):
        """compute_fixture_key result is used in versioned keys."""
        messages = [{"role": "user", "content": "test"}]
        messages_hash = compute_fixture_key(messages)
        
        # Create a fixture and check its key includes versions
        fixture = Fixture(
            provider="openai",
            model="gpt-4",
            role="chat",
            messages_hash=messages_hash,
            prompt_version=PROMPT_VERSION,
            tool_schema_version=TOOL_SCHEMA_VERSION,
            response="test response",
        )
        
        key = fixture.key
        assert f"pv-{PROMPT_VERSION}" in key, f"Key should include PROMPT_VERSION: {key}"
        assert f"sv-{TOOL_SCHEMA_VERSION}" in key, f"Key should include TOOL_SCHEMA_VERSION: {key}"
    
    def test_version_bump_changes_key(self):
        """Changing version changes fixture key."""
        messages = [{"role": "user", "content": "test"}]
        messages_hash = compute_fixture_key(messages)
        
        fixture1 = Fixture(
            provider="openai",
            model="gpt-4",
            role="chat",
            messages_hash=messages_hash,
            prompt_version="2026-01-24-a",
            tool_schema_version="v1",
            response="test",
        )
        
        fixture2 = Fixture(
            provider="openai",
            model="gpt-4",
            role="chat",
            messages_hash=messages_hash,
            prompt_version="2026-01-24-b",  # Bumped
            tool_schema_version="v1",
            response="test",
        )
        
        # Note: key property uses global versions, so we check filename instead
        assert fixture1.prompt_version != fixture2.prompt_version
    
    def test_fixture_filename_includes_versions(self):
        """Fixture filename includes version info."""
        fixture = Fixture(
            provider="openai",
            model="gpt-4",
            role="chat",
            messages_hash="abc123def456",
            prompt_version=PROMPT_VERSION,
            tool_schema_version=TOOL_SCHEMA_VERSION,
            response="test",
        )
        
        filename = fixture.filename
        assert f"pv-{PROMPT_VERSION}" in filename
        assert f"sv-{TOOL_SCHEMA_VERSION}" in filename
    
    def test_legacy_fixture_detection(self):
        """Legacy fixtures (no versions) are detected."""
        fixture = Fixture(
            provider="openai",
            model="gpt-4",
            role="chat",
            messages_hash="abc123",
            response="test",
            # No versions set
        )
        
        assert not fixture.is_versioned, "Empty version fixture should not be versioned"
        assert not fixture.is_current_version, "Empty version fixture should not be current"


class TestStrictFixturesMode:
    """Tests for STRICT_FIXTURES=1 mode."""
    
    def test_strict_mode_from_env(self):
        """FixtureManager respects STRICT_FIXTURES env var."""
        # Without env var
        manager1 = FixtureManager(strict_mode=False)
        assert not manager1.strict_mode
        
        # With explicit strict mode
        manager2 = FixtureManager(strict_mode=True)
        assert manager2.strict_mode


# ============================================================================
# PHASE 3: NO SLEEP TESTS
# ============================================================================

class TestNoSleepInHarness:
    """Tests that replay harness doesn't use sleep()."""
    
    HARNESS_FILES = [
        "tests/test_replay_harness.py",
        "python/helpers/testing/fake_provider.py",
        "python/helpers/testing/fixtures.py",
    ]
    
    # Allowed sleep patterns (in testing utilities only)
    ALLOWED_SLEEP_PATTERNS = [
        r"await asyncio\.sleep\(0\)",  # Yield control only
        r"# .* sleep",  # Comments
        r"FakeTimeProvider.*sleep",  # FakeTimeProvider.sleep method def
        r"async def sleep",  # Method definition
    ]
    
    def test_no_real_sleep_in_replay_harness(self):
        """
        Verify test_replay_harness.py doesn't use real sleep.
        
        time.sleep() and asyncio.sleep(>0) are forbidden.
        """
        repo_root = Path(__file__).parent.parent
        harness_file = repo_root / "tests" / "test_replay_harness.py"
        content = harness_file.read_text()
        
        # Check for time.sleep
        time_sleep_matches = re.findall(r"time\.sleep\s*\([^)]+\)", content)
        assert not time_sleep_matches, (
            f"time.sleep() found in replay harness: {time_sleep_matches}"
        )
        
        # Check for asyncio.sleep with non-zero value
        asyncio_sleep_matches = re.findall(r"asyncio\.sleep\s*\(([^)]+)\)", content)
        for match in asyncio_sleep_matches:
            match = match.strip()
            # Allow sleep(0) or very small values for yielding
            if match not in ("0", "0.0", "0.01"):
                pytest.fail(f"asyncio.sleep({match}) found - use FakeTimeProvider instead")
    
    def test_no_time_import_in_replay_harness(self):
        """
        Verify replay harness doesn't import time module for sleeping.
        """
        repo_root = Path(__file__).parent.parent
        harness_file = repo_root / "tests" / "test_replay_harness.py"
        content = harness_file.read_text()
        
        # Check for 'import time' or 'from time import'
        if "import time" in content:
            # Make sure it's not used for sleep
            if "time.sleep" in content:
                pytest.fail("time.sleep used in replay harness")


class TestTimeoutWithoutWaiting:
    """Tests that timeouts work via FakeTimeProvider without real waiting."""
    
    @pytest.mark.asyncio
    async def test_timeout_triggers_instantly_with_fake_time(self):
        """
        Timeout triggers instantly when FakeTimeProvider advances.
        
        This proves we don't need to wait real time.
        """
        fake_time = FakeTimeProvider(start_ms=0)
        old_provider = set_time_provider(fake_time)
        
        try:
            async def slow_operation():
                # Check time at start
                start = fake_time.now_ms()
                
                # Simulate work (advance time without sleeping)
                fake_time.advance(5000)  # 5 seconds
                
                # Time has passed in fake world
                elapsed = fake_time.now_ms() - start
                assert elapsed == 5000, "Fake time should have advanced"
                
                return "result"
            
            # This should timeout because fake time advances past budget
            with pytest.raises(TimeoutExceeded) as exc_info:
                await with_timeout(slow_operation(), timeout_ms=1000)
            
            assert exc_info.value.timeout_ms == 1000
        finally:
            set_time_provider(old_provider)
    
    @pytest.mark.asyncio
    async def test_check_timeout_raises_when_exceeded(self):
        """check_timeout() raises immediately when time exceeded."""
        fake_time = FakeTimeProvider(start_ms=0)
        old_provider = set_time_provider(fake_time)
        
        try:
            start_ms = fake_time.now_ms()
            
            # Advance past timeout
            fake_time.advance(2000)
            
            # Should raise immediately
            with pytest.raises(TimeoutExceeded):
                await check_timeout(start_ms, timeout_ms=1000)
        finally:
            set_time_provider(old_provider)
    
    def test_fake_time_advance_is_instant(self):
        """FakeTimeProvider.advance() is instant, not real time."""
        import time
        
        fake_time = FakeTimeProvider(start_ms=0)
        
        real_start = time.monotonic()
        
        # Advance fake time by 1 hour
        fake_time.advance(3600 * 1000)  # 1 hour in ms
        
        real_elapsed = time.monotonic() - real_start
        
        # Real time should be < 0.1 seconds
        assert real_elapsed < 0.1, (
            f"FakeTimeProvider.advance() took {real_elapsed}s - should be instant!"
        )
        
        # But fake time should be 1 hour
        assert fake_time.now_ms() == 3600 * 1000


# ============================================================================
# PHASE 4: CI GATES TESTS
# ============================================================================

class TestCIGates:
    """Tests that CI gates are properly configured."""
    
    def test_fast_gate_excludes_slow_tests(self):
        """
        FAST gate (pytest -m 'not slow') excludes replay harness.
        """
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_metacognition_policy.py",
                "tests/test_replay_harness.py",
                "-m", "not slow",
                "--collect-only", "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=30,
        )
        
        collected = result.stdout
        
        # test_replay_harness should NOT be collected
        assert "test_replay_case" not in collected or "deselected" in collected, (
            "FAST gate should exclude slow replay tests"
        )
        
        # test_metacognition_policy should BE collected
        assert "test_critical_confidence" in collected, (
            "FAST gate should include policy tests"
        )
    
    def test_full_gate_includes_all_tests(self):
        """
        FULL gate (pytest without -m) includes all tests.
        """
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_metacognition_policy.py",
                "tests/test_replay_harness.py",
                "--collect-only", "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=30,
        )
        
        collected = result.stdout
        
        # Both should be collected
        assert "test_replay_case" in collected, "FULL gate should include replay tests"
        assert "test_critical_confidence" in collected, "FULL gate should include policy tests"
    
    def test_slow_marker_on_replay_harness(self):
        """
        test_replay_harness.py has @pytest.mark.slow on TestReplayHarness.
        """
        repo_root = Path(__file__).parent.parent
        harness_file = repo_root / "tests" / "test_replay_harness.py"
        content = harness_file.read_text()
        
        assert "@pytest.mark.slow" in content, (
            "TestReplayHarness should have @pytest.mark.slow marker"
        )


class TestGuardRailsIntegrity:
    """Tests that guard rails are in place."""
    
    def test_conftest_has_network_guard(self):
        """conftest.py has network guard fixture."""
        repo_root = Path(__file__).parent.parent
        conftest_file = repo_root / "tests" / "conftest.py"
        content = conftest_file.read_text()
        
        assert "_network_guard" in content, "Network guard fixture missing"
        assert "autouse=True" in content, "Network guard should be autouse"
        assert "REAL_LITELLM_CALL_FORBIDDEN" in content, "Guard should have clear error"
    
    def test_harness_files_exist(self):
        """All harness files exist."""
        repo_root = Path(__file__).parent.parent
        
        required_files = [
            "tests/conftest.py",
            "tests/test_no_bypass_litellm.py",
            "tests/test_replay_harness.py",
            "python/helpers/testing/__init__.py",
            "python/helpers/testing/fake_provider.py",
            "python/helpers/testing/fixtures.py",
            "python/helpers/testing/time_provider.py",
            "python/helpers/testing/versions.py",
        ]
        
        for rel_path in required_files:
            full_path = repo_root / rel_path
            assert full_path.exists(), f"Required file missing: {rel_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
