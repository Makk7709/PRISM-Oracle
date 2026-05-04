"""
End-to-end integrity tests for the FileWriter → WeasyPrint PDF pipeline.

These tests run the REAL PDF engine (no mock) to verify that the output PDF
faithfully encodes the input markdown — i.e. that the rendered file is not
silently truncated, replaced by a placeholder, or stripped of structure.

This is the regression net for the yENoyKIZ incident at the integration
layer: even if Iter 1 (fail-hard on unresolved includes) and Iter 2
(actionable error message) pass, a future bug in the rendering chain could
re-introduce a similar "structural lie" — a small PDF claimed as a complete
deliverable. These tests guarantee the symptom would surface immediately.

All tests are marked `@pytest.mark.integration` and `@pytest.mark.slow` so
they can be excluded from the fast gate. They are MANDATORY for merge.
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


# ---------------------------------------------------------------------------
# Skip the whole module if WeasyPrint stack is unavailable.
# ---------------------------------------------------------------------------

_PDF_ENGINE_OK = False
_PDF_SKIP_REASON = ""
try:
    from python.helpers.evidence_pdf_engine import markdown_to_pdf  # noqa: F401
    _PDF_ENGINE_OK = True
except Exception as _exc:  # pragma: no cover
    _PDF_SKIP_REASON = f"WeasyPrint / evidence_pdf_engine unavailable: {_exc!r}"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not _PDF_ENGINE_OK,
        reason=_PDF_SKIP_REASON or "PDF engine not available",
    ),
]


from python.tools.file_writer import FileWriter


# ---------------------------------------------------------------------------
# Helpers
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


def _build_markdown(target_size_kb: int) -> str:
    """
    Build a realistic markdown payload of approx target_size_kb that includes:
      - Multiple H2 sections
      - Recognisable markers MARKER_AAA_42, MARKER_BBB_42, MARKER_CCC_42
      - Mixed prose + bullet lists (so the rendering exercises real CSS rules)
    """
    sections = []
    sections.append("## Executive Summary\n")
    sections.append(
        "MARKER_AAA_42 — Document de référence pour la validation du pipeline "
        "de génération de PDF. Ce paragraphe doit apparaître intégralement dans "
        "le rendu final.\n"
    )
    para = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 20
    n = 0
    while sum(len(s) for s in sections) < target_size_kb * 1024:
        n += 1
        sections.append(f"\n## Section {n} — Analyse approfondie\n")
        sections.append(f"MARKER_BBB_42_section_{n} contenu textuel principal.\n")
        sections.append(para)
        sections.append("\n- premier élément\n- deuxième élément\n- troisième élément\n")
    sections.append("\n## Conclusion\n\nMARKER_CCC_42 fin du document.\n")
    return "".join(sections)


def _extract_pdf_text(pdf_path: Path) -> str:
    """Best-effort PDF text extraction. Tries pdftotext (CLI), then pypdf."""
    import shutil
    import subprocess

    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        try:
            out = subprocess.run(
                [pdftotext, "-layout", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if out.returncode == 0:
                return out.stdout
        except Exception:
            pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# T14 — PDF size must be proportional to markdown content
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_T14_pdf_size_proportional_to_content(tmp_path: Path, monkeypatch):
    """
    A 30+ KB markdown should produce a PDF whose extracted text recovers
    at least ~50% of the source character count.

    Reference data (production PDFs from 28/04/2026):
      - 150 KB markdown → ~700 KB PDF, ~75 KB extracted text  (ratio ~50%)
      - 100 KB markdown → ~490 KB PDF, ~55 KB extracted text
    For the yENoyKIZ failure, the ratio was 0.7%  — orders of magnitude off.
    """
    _redirect_base_dir(monkeypatch, tmp_path)
    workspace = tmp_path / "shared" / "users" / "amine"
    workspace.mkdir(parents=True)
    markdown = _build_markdown(target_size_kb=30)
    md_size = len(markdown)
    assert md_size >= 30 * 1024, "fixture too small to be representative"

    writer = _make_writer(workspace)
    writer.args = {
        "filename": "integrity_test.pdf",
        "content": markdown,
        "template": "consulting_premium",
        "title": "Integration test",
    }

    response = await writer.execute()
    assert "successfully" in response.message.lower(), response.message

    pdfs = list((workspace / "generated").glob("*.pdf"))
    assert len(pdfs) == 1, f"Expected 1 PDF, got {pdfs}"
    pdf = pdfs[0]
    pdf_size = pdf.stat().st_size

    extracted = _extract_pdf_text(pdf)
    extracted_size = len(extracted)

    # The yENoyKIZ symptom: a 50 KB markdown produced a 25 KB PDF with
    # only 171 chars of extracted text. The ratio there was 0.34%.
    # We require AT LEAST 30% recovery, well above the failure mode but
    # tolerant to real CSS / page-break / header / footer overhead.
    recovery_ratio = extracted_size / md_size if md_size else 0.0
    assert recovery_ratio >= 0.30, (
        f"PDF text recovery too low: {extracted_size}/{md_size} = {recovery_ratio:.1%}.\n"
        f"This is the yENoyKIZ failure pattern (structural truncation).\n"
        f"PDF size: {pdf_size} bytes, MD size: {md_size} bytes."
    )

    # Sanity: PDF should not be ridiculously small relative to markdown.
    # ~25 KB fixed overhead (fonts) + at least 0.5 KB of real bytes per KB of MD.
    expected_min_pdf = 20_000 + (md_size // 2)
    assert pdf_size >= expected_min_pdf, (
        f"PDF size suspiciously small: {pdf_size} bytes for {md_size} bytes of MD. "
        f"Expected >= {expected_min_pdf}."
    )


# ═══════════════════════════════════════════════════════════════════════════
# T15 — Unique markers from source must survive into the PDF text layer
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_T15_pdf_contains_source_markers(tmp_path: Path, monkeypatch):
    _redirect_base_dir(monkeypatch, tmp_path)
    workspace = tmp_path / "shared" / "users" / "amine"
    workspace.mkdir(parents=True)
    markdown = _build_markdown(target_size_kb=15)
    writer = _make_writer(workspace)
    writer.args = {
        "filename": "markers.pdf",
        "content": markdown,
        "template": "consulting_premium",
    }

    await writer.execute()
    pdf = next((workspace / "generated").glob("*.pdf"))
    text = _extract_pdf_text(pdf)

    for marker in ("MARKER_AAA_42", "MARKER_CCC_42"):
        assert marker in text, (
            f"PDF text layer missing marker {marker!r}. The structural content "
            f"of the markdown was lost during rendering. Extracted text "
            f"({len(text)} chars):\n{text[:500]}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# T16 — No unresolved §§include directive must leak into the rendered PDF
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_T16_pdf_contains_no_unresolved_directive(tmp_path: Path, monkeypatch):
    """
    Direct yENoyKIZ regression at the rendering layer: when content is fully
    resolved (no missing includes), the §§include marker MUST NOT appear in
    the rendered PDF text. The Iter 1 fix should already prevent this case
    from reaching the renderer, but T16 provides defence-in-depth.
    """
    _redirect_base_dir(monkeypatch, tmp_path)
    workspace = tmp_path / "shared" / "users" / "amine"
    workspace.mkdir(parents=True)

    src = tmp_path / "tmp" / "uploads" / "src.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        "## Resolved Section\n\nMARKER_AAA_42 inline content for resolution test."
    )

    writer = _make_writer(workspace)
    writer.args = {
        "filename": "noleak.pdf",
        "content": f"# Header\n\n§§include({src})\n\nFooter line.",
        "template": "consulting_premium",
    }

    await writer.execute()
    pdf = next((workspace / "generated").glob("*.pdf"))
    text = _extract_pdf_text(pdf)

    assert "MARKER_AAA_42" in text, "Resolved content must reach the PDF."
    assert "§§include" not in text, (
        f"YENOYKIZ REGRESSION at the renderer: an unresolved-style directive "
        f"reached the PDF text layer. Extracted text:\n{text[:500]}"
    )
