"""
Format / quality tests for the agent-actionable error message produced when
FileWriter._resolve_includes raises IncludeResolutionError.

Invariant under test:
  I-5 — The error message returned to the agent must be actionable: it must
        cite the requested path(s) verbatim, list ALLOWED_INCLUDE_DIRS, give a
        concrete corrective action, and never leak a Python traceback or
        internal filesystem details beyond the allowed directory names.

These tests assume Iter 1 GREEN (i.e. _format_include_error is implemented).
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("whisper", types.ModuleType("whisper"))

from python.tools.file_writer import FileWriter, IncludeResolutionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _writer() -> FileWriter:
    w = FileWriter.__new__(FileWriter)
    w.agent = MagicMock()
    w.agent.context = SimpleNamespace(workspace=None, username=None)
    w.args = {}
    w.message = ""
    w.name = "file_writer"
    return w


# ═══════════════════════════════════════════════════════════════════════════
# T9 — Each requested path appears verbatim in the error message.
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorMessageContent:
    def test_T9_cites_each_requested_path(self):
        paths = [
            "/app/tmp/korev_dossier_content.md",
            "missing_under_uploads.md",
            "deeply/nested/file.txt",
        ]
        err = IncludeResolutionError(paths)
        msg = _writer()._format_include_error(err)
        for p in paths:
            assert p in msg, f"Path {p!r} missing from error message:\n{msg}"

    def test_T10_lists_each_allowed_dir(self):
        err = IncludeResolutionError(["x"])
        msg = _writer()._format_include_error(err)
        for d in FileWriter.ALLOWED_INCLUDE_DIRS:
            assert d in msg, f"Allowed dir {d!r} missing from error message:\n{msg}"

    def test_T11_states_corrective_action(self):
        """The message must propose at least one concrete remediation."""
        err = IncludeResolutionError(["x"])
        msg = _writer()._format_include_error(err).lower()
        assert (
            "corrective action" in msg
            or "remediation" in msg
            or "move" in msg
            or "inline" in msg
        ), msg
        assert "inline" in msg or "content" in msg, (
            "The 'pass content inline' alternative MUST be mentioned: "
            "without it the agent has no escape hatch when the file path is wrong "
            f"in the model's view of the world. Got:\n{msg}"
        )

    def test_T12_no_python_traceback_or_internals_leak(self):
        """
        The message must NOT contain Python traceback metadata or absolute
        filesystem paths to internals (only ALLOWED_INCLUDE_DIRS names allowed).
        """
        err = IncludeResolutionError(["foo.md"])
        msg = _writer()._format_include_error(err)
        forbidden = [
            "Traceback",
            "File \"",
            "site-packages",
            "/Users/",
            ".venv/",
            "_resolve_includes",
        ]
        for token in forbidden:
            assert token not in msg, (
                f"Internals leak in error message: {token!r} present.\n{msg}"
            )

    def test_T13_snapshot_format_is_stable(self):
        """
        Snapshot test (cf. plan §3.2 / H-13). Hard-coded reference.

        Updating this snapshot REQUIRES:
          1. Updating _format_include_error
          2. Updating this expected string
          3. Reviewing in PR (not auto-update).
        """
        err = IncludeResolutionError([
            "missing_one.md",
            "nested/missing_two.txt",
        ])
        msg = _writer()._format_include_error(err)

        expected = (
            "❌ FileWriter aborted: include directive(s) could not be resolved.\n"
            "\n"
            "Failed paths (2):\n"
            "  • missing_one.md\n"
            "  • nested/missing_two.txt\n"
            "\n"
            "Allowed include directories (relative to project root):\n"
            "  • tmp/uploads\n"
            "  • tmp/generated\n"
            "  • docs\n"
            "  • work_dir\n"
            "\n"
            "Corrective action:\n"
            "  - Move the referenced file(s) into one of the allowed "
            "directories above, OR\n"
            "  - Pass the full file content inline as the `content` argument "
            "instead of using a §§include(...) directive.\n"
            "\n"
            "No artefact was written. Please retry with a corrected payload."
        )

        assert msg == expected, (
            "SNAPSHOT MISMATCH — _format_include_error output changed.\n"
            "If this is intentional, update the expected string in this test.\n"
            f"Expected:\n{expected!r}\n\n"
            f"Got:\n{msg!r}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# T9bis — Edge cases on format
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorMessageEdgeCases:
    def test_single_path_format_grammatically_clean(self):
        """One path → 'Failed paths (1)' header is acceptable."""
        err = IncludeResolutionError(["only_one.md"])
        msg = _writer()._format_include_error(err)
        assert "Failed paths (1)" in msg
        assert "only_one.md" in msg

    def test_empty_list_does_not_crash(self):
        """Defensive: an empty list (caller error) should still format cleanly."""
        err = IncludeResolutionError([])
        msg = _writer()._format_include_error(err)
        assert "Failed paths (0)" in msg
        assert "❌" in msg or "aborted" in msg.lower()

    def test_many_paths_does_not_truncate(self):
        """20 paths should all appear (no silent truncation)."""
        paths = [f"file_{i:02d}.md" for i in range(20)]
        err = IncludeResolutionError(paths)
        msg = _writer()._format_include_error(err)
        for p in paths:
            assert p in msg
        assert "Failed paths (20)" in msg

    def test_path_with_special_chars_preserved_verbatim(self):
        """Spaces, parens, unicode in the path must be preserved verbatim."""
        weird = "weird path/With (parens) and ünicödé.md"
        err = IncludeResolutionError([weird])
        msg = _writer()._format_include_error(err)
        assert weird in msg
