"""
TDD — Strict rebranding verification tests.

These tests ensure NO client-visible "Agent Zero" / "A0" branding leaks
into the deployed product.  They are written BEFORE the refactoring so
they will initially FAIL (red phase).  After the rebranding, they must
all PASS (green phase).

Baseline reference: 308 existing tests PASSED before rebranding.
"""

from __future__ import annotations

import os
import re
import pathlib
import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Directories excluded from scanning (not client-visible or generated)
EXCLUDED_DIRS = {
    "venv", "node_modules", ".git", "__pycache__", ".pytest_cache",
    ".mypy_cache", "dist", "build", "*.egg-info",
}

# Files excluded from scanning
EXCLUDED_FILES = {
    # This test file itself references the forbidden patterns for testing
    "tests/test_rebrand_agent_zero.py",
    # Git internal files
    ".gitignore",
}


def _should_scan(path: pathlib.Path) -> bool:
    """Return True if path should be scanned for forbidden patterns."""
    rel = path.relative_to(ROOT)
    parts = rel.parts

    # Skip excluded directories
    for part in parts:
        if part in EXCLUDED_DIRS:
            return False

    # Skip excluded files
    rel_str = str(rel)
    if rel_str in EXCLUDED_FILES:
        return False

    # Only scan text files
    suffix = path.suffix.lower()
    TEXT_EXTS = {
        ".py", ".js", ".ts", ".html", ".css", ".md", ".txt", ".sh",
        ".yml", ".yaml", ".json", ".toml", ".cfg", ".conf", ".ini",
        ".env", ".gitignore", ".dockerignore",
    }
    if suffix not in TEXT_EXTS and path.name not in {
        "Dockerfile", "DockerfileLocal", "Makefile",
    }:
        return False

    return True


def _read_text_safe(path: pathlib.Path) -> str:
    """Read a file as text, returning '' on decode errors."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _collect_files() -> list[pathlib.Path]:
    """Collect all scannable files in the repo."""
    files = []
    for path in ROOT.rglob("*"):
        if path.is_file() and _should_scan(path):
            files.append(path)
    return sorted(files)


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 1 — CRITICAL: Direct "Agent Zero" branding visible to clients
# ══════════════════════════════════════════════════════════════════════════════

class TestNoAgentZeroBranding:
    """Verify no 'Agent Zero' branding remains in client-visible files."""

    # Files where 'Agent Zero' / 'agent-zero' is strictly forbidden
    CRITICAL_FILES = [
        "webui/components/settings/legal/legal-notices.html",
        "docker/run/docker-compose.yml",
        "docker/run/fs/exe/run_A0.sh",  # file shouldn't exist after rename
        "docker/run/fs/ins/copy_A0.sh",  # file shouldn't exist after rename
    ]

    def test_no_agent_zero_in_legal_notices_html(self):
        """Legal notices must not show 'AGENT ZERO' as a prominent heading."""
        path = ROOT / "webui/components/settings/legal/legal-notices.html"
        content = _read_text_safe(path)
        # <strong>AGENT ZERO — MIT License</strong> is client-visible heading
        assert "<strong>AGENT ZERO" not in content, \
            "legal-notices.html still contains prominent 'AGENT ZERO' heading"

    def test_no_agent_zero_in_third_party_notices(self):
        """THIRD_PARTY_NOTICES.txt must not have 'AGENT ZERO' as a section header."""
        path = ROOT / "legal/THIRD_PARTY_NOTICES.txt"
        content = _read_text_safe(path)
        # The === AGENT ZERO === block header is client-visible
        assert "AGENT ZERO" not in content.split("ADDITIONAL")[0], \
            "THIRD_PARTY_NOTICES.txt still has 'AGENT ZERO' as main section header"

    def test_no_frdel_github_link_in_legal(self):
        """Legal notices must not contain github.com/frdel/agent-zero link."""
        for fname in [
            "webui/components/settings/legal/legal-notices.html",
            "legal/THIRD_PARTY_NOTICES.txt",
        ]:
            path = ROOT / fname
            content = _read_text_safe(path)
            assert "frdel/agent-zero" not in content, \
                f"{fname} still contains frdel/agent-zero GitHub link"

    def test_no_agent0ai_in_funding(self):
        """.github/FUNDING.yml must not reference agent0ai."""
        path = ROOT / ".github/FUNDING.yml"
        content = _read_text_safe(path)
        assert "agent0ai" not in content, \
            "FUNDING.yml still references agent0ai"

    def test_no_agent0ai_in_docs(self):
        """Documentation must not reference agent0ai GitHub org."""
        for fname in [
            "docs/README.md",
        ]:
            path = ROOT / fname
            if path.exists():
                content = _read_text_safe(path)
                assert "agent0ai" not in content, \
                    f"{fname} still references agent0ai"


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 2 — Docker paths: /a0/ → /app/, /git/agent-zero → /git/korev-evidence
# ══════════════════════════════════════════════════════════════════════════════

class TestDockerPathRebranding:
    """Verify Docker scripts use /app/ instead of /a0/ and no /git/agent-zero."""

    DOCKER_SCRIPTS = [
        "docker/run/fs/exe/run_evidence.sh",      # renamed from run_A0.sh
        "docker/run/fs/ins/copy_evidence.sh",      # renamed from copy_A0.sh
        "docker/run/fs/ins/install_evidence.sh",   # renamed from install_A0.sh
        "docker/run/fs/ins/install_evidence2.sh",  # renamed from install_A02.sh
        "docker/run/fs/exe/run_tunnel_api.sh",
        "docker/run/fs/ins/install_playwright.sh",
    ]

    def test_renamed_scripts_exist(self):
        """Renamed Docker scripts must exist."""
        for script in self.DOCKER_SCRIPTS:
            path = ROOT / script
            assert path.exists(), f"Renamed script {script} does not exist"

    def test_old_a0_scripts_removed(self):
        """Old A0-named scripts must be removed."""
        old_scripts = [
            "docker/run/fs/exe/run_A0.sh",
            "docker/run/fs/ins/copy_A0.sh",
            "docker/run/fs/ins/install_A0.sh",
            "docker/run/fs/ins/install_A02.sh",
        ]
        for script in old_scripts:
            path = ROOT / script
            assert not path.exists(), f"Old script {script} still exists"

    def test_no_git_agent_zero_path(self):
        """No Docker script should reference /git/agent-zero."""
        for script in self.DOCKER_SCRIPTS:
            path = ROOT / script
            if path.exists():
                content = _read_text_safe(path)
                assert "/git/agent-zero" not in content, \
                    f"{script} still references /git/agent-zero"

    def test_no_a0_runtime_path_in_scripts(self):
        """Docker scripts must use /app/ instead of /a0/."""
        for script in self.DOCKER_SCRIPTS:
            path = ROOT / script
            if path.exists():
                content = _read_text_safe(path)
                # Match /a0/ or /a0\b but not in comments about backward compat
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    assert "/a0/" not in line and not re.search(r"/a0\b", line), \
                        f"{script}:{i} still references /a0 path: {line.strip()}"

    def test_no_starting_a0_message(self):
        """No 'Starting A0' echo message in Docker scripts."""
        for script_dir in [
            "docker/run/fs/exe",
            "docker/run/fs/ins",
        ]:
            dir_path = ROOT / script_dir
            if dir_path.exists():
                for path in dir_path.iterdir():
                    if path.suffix == ".sh":
                        content = _read_text_safe(path)
                        assert "Starting A0" not in content, \
                            f"{path.name} still has 'Starting A0' message"

    def test_docker_compose_no_a0_path(self):
        """docker-compose.yml must not mount to /a0/."""
        path = ROOT / "docker/run/docker-compose.yml"
        content = _read_text_safe(path)
        assert ":/a0/" not in content and ":/a0\n" not in content, \
            "docker-compose.yml still mounts to /a0"

    def test_supervisord_uses_renamed_script(self):
        """supervisord.conf must reference run_evidence.sh, not run_A0.sh."""
        path = ROOT / "docker/run/fs/etc/supervisor/conf.d/supervisord.conf"
        content = _read_text_safe(path)
        assert "run_A0.sh" not in content, \
            "supervisord.conf still references run_A0.sh"
        assert "run_evidence.sh" in content, \
            "supervisord.conf does not reference run_evidence.sh"

    def test_dockerfiles_use_renamed_scripts(self):
        """Dockerfiles must reference renamed scripts."""
        for dockerfile in ["DockerfileLocal", "docker/run/Dockerfile"]:
            path = ROOT / dockerfile
            content = _read_text_safe(path)
            assert "run_A0.sh" not in content, \
                f"{dockerfile} still references run_A0.sh"
            assert "install_A0.sh" not in content, \
                f"{dockerfile} still references install_A0.sh"
            assert "install_A02.sh" not in content, \
                f"{dockerfile} still references install_A02.sh"

    def test_dockerfile_no_agent_zero_symlink(self):
        """DockerfileLocal must not create /git/agent-zero symlink."""
        path = ROOT / "DockerfileLocal"
        content = _read_text_safe(path)
        assert "agent-zero" not in content, \
            "DockerfileLocal still references agent-zero"

    def test_dockerfile_copies_to_korev_evidence(self):
        """DockerfileLocal should copy to /git/korev-evidence."""
        path = ROOT / "DockerfileLocal"
        content = _read_text_safe(path)
        assert "/git/korev-evidence" in content, \
            "DockerfileLocal does not reference /git/korev-evidence"


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 3 — Python code backward-compat paths
# ══════════════════════════════════════════════════════════════════════════════

class TestPythonCodePaths:
    """Verify Python code supports /app/ path alongside legacy paths."""

    def test_fix_dev_path_supports_app(self):
        """files.fix_dev_path must handle /app/ prefix."""
        from python.helpers.files import fix_dev_path
        # In dev mode, /app/foo should resolve like /a0/foo and /korev/foo
        result = fix_dev_path("/app/tmp/test.txt")
        assert "tmp/test.txt" in result
        assert "/app/" not in result  # prefix should be stripped in dev mode

    def test_api_files_get_supports_app_path(self):
        """api_files_get.py must handle /app/ prefix."""
        path = ROOT / "python/api/api_files_get.py"
        content = _read_text_safe(path)
        assert '"/app/"' in content or "'/app/'" in content or \
               'startswith("/app/")' in content, \
            "api_files_get.py does not handle /app/ prefix"

    def test_messages_js_supports_app_path(self):
        """messages.js must handle /app/ path normalization."""
        path = ROOT / "webui/js/messages.js"
        content = _read_text_safe(path)
        assert "/app/" in content, \
            "messages.js does not handle /app/ path normalization"


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 4 — Prompts use /app/ not /a0/
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptsRebranded:
    """Verify prompt files use /app/ instead of /a0/."""

    PROMPT_FILES = [
        "prompts/agent.system.tool.browser.md",
        "prompts/agent.system.main.communication_additions.md",
    ]

    def test_prompts_no_a0_path(self):
        """Prompt files must use /app/ instead of /a0/."""
        for fname in self.PROMPT_FILES:
            path = ROOT / fname
            if path.exists():
                content = _read_text_safe(path)
                assert "/a0/" not in content, \
                    f"{fname} still contains /a0/ path"


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 5 — Other artifacts
# ══════════════════════════════════════════════════════════════════════════════

class TestOtherArtifacts:
    """Verify other files are rebranded."""

    def test_yt_download_uses_app_path(self):
        """yt_download scripts must use /app/ instead of /a0/."""
        for fname in [
            "instruments/default/yt_download/yt_download.sh",
            "instruments/default/yt_download/yt_download.md",
        ]:
            path = ROOT / fname
            if path.exists():
                content = _read_text_safe(path)
                assert "/a0/" not in content, \
                    f"{fname} still contains /a0/ path"

    def test_gitignore_comment_updated(self):
        """projects.default.gitignore should not mention 'A0 project'."""
        path = ROOT / "conf/projects.default.gitignore"
        content = _read_text_safe(path)
        assert "A0 project" not in content, \
            "projects.default.gitignore still mentions 'A0 project'"

    def test_readme_no_explicit_agent_zero(self):
        """README.md should not mention 'Agent Zero' except in THIRD_PARTY reference."""
        path = ROOT / "README.md"
        content = _read_text_safe(path)
        # The line "La licence MIT originale d'Agent Zero" should be rebranded
        assert "Agent Zero" not in content, \
            "README.md still explicitly mentions 'Agent Zero'"

    def test_knowledge_installation_no_a0(self):
        """Knowledge installation guide must use /app/ instead of /a0/."""
        path = ROOT / "knowledge/default/main/about/installation.md"
        if path.exists():
            content = _read_text_safe(path)
            # Count /a0 references that are NOT in backward-compat or explanation context
            active_a0_refs = []
            for i, line in enumerate(content.split("\n"), 1):
                if "/a0" in line and "legacy" not in line.lower():
                    active_a0_refs.append(f"  line {i}: {line.strip()}")
            assert len(active_a0_refs) == 0, \
                f"installation.md still has active /a0 references:\n" + \
                "\n".join(active_a0_refs[:10])


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 6 — Comprehensive sweep: no 'agent-zero' in ANY repo file
# ══════════════════════════════════════════════════════════════════════════════

class TestComprehensiveSweep:
    """Final sweep: forbidden patterns must not appear outside allowlisted contexts."""

    # Patterns strictly forbidden everywhere
    FORBIDDEN_PATTERNS = [
        (r"github\.com/frdel/agent-zero", "frdel/agent-zero GitHub link"),
        (r"github\.com/agent0ai/agent-zero", "agent0ai/agent-zero GitHub link"),
        (r"Starting A0\b", "'Starting A0' log message"),
    ]

    # Files allowed to contain 'agent_zero' ONLY for backward compatibility
    BACKWARD_COMPAT_ALLOWLIST = {
        "webui/components/settings/backup/backup-store.js",  # .agent_zero_version fallback
        "python/helpers/files.py",  # normalize_a0_path alias
    }

    def test_no_forbidden_patterns_in_repo(self):
        """No forbidden pattern should appear in any repo file."""
        files = _collect_files()
        violations = []

        for path in files:
            rel = str(path.relative_to(ROOT))
            content = _read_text_safe(path)

            for pattern, description in self.FORBIDDEN_PATTERNS:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                if matches:
                    for m in matches:
                        line_num = content[:m.start()].count("\n") + 1
                        violations.append(
                            f"  {rel}:{line_num} — {description}: "
                            f"{m.group()!r}"
                        )

        assert len(violations) == 0, \
            f"Found {len(violations)} forbidden pattern(s):\n" + \
            "\n".join(violations[:20])

    def test_no_a0_docker_paths_outside_compat(self):
        """No /a0/ Docker paths outside backward-compat allowlist."""
        # Check Docker-related files specifically
        docker_files = [
            "docker/run/docker-compose.yml",
            "docker/run/fs/etc/supervisor/conf.d/supervisord.conf",
        ]
        for fname in docker_files:
            path = ROOT / fname
            if path.exists():
                content = _read_text_safe(path)
                assert "/a0/" not in content and "/a0\n" not in content, \
                    f"{fname} still contains /a0 path reference"
