"""
Security / Integrity Tests — FileWriter MUST fail hard on unresolved includes.

Context (incident KOREV Evidence — session yENoyKIZ, 04/05/2026 13:12 UTC):
The agent passed `§§include(/app/tmp/korev_dossier_content.md)` to file_writer
because the markdown source had been written outside ALLOWED_INCLUDE_DIRS.
The directive could NOT be resolved, but file_writer continued silently and
generated a 25 KB PDF whose content was the literal directive text instead of
the 50 KB engineering dossier the user expected. Response.message claimed
"✅ File created successfully!" — a structural lie.

Invariants under test (cf. plan de correction §1):
  I-1 : No artefact must ever be written if any §§include(...) directive
        could not be resolved.
  I-2 : No unresolved §§include(...) directive must ever appear in the final
        rendered output.
  I-4 : Response.message must reflect filesystem state exactly (no apparent
        success masking partial failure).

These tests MUST FAIL on the current code (RED phase) and PASS after the
fix is implemented (GREEN phase).

Anti-simplification rules (cf. plan §2.1):
  - No mocking of the filesystem. Tests read the actual disk state.
  - Each test verifies BOTH Response.message AND filesystem state.
  - Each test is independent: own fixtures, own cleanup, no shared state.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("whisper", types.ModuleType("whisper"))

from python.tools.file_writer import FileWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_writer(*, workspace: str | None, username: str | None, args: dict) -> FileWriter:
    """Construct a FileWriter without going through __init__ (which expects an Agent)."""
    writer = FileWriter.__new__(FileWriter)
    writer.agent = MagicMock()
    writer.agent.context = SimpleNamespace(workspace=workspace, username=username)
    writer.args = args
    writer.message = ""
    writer.name = "file_writer"
    return writer


def _redirect_base_dir(monkeypatch, base: Path) -> None:
    """
    Make `files.get_base_dir()` and `files.get_abs_path()` return paths under `base`.

    This lets us run tests in an isolated tmp directory without writing into
    the real project root.
    """

    def _fake_get_base_dir():
        return str(base)

    def _fake_get_abs_path(*parts):
        return str(base.joinpath(*parts))

    monkeypatch.setattr("python.tools.file_writer.files.get_base_dir", _fake_get_base_dir)
    monkeypatch.setattr("python.tools.file_writer.files.get_abs_path", _fake_get_abs_path)


def _setup_workspace(base: Path) -> Path:
    """Create the project skeleton: tmp/, tmp/uploads/, tmp/generated/, docs/, work_dir/."""
    for sub in ("tmp", "tmp/uploads", "tmp/generated", "docs", "work_dir"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch) -> Path:
    """Create an isolated project root and redirect file_writer to use it."""
    root = _setup_workspace(tmp_path)
    _redirect_base_dir(monkeypatch, root)
    return root


@pytest.fixture
def user_workspace(project_root: Path) -> Path:
    """Pre-create the per-user workspace where generated files land."""
    ws = project_root / "shared" / "users" / "amine"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "generated").mkdir(parents=True, exist_ok=True)
    return ws


def _writer_for(user_workspace: Path, args: dict) -> FileWriter:
    return _make_writer(workspace=str(user_workspace), username="amine", args=args)


def _list_generated(user_workspace: Path) -> list[Path]:
    """Return all files inside <workspace>/generated (whatever subdir)."""
    gen_dir = user_workspace / "generated"
    if not gen_dir.exists():
        return []
    return [p for p in gen_dir.rglob("*") if p.is_file()]


# ═══════════════════════════════════════════════════════════════════════════
# T1-T8 : Execute() MUST fail hard on unresolved include directives.
# ═══════════════════════════════════════════════════════════════════════════


class TestExecuteFailsOnUnresolvedInclude:
    """
    Invariant I-1: when a directive cannot be resolved, NO artefact must
    be written and the Response must clearly indicate an error.
    """

    @pytest.mark.asyncio
    async def test_T1_single_unresolved_include_fails(self, user_workspace: Path):
        """T1 — Single directive pointing to a non-existent file: MUST error.

        REPRO: the exact pattern of the yENoyKIZ session — the agent passes a
        directive but the target file is nowhere to be found.
        """
        writer = _writer_for(
            user_workspace,
            args={
                "filename": "out.pdf",
                "content": "§§include(does_not_exist.md)",
                "template": "consulting_premium",
            },
        )

        response = await writer.execute()

        assert "successfully" not in response.message.lower(), (
            f"FAIL-LOUD VIOLATION: tool returned a success message for an "
            f"unresolved include. Response was:\n{response.message}"
        )
        assert "error" in response.message.lower() or "❌" in response.message, (
            f"FAIL-LOUD VIOLATION: error not signalled in Response.message:\n"
            f"{response.message}"
        )
        assert "include" in response.message.lower(), (
            "Error message should mention the include directive that failed."
        )
        assert _list_generated(user_workspace) == [], (
            f"ATOMICITY VIOLATION: artefacts were written despite the include "
            f"failure: {_list_generated(user_workspace)}"
        )

    @pytest.mark.asyncio
    async def test_T2_multiple_unresolved_includes_fails(self, user_workspace: Path):
        """T2 — Multiple unresolved directives: MUST error and mention each path."""
        writer = _writer_for(
            user_workspace,
            args={
                "filename": "out.pdf",
                "content": (
                    "§§include(does_not_exist_one.md)\n"
                    "Some narrative.\n"
                    "@include(also_missing.md)\n"
                    "More narrative."
                ),
            },
        )

        response = await writer.execute()

        assert "successfully" not in response.message.lower()
        assert "does_not_exist_one.md" in response.message, (
            "Error must cite each unresolved path so the agent can self-correct. "
            f"Message:\n{response.message}"
        )
        assert "also_missing.md" in response.message, (
            "Error must cite each unresolved path so the agent can self-correct. "
            f"Message:\n{response.message}"
        )
        assert _list_generated(user_workspace) == []

    @pytest.mark.asyncio
    async def test_T3_mixed_resolved_and_unresolved_is_atomic(
        self, project_root: Path, user_workspace: Path
    ):
        """T3 — Atomicity: if ANY directive fails, NOTHING is written, even if some directives resolve.

        Anti-simplification: a naive fix that resolves the valid ones and silently
        drops the invalid ones would PASS T1 and T2 but FAIL T3.
        """
        ok_md = project_root / "tmp" / "uploads" / "ok.md"
        ok_md.write_text("RESOLVED_OK_CONTENT")

        writer = _writer_for(
            user_workspace,
            args={
                "filename": "out.pdf",
                "content": (
                    f"§§include({ok_md})\n"
                    "§§include(missing_file.md)"
                ),
            },
        )

        response = await writer.execute()

        assert "successfully" not in response.message.lower()
        assert "missing_file.md" in response.message
        assert _list_generated(user_workspace) == [], (
            "ATOMICITY VIOLATION: a partial PDF was written when one include failed."
        )

    @pytest.mark.asyncio
    async def test_T4_resolved_only_succeeds(self, project_root: Path, user_workspace: Path):
        """T4 — Happy path: all directives resolve → success + content embedded."""
        a = project_root / "tmp" / "uploads" / "a.md"
        b = project_root / "tmp" / "uploads" / "b.md"
        a.write_text("# Section A\n\nMARKER_AAA_42 content for section A.")
        b.write_text("# Section B\n\nMARKER_BBB_42 content for section B.")

        writer = _writer_for(
            user_workspace,
            args={
                "filename": "report.txt",
                "content": f"§§include({a})\n\n§§include({b})",
                "format": "txt",
            },
        )

        response = await writer.execute()

        assert "successfully" in response.message.lower(), response.message
        artefacts = _list_generated(user_workspace)
        assert len(artefacts) == 1, f"Expected exactly one artefact, got {artefacts}"
        produced = artefacts[0].read_text()
        assert "MARKER_AAA_42" in produced
        assert "MARKER_BBB_42" in produced
        assert "§§include" not in produced, (
            "I-2 VIOLATION: the directive leaked into the rendered output."
        )

    @pytest.mark.asyncio
    async def test_T5_no_includes_succeeds(self, user_workspace: Path):
        """T5 — Sanity: plain content without any include directive renders normally."""
        writer = _writer_for(
            user_workspace,
            args={
                "filename": "plain.txt",
                "content": "# Plain content\n\nThis has no directives at all.",
                "format": "txt",
            },
        )

        response = await writer.execute()

        assert "successfully" in response.message.lower(), response.message
        artefacts = _list_generated(user_workspace)
        assert len(artefacts) == 1
        assert "Plain content" in artefacts[0].read_text()

    @pytest.mark.asyncio
    async def test_T6_unresolved_include_leaves_no_pdf_on_disk(
        self, user_workspace: Path
    ):
        """T6 — Explicit no-orphan-PDF check (covers the actual yENoyKIZ symptom)."""
        writer = _writer_for(
            user_workspace,
            args={
                "filename": "KOREV_Dossier.pdf",
                "content": "§§include(/abs/path/to/missing/dossier.md)",
                "template": "consulting_premium",
            },
        )

        await writer.execute()

        pdfs = [p for p in _list_generated(user_workspace) if p.suffix == ".pdf"]
        assert pdfs == [], (
            f"YENOYKIZ REGRESSION: an orphan PDF was written despite include failure: "
            f"{pdfs}"
        )

    @pytest.mark.asyncio
    async def test_T7_unresolved_include_leaves_no_orphan_artefact(
        self, project_root: Path, user_workspace: Path
    ):
        """T7 — No orphan tempfile, no .write_test residue, no half-written file."""
        writer = _writer_for(
            user_workspace,
            args={
                "filename": "thing.pdf",
                "content": "§§include(missing.md)",
            },
        )

        before = sorted(p.name for p in _list_generated(user_workspace))
        await writer.execute()
        after = sorted(p.name for p in _list_generated(user_workspace))

        assert before == after, (
            f"ORPHAN VIOLATION: filesystem changed inside generated/ "
            f"despite the include failure. Before={before} After={after}"
        )

    @pytest.mark.asyncio
    async def test_T8_unresolved_include_logs_warning(
        self, user_workspace: Path, capsys
    ):
        """T8 — Observability: a warning log line MUST be emitted on failure.

        We check stdout because PrintStyle writes to stdout.
        """
        writer = _writer_for(
            user_workspace,
            args={
                "filename": "x.pdf",
                "content": "§§include(missing_for_log_test.md)",
            },
        )

        await writer.execute()

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "Could not resolve include" in combined or "could not resolve" in combined.lower(), (
            f"OBSERVABILITY: the failure must produce a log line containing "
            f"'Could not resolve include'. Stdout/Stderr was:\n{combined}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# T19 — Atomicity at the _resolve_includes level (H-4 mitigation)
# ═══════════════════════════════════════════════════════════════════════════


class TestResolveIncludesAtomicity:
    """
    Direct tests on _resolve_includes() to lock the all-or-nothing contract.

    H-4 in the plan: ensure resolution happens BEFORE any output file is
    opened, so we can never end up with a half-written PDF on disk. These
    tests verify the atomicity at the resolution layer itself.
    """

    @staticmethod
    def _bare_writer():
        from python.tools.file_writer import FileWriter

        w = FileWriter.__new__(FileWriter)
        w.agent = MagicMock()
        w.agent.context = SimpleNamespace(workspace=None, username=None)
        w.args = {}
        w.message = ""
        w.name = "file_writer"
        return w

    def test_T19_no_substitution_when_any_include_fails(
        self, project_root: Path
    ):
        """When ONE include resolves and ANOTHER fails, the call MUST raise
        and NOTHING about the resolved one should leak to a partial result."""
        from python.tools.file_writer import IncludeResolutionError

        ok_md = project_root / "tmp" / "uploads" / "ok.md"
        ok_md.write_text("RESOLVED_FIRST")

        writer = self._bare_writer()
        content = (
            f"§§include({ok_md})\n"
            "§§include(missing_atomic.md)"
        )
        with pytest.raises(IncludeResolutionError) as exc_info:
            writer._resolve_includes(content)
        assert "missing_atomic.md" in exc_info.value.unresolved_paths
        # The resolved one must NOT be in the unresolved list.
        assert all("ok.md" not in p for p in exc_info.value.unresolved_paths)

    def test_T20_unresolved_paths_are_reported_in_order(
        self, project_root: Path
    ):
        """Caller-actionable: failing paths reported in the order encountered."""
        from python.tools.file_writer import IncludeResolutionError

        writer = self._bare_writer()
        content = (
            "§§include(first_missing.md)\n"
            "Some prose.\n"
            "§§include(second_missing.md)\n"
            "@include(third_missing.md)"
        )
        with pytest.raises(IncludeResolutionError) as exc_info:
            writer._resolve_includes(content)
        assert exc_info.value.unresolved_paths == [
            "first_missing.md",
            "second_missing.md",
            "third_missing.md",
        ]


# ═══════════════════════════════════════════════════════════════════════════
# T25-T28 — Edge cases (anti-simplification)
# ═══════════════════════════════════════════════════════════════════════════


class TestIncludeEdgeCases:
    @pytest.mark.asyncio
    async def test_T25_multiple_identical_includes_all_resolve(
        self, project_root: Path, user_workspace: Path
    ):
        """Same file referenced 3 times: each occurrence must be substituted.

        Naive implementations using a dict keyed by path would substitute only
        once. The implementation iterates over `matches`, so each occurrence
        is independently substituted.
        """
        f = project_root / "tmp" / "uploads" / "repeated.md"
        f.write_text("MARKER_REPEAT")

        writer = _writer_for(
            user_workspace,
            args={
                "filename": "rep.txt",
                "content": (
                    f"§§include({f}) | §§include({f}) | §§include({f})"
                ),
                "format": "txt",
            },
        )
        response = await writer.execute()
        assert "successfully" in response.message.lower(), response.message
        produced = next(iter(_list_generated(user_workspace))).read_text()
        assert produced.count("MARKER_REPEAT") == 3, (
            f"Expected 3 substitutions, got {produced.count('MARKER_REPEAT')}.\n"
            f"Content was:\n{produced}"
        )
        assert "§§include" not in produced

    @pytest.mark.asyncio
    async def test_T26_non_utf8_include_target_fails_hard(
        self, project_root: Path, user_workspace: Path
    ):
        """A binary / non-UTF-8 file in an allowed dir must NOT crash the
        process and must NOT silently ship a corrupted document. It must
        either decode cleanly or fail hard like any unresolved include.
        """
        binary = project_root / "tmp" / "uploads" / "binary.bin"
        binary.write_bytes(b"\xff\xfe\x00\x01\x02non-utf8\x80\xa0")

        writer = _writer_for(
            user_workspace,
            args={
                "filename": "x.txt",
                "content": f"§§include({binary})",
                "format": "txt",
            },
        )
        response = await writer.execute()
        # No artefact should be produced if the file cannot be read as text.
        assert "successfully" not in response.message.lower(), (
            "non-UTF-8 include must not produce a success — got:\n"
            f"{response.message}"
        )
        assert _list_generated(user_workspace) == []

    @pytest.mark.asyncio
    async def test_T27_many_valid_includes_resolve_quickly(
        self, project_root: Path, user_workspace: Path
    ):
        """25 valid includes must resolve in well under 5 seconds."""
        import time

        for i in range(25):
            (project_root / "tmp" / "uploads" / f"part_{i:02d}.md").write_text(
                f"PART_{i:02d}_OK\n"
            )
        directives = "\n".join(
            f"§§include(part_{i:02d}.md)" for i in range(25)
        )
        writer = _writer_for(
            user_workspace,
            args={
                "filename": "many.txt",
                "content": directives,
                "format": "txt",
            },
        )
        t0 = time.monotonic()
        response = await writer.execute()
        elapsed = time.monotonic() - t0
        assert elapsed < 5.0, f"too slow: {elapsed:.2f}s for 25 includes"
        assert "successfully" in response.message.lower()

        produced = next(iter(_list_generated(user_workspace))).read_text()
        for i in range(25):
            assert f"PART_{i:02d}_OK" in produced, f"part {i:02d} missing"
        assert "§§include" not in produced

    @pytest.mark.asyncio
    async def test_T28_one_megabyte_include_safely_resolves(
        self, project_root: Path, user_workspace: Path
    ):
        """A 1 MB include must succeed without OOM. Beyond that we accept
        either success or hard failure but never silent corruption."""
        big = project_root / "tmp" / "uploads" / "big.md"
        big.write_text("BIG_MARKER " * 100_000)  # ~1.1 MB
        assert big.stat().st_size > 1_000_000

        writer = _writer_for(
            user_workspace,
            args={
                "filename": "big.txt",
                "content": f"§§include({big})",
                "format": "txt",
            },
        )
        response = await writer.execute()
        if "successfully" in response.message.lower():
            produced = next(iter(_list_generated(user_workspace))).read_text()
            assert "BIG_MARKER" in produced
            assert len(produced) > 900_000
        else:
            # Acceptable: a deliberate cap was hit. Must NOT corrupt silently.
            assert _list_generated(user_workspace) == []
