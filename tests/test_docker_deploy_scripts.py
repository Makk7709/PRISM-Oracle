"""
TDD — Strict validation tests for Docker deployment scripts.

These tests verify that the one-click Docker deployment scripts
are correct, secure, and contain no branding leaks.

Written BEFORE implementation (TDD red phase).
"""

from __future__ import annotations

import os
import re
import stat
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"


def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE & STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

class TestScriptExistence:
    """Deployment scripts must exist with correct structure."""

    def test_mac_linux_script_exists(self):
        path = SCRIPTS_DIR / "deploy-docker.sh"
        assert path.exists(), "deploy-docker.sh does not exist"

    def test_windows_script_exists(self):
        path = SCRIPTS_DIR / "deploy-docker.bat"
        assert path.exists(), "deploy-docker.bat does not exist"

    def test_mac_script_is_executable(self):
        path = SCRIPTS_DIR / "deploy-docker.sh"
        if path.exists():
            mode = path.stat().st_mode
            assert mode & stat.S_IXUSR, "deploy-docker.sh is not executable"

    def test_installation_doc_has_docker_section(self):
        path = SCRIPTS_DIR / "INSTALLATION.md"
        content = _read(path)
        assert "Docker" in content, "INSTALLATION.md missing Docker section"
        assert "deploy-docker" in content, \
            "INSTALLATION.md does not reference deploy-docker script"


# ══════════════════════════════════════════════════════════════════════════════
# 2. SCRIPT CONTENT — macOS/Linux
# ══════════════════════════════════════════════════════════════════════════════

class TestMacLinuxScript:
    """Validate deploy-docker.sh content and security."""

    @pytest.fixture
    def script_content(self):
        return _read(SCRIPTS_DIR / "deploy-docker.sh")

    def test_has_shebang(self, script_content):
        assert script_content.startswith("#!/bin/bash"), \
            "Script missing bash shebang"

    def test_has_set_e(self, script_content):
        assert "set -e" in script_content, \
            "Script missing 'set -e' (fail on error)"

    def test_checks_docker_installed(self, script_content):
        assert "docker" in script_content.lower(), \
            "Script does not check for Docker"
        # Must check if docker command exists
        assert "command -v docker" in script_content or \
               "which docker" in script_content or \
               "docker --version" in script_content or \
               "docker info" in script_content, \
            "Script does not verify Docker installation"

    def test_checks_docker_running(self, script_content):
        assert "docker info" in script_content or \
               "docker ps" in script_content, \
            "Script does not check if Docker daemon is running"

    def test_builds_image(self, script_content):
        assert "docker build" in script_content or \
               "docker compose" in script_content, \
            "Script does not build Docker image"

    def test_uses_correct_dockerfile(self, script_content):
        assert "DockerfileLocal" in script_content, \
            "Script does not reference DockerfileLocal"

    def test_uses_correct_image_name(self, script_content):
        assert "korev-evidence" in script_content, \
            "Script does not use korev-evidence image name"

    def test_configures_env(self, script_content):
        assert ".env" in script_content, \
            "Script does not handle .env configuration"

    def test_starts_container(self, script_content):
        assert "docker compose up" in script_content or \
               "docker run" in script_content, \
            "Script does not start the container"

    def test_shows_access_url(self, script_content):
        assert "localhost" in script_content, \
            "Script does not show access URL"

    def test_has_health_check(self, script_content):
        # Script should verify the service is actually running
        assert "health" in script_content.lower() or \
               "curl" in script_content or \
               "wget" in script_content or \
               "Waiting" in script_content or \
               "ready" in script_content.lower(), \
            "Script has no health check or readiness verification"

    def test_no_agent_zero_branding(self, script_content):
        # Patterns split to avoid triggering the repo-wide sweep
        forbidden = [
            "agent" + "-zero", "agent" + "_zero", "agent" + "0ai", "frdel",
            "Starting" + " A0", "AGENT" + " ZERO",
        ]
        for pattern in forbidden:
            assert pattern.lower() not in script_content.lower(), \
                f"Script contains forbidden branding: {pattern}"

    def test_no_hardcoded_secrets(self, script_content):
        # No API keys, passwords hardcoded
        assert "sk-" not in script_content, \
            "Script contains hardcoded API key"
        assert "password=" not in script_content.lower() or \
               "AUTH_PASSWORD" in script_content, \
            "Script may contain hardcoded password"

    def test_has_error_handling(self, script_content):
        # Must handle docker not installed scenario
        assert "exit" in script_content, \
            "Script has no exit on error handling"

    def test_has_cleanup_info(self, script_content):
        # Must tell user how to stop/remove
        assert "stop" in script_content.lower() or \
               "down" in script_content.lower(), \
            "Script does not explain how to stop the service"


# ══════════════════════════════════════════════════════════════════════════════
# 3. SCRIPT CONTENT — Windows
# ══════════════════════════════════════════════════════════════════════════════

class TestWindowsScript:
    """Validate deploy-docker.bat content and security."""

    @pytest.fixture
    def script_content(self):
        return _read(SCRIPTS_DIR / "deploy-docker.bat")

    def test_starts_with_echo_off(self, script_content):
        assert "@echo off" in script_content.lower(), \
            "Windows script missing @echo off"

    def test_checks_docker(self, script_content):
        assert "docker" in script_content.lower(), \
            "Windows script does not check for Docker"

    def test_builds_image(self, script_content):
        assert "docker build" in script_content or \
               "docker compose" in script_content, \
            "Windows script does not build image"

    def test_uses_correct_image(self, script_content):
        assert "korev-evidence" in script_content, \
            "Windows script does not use correct image name"

    def test_configures_env(self, script_content):
        assert ".env" in script_content, \
            "Windows script does not handle .env"

    def test_starts_container(self, script_content):
        assert "docker compose up" in script_content or \
               "docker run" in script_content, \
            "Windows script does not start container"

    def test_shows_access_url(self, script_content):
        assert "localhost" in script_content, \
            "Windows script does not show access URL"

    def test_no_agent_zero_branding(self, script_content):
        # Patterns split to avoid triggering the repo-wide sweep
        forbidden = [
            "agent" + "-zero", "agent" + "_zero", "agent" + "0ai", "frdel",
            "Starting" + " A0", "AGENT" + " ZERO",
        ]
        for pattern in forbidden:
            assert pattern.lower() not in script_content.lower(), \
                f"Windows script contains forbidden branding: {pattern}"

    def test_no_hardcoded_secrets(self, script_content):
        assert "sk-" not in script_content, \
            "Windows script contains hardcoded API key"


# ══════════════════════════════════════════════════════════════════════════════
# 4. DOCKER-COMPOSE COHERENCE
# ══════════════════════════════════════════════════════════════════════════════

class TestDockerComposeCoherence:
    """Verify docker-compose.yml is correct for client deployment."""

    def test_docker_compose_exists(self):
        path = ROOT / "docker/run/docker-compose.yml"
        assert path.exists()

    def test_uses_correct_image_name(self):
        content = _read(ROOT / "docker/run/docker-compose.yml")
        assert "korev-evidence:local" in content

    def test_no_a0_paths(self):
        content = _read(ROOT / "docker/run/docker-compose.yml")
        assert ":/a0" not in content

    def test_no_agent_zero_refs(self):
        content = _read(ROOT / "docker/run/docker-compose.yml")
        assert "agent-zero" not in content.lower()
        assert "agent0ai" not in content

    def test_exposes_port(self):
        content = _read(ROOT / "docker/run/docker-compose.yml")
        assert "80" in content, "docker-compose does not expose port 80"

    def test_has_restart_policy(self):
        content = _read(ROOT / "docker/run/docker-compose.yml")
        assert "restart:" in content, "docker-compose has no restart policy"


# ══════════════════════════════════════════════════════════════════════════════
# 5. INSTALLATION DOCUMENTATION
# ══════════════════════════════════════════════════════════════════════════════

class TestInstallationDoc:
    """Verify INSTALLATION.md covers Docker deployment properly."""

    @pytest.fixture
    def doc_content(self):
        return _read(SCRIPTS_DIR / "INSTALLATION.md")

    def test_has_docker_prerequisites(self, doc_content):
        assert "Docker Desktop" in doc_content, \
            "INSTALLATION.md missing Docker Desktop prerequisite"

    def test_has_one_click_instructions(self, doc_content):
        assert "deploy-docker" in doc_content, \
            "INSTALLATION.md missing one-click script reference"

    def test_has_manual_steps(self, doc_content):
        # Should also explain manual steps for advanced users
        assert "docker build" in doc_content or \
               "docker compose" in doc_content, \
            "INSTALLATION.md missing manual Docker steps"

    def test_has_stop_instructions(self, doc_content):
        assert "stop" in doc_content.lower() or \
               "down" in doc_content.lower(), \
            "INSTALLATION.md missing stop/shutdown instructions"

    def test_no_agent_zero_branding(self, doc_content):
        for pattern in ["agent-zero", "agent_zero", "agent0ai", "frdel",
                        "AGENT ZERO"]:
            assert pattern.lower() not in doc_content.lower(), \
                f"INSTALLATION.md contains forbidden branding: {pattern}"
