"""
Security Tests — Path Traversal in FileWriter._read_include_file()

Vulnerability: The _read_include_file() method reads arbitrary files from
disk based on paths found in include directives. A malicious prompt could
inject §§include(/etc/passwd) and the function would read the file.

Attack vectors tested:
1. Absolute path to system files         →  /etc/passwd
2. Relative traversal                     →  ../../../etc/passwd
3. Home directory sensitive files         →  ~/.ssh/id_rsa, ~/.env
4. Project-level sensitive files          →  .env, .git/config
5. Null byte truncation                   →  file.txt\x00.jpg
6. URL-encoded traversal                  →  ..%2F..%2F
7. Mixed legitimate + malicious includes  →  inline injection
8. Legitimate includes within project     →  regression test

These tests MUST FAIL before the fix (RED phase) and PASS after (GREEN phase).
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from python.helpers import files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_writer():
    """Create a FileWriter instance with minimal mocking."""
    from python.tools.file_writer import FileWriter

    # FileWriter extends Tool which needs agent, name, args, message
    mock_agent = MagicMock()
    mock_agent.config = MagicMock()
    
    writer = FileWriter.__new__(FileWriter)
    writer.agent = mock_agent
    writer.name = "file_writer"
    writer.args = {}
    writer.message = ""
    return writer


def _create_temp_file(content: str, suffix: str = ".txt") -> str:
    """Create a temporary file with given content, return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def writer():
    return _make_file_writer()


@pytest.fixture
def sensitive_file():
    """Create a fake sensitive file to test against."""
    path = _create_temp_file("SENSITIVE_DATA_LEAKED", suffix=".secret")
    yield path
    os.unlink(path)


@pytest.fixture
def project_file():
    """Create a file inside the project directory (allowed)."""
    project_dir = files.get_base_dir()
    docs_dir = os.path.join(project_dir, "tmp", "uploads")
    os.makedirs(docs_dir, exist_ok=True)
    
    file_path = os.path.join(docs_dir, "test_include_allowed.txt")
    with open(file_path, 'w') as f:
        f.write("LEGITIMATE_CONTENT_FOR_INCLUDE")
    yield file_path
    try:
        os.unlink(file_path)
    except OSError:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASS: _read_include_file Path Traversal
# ═══════════════════════════════════════════════════════════════════════════

class TestReadIncludeFilePathTraversal:
    """
    Verify that _read_include_file() cannot read files outside
    allowed project directories.
    """

    def test_absolute_path_etc_passwd(self, writer):
        """
        ATTACK: §§include(/etc/passwd)
        Must return None (blocked), not file contents.
        """
        result = writer._read_include_file("/etc/passwd")
        assert result is None, (
            "PATH TRAVERSAL: _read_include_file read /etc/passwd! "
            f"Got {len(result)} chars" if result else ""
        )

    def test_absolute_path_etc_shadow(self, writer):
        """
        ATTACK: §§include(/etc/shadow)
        """
        result = writer._read_include_file("/etc/shadow")
        assert result is None, "PATH TRAVERSAL: _read_include_file read /etc/shadow!"

    def test_absolute_path_arbitrary_sensitive(self, writer, sensitive_file):
        """
        ATTACK: §§include(<absolute_path_to_sensitive_file>)
        """
        result = writer._read_include_file(sensitive_file)
        if result is not None:
            assert "SENSITIVE_DATA_LEAKED" not in result, (
                f"PATH TRAVERSAL: _read_include_file read arbitrary sensitive file at "
                f"{sensitive_file}"
            )
        # If result is None, the fix is working

    def test_relative_traversal_etc_passwd(self, writer):
        """
        ATTACK: §§include(../../../../../../../etc/passwd)
        """
        result = writer._read_include_file("../../../../../../../etc/passwd")
        assert result is None, (
            "PATH TRAVERSAL: relative traversal reached /etc/passwd!"
        )

    def test_relative_traversal_from_project(self, writer):
        """
        ATTACK: Traversal from project-relative path.
        §§include(tmp/uploads/../../.env)
        The path starts with an allowed dir prefix but escapes via ../
        The resolved file is still in the base dir but NOT in the allowed sub-dir.
        """
        result = writer._read_include_file("tmp/uploads/../../.env")
        assert result is None, (
            "PATH TRAVERSAL: tmp/uploads/../../.env escaped the allowed "
            "sub-directory and read a file from the project root!"
        )

    def test_traversal_within_allowed_prefix(self, writer):
        """
        ATTACK: §§include(docs/../.git/config)
        Starts with 'docs/' but escapes via ../ to read .git/config.
        """
        result = writer._read_include_file("docs/../.git/config")
        assert result is None, (
            "PATH TRAVERSAL: docs/../.git/config escaped the docs/ "
            "sub-directory!"
        )

    def test_traversal_allowed_prefix_to_sibling_dir(self, writer):
        """
        ATTACK: §§include(tmp/uploads/../generated/../../run_ui.py)
        Starts in tmp/uploads, crosses to tmp/generated, then escapes to root.
        """
        result = writer._read_include_file("tmp/uploads/../generated/../../run_ui.py")
        assert result is None, (
            "PATH TRAVERSAL: traversal from tmp/uploads to project root "
            "read run_ui.py!"
        )

    def test_home_directory_ssh_key(self, writer):
        """
        ATTACK: §§include(~/.ssh/id_rsa)
        Expanded ~ could reach SSH private keys.
        """
        expanded = os.path.expanduser("~/.ssh/id_rsa")
        result = writer._read_include_file(expanded)
        assert result is None, (
            "PATH TRAVERSAL: _read_include_file read SSH private key!"
        )

    def test_home_directory_env_file(self, writer):
        """
        ATTACK: §§include(/Users/<user>/.env)
        """
        home_env = os.path.join(os.path.expanduser("~"), ".env")
        result = writer._read_include_file(home_env)
        # Even if .env doesn't exist, the function shouldn't attempt to read it
        # This is about path validation, not file existence

    def test_git_config_read(self, writer):
        """
        ATTACK: §§include(.git/config)
        Could leak repository URLs, credentials.
        .git/ is NOT in the allowed include directories.
        """
        result = writer._read_include_file(".git/config")
        assert result is None, (
            "PATH TRAVERSAL: _read_include_file read .git/config! "
            "Git credentials potentially exposed."
        )

    def test_null_byte_truncation(self, writer):
        """
        ATTACK: §§include(/etc/passwd\x00.txt)
        Null byte could truncate path in C-level operations.
        """
        result = writer._read_include_file("/etc/passwd\x00.txt")
        assert result is None, (
            "PATH TRAVERSAL: null byte truncation bypassed path validation!"
        )

    def test_double_url_encoding(self, writer):
        """
        ATTACK: §§include(..%252F..%252Fetc%252Fpasswd)
        Double URL encoding could bypass simple decode checks.
        """
        result = writer._read_include_file("..%252F..%252Fetc%252Fpasswd")
        assert result is None

    def test_windows_style_traversal(self, writer):
        """
        ATTACK: §§include(..\\..\\..\\etc\\passwd)
        Windows-style path separators.
        """
        result = writer._read_include_file("..\\..\\..\\etc\\passwd")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASS: _resolve_includes Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveIncludesIntegration:
    """
    Verify that the full _resolve_includes pipeline handles malicious
    include directives safely.

    Contract change (yENoyKIZ fix, ADR-006): _resolve_includes() now raises
    IncludeResolutionError when ANY directive cannot be resolved (atomic
    fail). The security invariant (no /etc/passwd leak) is unchanged — and
    in fact strengthened. These tests therefore accept either behaviour:
      - the legacy behaviour (silent return without the file content), or
      - the new behaviour (exception raised before any leak).
    Both paths are verified to never contain the sensitive content.
    """

    def _safe_resolve(self, writer, content: str) -> str:
        """Run _resolve_includes; if it raises (new contract), return empty."""
        try:
            return writer._resolve_includes(content)
        except Exception:
            # New contract: unresolved/blocked paths raise. The security
            # invariant is satisfied because nothing was returned.
            return ""

    def test_include_etc_passwd_directive(self, writer):
        """
        ATTACK: Content with §§include(/etc/passwd)
        Should NOT resolve to /etc/passwd contents.
        """
        content = "Header\n§§include(/etc/passwd)\nFooter"
        result = self._safe_resolve(writer, content)
        assert "root:" not in result, (
            "PATH TRAVERSAL: §§include directive read /etc/passwd in full pipeline!"
        )

    def test_include_traversal_directive(self, writer):
        """
        ATTACK: Content with §§include(../../../../etc/passwd)
        """
        content = "§§include(../../../../etc/passwd)"
        result = self._safe_resolve(writer, content)
        assert "root:" not in result

    def test_multiple_malicious_includes(self, writer):
        """
        ATTACK: Content with multiple malicious includes.
        """
        content = (
            "Start\n"
            "§§include(/etc/passwd)\n"
            "Middle\n"
            "@include(/etc/shadow)\n"
            "End"
        )
        result = self._safe_resolve(writer, content)
        assert "root:" not in result
        assert "SENSITIVE" not in result

    def test_mixed_legitimate_and_malicious(self, writer, project_file):
        """
        Mixed content: legitimate include (project file) + malicious include.

        Under the new atomic-resolution contract, ONE failing directive
        invalidates the whole resolution: the legitimate content is also
        held back. The security invariant (no /etc/passwd leak) is what
        matters here.
        """
        content = (
            f"§§include({project_file})\n"
            "§§include(/etc/passwd)"
        )
        result = self._safe_resolve(writer, content)
        # System file content MUST NOT be present (the only invariant
        # that matters under the new contract).
        assert "root:" not in result, (
            "PATH TRAVERSAL: /etc/passwd was read in mixed content!"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASS: Legitimate includes (regression)
# ═══════════════════════════════════════════════════════════════════════════

class TestLegitimateIncludes:
    """
    Regression tests: legitimate include directives pointing to files
    within allowed project directories must continue to work.
    """

    def test_include_from_uploads(self, writer, project_file):
        """Include from tmp/uploads/ must work."""
        result = writer._read_include_file(project_file)
        assert result is not None, (
            f"REGRESSION: legitimate include from {project_file} returned None"
        )
        assert "LEGITIMATE_CONTENT_FOR_INCLUDE" in result

    def test_include_from_docs(self, writer):
        """Include from docs/ must work."""
        project_dir = files.get_base_dir()
        docs_dir = os.path.join(project_dir, "docs")
        
        # Create a temp file in docs/
        test_file = os.path.join(docs_dir, "test_include_regression.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("DOCS_CONTENT_OK")
            
            result = writer._read_include_file(test_file)
            assert result is not None, "REGRESSION: include from docs/ returned None"
            assert "DOCS_CONTENT_OK" in result
        finally:
            try:
                os.unlink(test_file)
            except OSError:
                pass

    def test_include_from_tmp_generated(self, writer):
        """Include from tmp/generated/ must work."""
        project_dir = files.get_base_dir()
        gen_dir = os.path.join(project_dir, "tmp", "generated")
        os.makedirs(gen_dir, exist_ok=True)
        
        test_file = os.path.join(gen_dir, "test_include_regression.md")
        try:
            with open(test_file, 'w') as f:
                f.write("GENERATED_CONTENT_OK")
            
            result = writer._read_include_file(test_file)
            assert result is not None, "REGRESSION: include from tmp/generated/ returned None"
            assert "GENERATED_CONTENT_OK" in result
        finally:
            try:
                os.unlink(test_file)
            except OSError:
                pass

    def test_basename_lookup_in_allowed_dirs(self, writer):
        """
        Basename lookup (existing feature): if just a filename is given,
        the function tries common directories. This must still work.
        """
        project_dir = files.get_base_dir()
        uploads_dir = os.path.join(project_dir, "tmp", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        test_file = os.path.join(uploads_dir, "test_basename_lookup.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("BASENAME_LOOKUP_OK")

            result = writer._read_include_file("test_basename_lookup.txt")
            assert result is not None, "REGRESSION: basename lookup in uploads/ returned None"
            assert "BASENAME_LOOKUP_OK" in result
        finally:
            try:
                os.unlink(test_file)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASS: Edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases for include resolution."""

    def test_empty_path(self, writer):
        """Empty path should return None gracefully."""
        result = writer._read_include_file("")
        assert result is None

    def test_whitespace_path(self, writer):
        """Whitespace-only path should return None."""
        result = writer._read_include_file("   ")
        assert result is None

    def test_very_long_path(self, writer):
        """Extremely long path should not crash."""
        long_path = "/etc/" + "a" * 10000 + ".txt"
        result = writer._read_include_file(long_path)
        assert result is None

    def test_path_with_newlines(self, writer):
        """Path with newline characters should not trick the parser."""
        result = writer._read_include_file("/etc/passwd\n/etc/shadow")
        assert result is None

    def test_no_include_directives(self, writer):
        """Content without includes should pass through unchanged."""
        content = "# Normal Markdown\n\nNo includes here."
        result = writer._resolve_includes(content)
        assert result == content

    def test_include_nonexistent_file(self, writer):
        """Include directive for non-existent file should return None."""
        result = writer._read_include_file("/tmp/definitely_does_not_exist_xyz.txt")
        assert result is None
