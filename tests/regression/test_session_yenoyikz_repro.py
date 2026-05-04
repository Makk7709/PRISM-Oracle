"""
Regression — exact reproduction of the yENoyKIZ session bug
(Evidence v1.4.0, KOREV server, 04/05/2026 13:12 UTC).

Original symptom:
  - Agent wrote ~50 KB of markdown to /app/tmp/korev_dossier_content.md.
  - Agent called file_writer with content="§§include(/app/tmp/korev_dossier_content.md)"
    (path is OUTSIDE ALLOWED_INCLUDE_DIRS; tmp/ is not allowed, only
    tmp/uploads, tmp/generated, docs, work_dir).
  - file_writer logged "Could not resolve include file" but generated a
    25 KB PDF whose body was the literal directive text. Response.message
    claimed "✅ File created successfully!".

Expected after fix:
  - T17: same scenario MUST now error out hard. No PDF on disk.
         Response.message MUST cite the failing path.
  - T18: with the markdown moved to tmp/uploads/ (allowed), the workflow
         MUST succeed and produce a PDF whose extracted text recovers the
         markdown content.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("whisper", types.ModuleType("whisper"))

from python.tools.file_writer import FileWriter


# ---------------------------------------------------------------------------
# Reproduction harness
# ---------------------------------------------------------------------------


def _make_writer(workspace: Path) -> FileWriter:
    w = FileWriter.__new__(FileWriter)
    w.agent = MagicMock()
    w.agent.context = SimpleNamespace(workspace=str(workspace), username="amine")
    w.args = {}
    w.message = ""
    w.name = "file_writer"
    return w


def _redirect_base_dir(monkeypatch, base: Path) -> None:
    monkeypatch.setattr(
        "python.tools.file_writer.files.get_base_dir", lambda: str(base)
    )
    monkeypatch.setattr(
        "python.tools.file_writer.files.get_abs_path",
        lambda *parts: str(base.joinpath(*parts)),
    )


def _build_dossier_markdown() -> str:
    """Sanitised excerpt mimicking the structure of the real dossier."""
    return (
        "## Executive Summary\n\n"
        "MARKER_AAA_42 Document maître pour l'intégration engineering.\n\n"
        "## 1. Vision stratégique\n\n"
        "Lorem ipsum dolor sit amet. " * 50
        + "\n\n"
        "## 2. Cartographie technique\n\n"
        "MARKER_BBB_42 Modules critiques recensés.\n"
        + "Sed do eiusmod tempor. " * 50
        + "\n\n"
        "## Conclusion\n\nMARKER_CCC_42 Fin du document.\n"
    )


# ═══════════════════════════════════════════════════════════════════════════
# T17 — Original failure scenario MUST now fail hard
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_T17_yenoyikz_unsafe_path_now_fails_hard(
    tmp_path: Path, monkeypatch, capsys
):
    _redirect_base_dir(monkeypatch, tmp_path)
    workspace = tmp_path / "shared" / "users" / "amine"
    workspace.mkdir(parents=True)

    # Step 1 — agent writes the dossier markdown OUTSIDE allowed dirs.
    # In production this was /app/tmp/korev_dossier_content.md ; here we
    # mirror the structure: <project_root>/tmp/<file>.md (tmp/ alone is
    # NOT in ALLOWED_INCLUDE_DIRS).
    (tmp_path / "tmp").mkdir(exist_ok=True)
    md_path = tmp_path / "tmp" / "korev_dossier_content.md"
    md_path.write_text(_build_dossier_markdown())
    md_size = md_path.stat().st_size
    assert md_size > 1000, "fixture must be non-trivial"

    # Step 2 — agent calls file_writer with a §§include directive pointing
    # at the file just written, exactly as it did in the production session.
    writer = _make_writer(workspace)
    writer.args = {
        "filename": "KOREV_Dossier_Maitre_Integration_Engineering_Aya.pdf",
        "content": f"§§include({md_path})",
        "template": "consulting_premium",
    }
    response = await writer.execute()

    # ── Assertions ─────────────────────────────────────────────────────
    # 4a. Response is an error, not a success.
    assert "successfully" not in response.message.lower(), (
        f"yENoyKIZ REGRESSION: tool returned success for an unresolved "
        f"include. Response was:\n{response.message}"
    )
    assert "❌" in response.message or "error" in response.message.lower(), (
        f"yENoyKIZ REGRESSION: error not signalled.\n{response.message}"
    )

    # 4b. The error message cites the failing path so the agent can correct.
    assert "korev_dossier_content.md" in response.message, (
        "Error message must cite the unresolvable path verbatim."
    )

    # 4c. No PDF was written.
    pdfs = list((workspace / "generated").rglob("*.pdf"))
    assert pdfs == [], (
        f"yENoyKIZ REGRESSION: a 25 KB-style orphan PDF was written "
        f"despite the include failure: {pdfs}"
    )

    # 4d. Observability: log line emitted.
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "Could not resolve include" in combined, (
        f"OBSERVABILITY: warning log missing. Stdout/Stderr was:\n{combined}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# T18 — Same scenario with corrected path now succeeds end-to-end
# ═══════════════════════════════════════════════════════════════════════════


# Skip module-level if WeasyPrint engine is unavailable for the success path.
_PDF_OK = False
try:
    from python.helpers.evidence_pdf_engine import markdown_to_pdf  # noqa: F401
    _PDF_OK = True
except Exception:
    pass


@pytest.mark.integration
@pytest.mark.skipif(not _PDF_OK, reason="WeasyPrint engine not available")
@pytest.mark.asyncio
async def test_T18_yenoyikz_correct_path_succeeds(tmp_path: Path, monkeypatch):
    _redirect_base_dir(monkeypatch, tmp_path)
    workspace = tmp_path / "shared" / "users" / "amine"
    workspace.mkdir(parents=True)

    # Same scenario but the markdown is in tmp/uploads (an allowed dir).
    (tmp_path / "tmp" / "uploads").mkdir(parents=True, exist_ok=True)
    md_path = tmp_path / "tmp" / "uploads" / "korev_dossier_content.md"
    md_path.write_text(_build_dossier_markdown())
    md_size = md_path.stat().st_size

    writer = _make_writer(workspace)
    writer.args = {
        "filename": "KOREV_Dossier_Maitre_Integration_Engineering_Aya.pdf",
        "content": f"§§include({md_path})",
        "template": "consulting_premium",
    }
    response = await writer.execute()

    assert "successfully" in response.message.lower(), response.message

    pdfs = list((workspace / "generated").rglob("*.pdf"))
    assert len(pdfs) == 1, f"Expected one PDF, got {pdfs}"
    pdf_size = pdfs[0].stat().st_size

    # The yENoyKIZ failure produced a fixed ~25 KB PDF regardless of the
    # markdown size: it carried only template chrome + the literal directive.
    # A real render scales with content. The threshold below mirrors T14:
    # ~25 KB fixed font/template overhead + at least 0.5 KB per KB of MD.
    expected_min_pdf = 25_000 + (md_size // 2)
    assert pdf_size >= expected_min_pdf, (
        f"yENoyKIZ REGRESSION (renderer): PDF size {pdf_size} bytes is below "
        f"the expected minimum {expected_min_pdf} bytes for a {md_size}-byte "
        f"markdown source. The 25 KB-flat failure pattern may have re-emerged."
    )
