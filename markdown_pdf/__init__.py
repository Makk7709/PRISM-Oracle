"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  markdown_pdf — MIT-licensed drop-in replacement shim                        ║
║                                                                              ║
║  Replaces the original `markdown-pdf` package which depends on PyMuPDF       ║
║  (AGPL v3). This shim provides the same public API used by `browser-use`     ║
║  but generates PDFs using `reportlab` (BSD license) instead.                 ║
║                                                                              ║
║  API surface (used by browser_use.filesystem.file_system):                   ║
║    - MarkdownPdf()                                                           ║
║    - MarkdownPdf.add_section(section: Section)                               ║
║    - MarkdownPdf.save(path)                                                  ║
║    - Section(content: str)                                                   ║
║                                                                              ║
║  License: MIT (Korev AI)                                                     ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Union

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class Section:
    """A section of markdown content to be rendered as PDF."""

    def __init__(self, content: str = ""):
        self.content = content


class MarkdownPdf:
    """
    Minimal markdown-to-PDF converter using reportlab (BSD license).

    Drop-in replacement for the original `markdown-pdf` package that
    depends on PyMuPDF (AGPL v3). Supports basic markdown rendering:
    headings (#, ##, ###), bold (**), italic (*), and paragraphs.
    """

    def __init__(self):
        self._sections: List[Section] = []
        self._styles = getSampleStyleSheet()

        # Custom styles
        self._styles.add(ParagraphStyle(
            "MD_H1",
            parent=self._styles["Heading1"],
            fontSize=18,
            spaceAfter=8 * mm,
        ))
        self._styles.add(ParagraphStyle(
            "MD_H2",
            parent=self._styles["Heading2"],
            fontSize=15,
            spaceAfter=6 * mm,
        ))
        self._styles.add(ParagraphStyle(
            "MD_H3",
            parent=self._styles["Heading3"],
            fontSize=12,
            spaceAfter=4 * mm,
        ))
        self._styles.add(ParagraphStyle(
            "MD_Body",
            parent=self._styles["BodyText"],
            fontSize=10,
            leading=14,
            spaceAfter=3 * mm,
        ))

    def add_section(self, section: Section) -> None:
        """Add a section of markdown content."""
        self._sections.append(section)

    def save(self, path: Union[str, Path]) -> None:
        """Render all sections to a PDF file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        story: list = []
        for section in self._sections:
            story.extend(self._render_markdown(section.content))

        if not story:
            # Empty PDF — add a blank spacer so reportlab doesn't crash
            story.append(Spacer(1, 1))

        doc.build(story)

    # ── internal markdown→flowable conversion ──────────────────────────

    def _render_markdown(self, md_text: str) -> list:
        """Convert simple markdown to reportlab flowables."""
        flowables: list = []
        lines = md_text.split("\n")
        paragraph_buffer: list[str] = []

        def _flush_paragraph():
            if paragraph_buffer:
                text = " ".join(paragraph_buffer).strip()
                if text:
                    text = self._md_inline(text)
                    flowables.append(Paragraph(text, self._styles["MD_Body"]))
                paragraph_buffer.clear()

        for line in lines:
            stripped = line.strip()

            # Empty line → flush current paragraph
            if not stripped:
                _flush_paragraph()
                continue

            # Headings
            if stripped.startswith("### "):
                _flush_paragraph()
                heading = self._md_inline(stripped[4:].strip())
                flowables.append(Paragraph(heading, self._styles["MD_H3"]))
                flowables.append(Spacer(1, 2 * mm))
            elif stripped.startswith("## "):
                _flush_paragraph()
                heading = self._md_inline(stripped[3:].strip())
                flowables.append(Paragraph(heading, self._styles["MD_H2"]))
                flowables.append(Spacer(1, 3 * mm))
            elif stripped.startswith("# "):
                _flush_paragraph()
                heading = self._md_inline(stripped[2:].strip())
                flowables.append(Paragraph(heading, self._styles["MD_H1"]))
                flowables.append(Spacer(1, 4 * mm))
            elif stripped.startswith("---") or stripped.startswith("***"):
                _flush_paragraph()
                flowables.append(Spacer(1, 4 * mm))
            else:
                paragraph_buffer.append(stripped)

        _flush_paragraph()
        return flowables

    @staticmethod
    def _md_inline(text: str) -> str:
        """Convert inline markdown (bold, italic) to reportlab XML tags.

        Handles nested emphasis by processing bold first, then stripping
        remaining single asterisks (italic inside bold is flattened to bold)
        to avoid producing invalid XML nesting that reportlab rejects.
        """
        # Inline code first (protect from bold/italic processing)
        text = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', text)

        # Bold: **text** → <b>text</b>
        # Inner content may contain * for italic — strip them to avoid
        # invalid XML nesting (<b>...<i>...</b></i> is invalid).
        def _bold_replace(m: re.Match) -> str:
            inner = m.group(1).replace("*", "")
            return f"<b>{inner}</b>"

        text = re.sub(r"\*\*(.+?)\*\*", _bold_replace, text)

        # Italic: *text* → <i>text</i> (only remaining single asterisks)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)

        return text
