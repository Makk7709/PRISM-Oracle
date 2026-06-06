"""
PDF Test Fixture Generator.

Generates deterministic PDF files for testing PDF extraction.
Uses reportlab (already in requirements.txt) to create PDFs programmatically.

Each PDF is designed to test a specific extraction scenario.
Generated PDFs are byte-stable across runs (no timestamps/random IDs).

Usage:
    python -m tests.fixtures.pdf_generator          # generate all
    python -m tests.fixtures.pdf_generator --list    # list available fixtures

Copyright 2025 Korev AI - Proprietary
"""

import io
import os
from pathlib import Path
from typing import Callable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


FIXTURES_DIR = Path(__file__).parent / "pdfs"

# REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

_GENERATORS: dict[str, Callable[[], bytes]] = {}


def register(name: str):
    """Decorator to register a PDF fixture generator."""
    def decorator(func: Callable[[], bytes]):
        _GENERATORS[name] = func
        return func
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: text_simple.pdf
# Single page, basic text, no tables, no images.
# ═══════════════════════════════════════════════════════════════════════════════

@register("text_simple")
def gen_text_simple() -> bytes:
    """Single page with paragraph text. Tests basic text extraction."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Text Simple Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Document Title: Test Report", styles["Title"]))
    story.append(Spacer(1, 12))

    body_text = (
        "This is a simple test document used to verify PDF text extraction. "
        "It contains multiple sentences with varying vocabulary. "
        "The extraction pipeline should capture every word with correct reading order."
    )
    story.append(Paragraph(body_text, styles["BodyText"]))
    story.append(Spacer(1, 12))

    body_text_2 = (
        "Second paragraph with additional content. "
        "Numbers like 42, 3.14, and 1000000 should be preserved exactly. "
        "Special characters: parentheses (test), brackets [test], "
        "and currency symbols like 100.50 EUR."
    )
    story.append(Paragraph(body_text_2, styles["BodyText"]))
    story.append(Spacer(1, 12))

    body_text_3 = (
        "French text: Les dispositions de l'article L.225-35 du code de commerce "
        "imposent au conseil d'administration de se saisir de toute question "
        "int\u00e9ressant la bonne marche de la soci\u00e9t\u00e9."
    )
    story.append(Paragraph(body_text_3, styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: text_multipage.pdf
# 3 pages with headers, body text, page numbers.
# ═══════════════════════════════════════════════════════════════════════════════

@register("text_multipage")
def gen_text_multipage() -> bytes:
    """Multi-page document with headers and body text."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Multipage Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    for page_num in range(1, 4):
        story.append(Paragraph(f"Chapter {page_num}: Analysis Section", styles["Heading1"]))
        story.append(Spacer(1, 12))

        for para_num in range(1, 5):
            text = (
                f"Page {page_num}, paragraph {para_num}. "
                f"This is substantive content that spans multiple lines "
                f"to ensure the extraction pipeline correctly handles "
                f"text flow across line breaks within the PDF layout. "
                f"Word count verification: the total words on this page "
                f"should be deterministic and reproducible."
            )
            story.append(Paragraph(text, styles["BodyText"]))
            story.append(Spacer(1, 8))

        if page_num < 3:
            story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: table_simple.pdf
# One page with a simple 4x3 table.
# ═══════════════════════════════════════════════════════════════════════════════

@register("table_simple")
def gen_table_simple() -> bytes:
    """Single page with a simple table. Tests table extraction."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Table Simple Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Revenue Report Q1 2025", styles["Title"]))
    story.append(Spacer(1, 20))

    # Simple 4-row, 3-column table
    data = [
        ["Product", "Revenue", "Growth"],
        ["Alpha", "1250000", "12.5%"],
        ["Beta", "875000", "8.3%"],
        ["Gamma", "2100000", "15.7%"],
    ]

    table = Table(data, colWidths=[150, 120, 100])
    table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ECF0F1")]),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Total revenue for Q1 2025 amounts to 4225000 EUR.",
        styles["BodyText"]
    ))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: table_financial.pdf
# Financial table with numbers, currency, percentages.
# Tests numeric extraction accuracy.
# ═══════════════════════════════════════════════════════════════════════════════

@register("table_financial")
def gen_table_financial() -> bytes:
    """Financial table with numbers and currency. Tests numeric accuracy."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Financial Table Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Bilan Financier 2024", styles["Title"]))
    story.append(Spacer(1, 16))

    data = [
        ["Poste", "2024 (EUR)", "2023 (EUR)", "Variation", "% Var"],
        ["Chiffre d'affaires", "15 250 000", "13 800 000", "+1 450 000", "+10.5%"],
        ["Charges d'exploitation", "9 150 000", "8 500 000", "+650 000", "+7.6%"],
        ["R\u00e9sultat d'exploitation", "6 100 000", "5 300 000", "+800 000", "+15.1%"],
        ["R\u00e9sultat net", "4 575 000", "3 975 000", "+600 000", "+15.1%"],
        ["Capitaux propres", "22 350 000", "19 750 000", "+2 600 000", "+13.2%"],
        ["Dettes financi\u00e8res", "8 900 000", "10 200 000", "-1 300 000", "-12.7%"],
        ["Tr\u00e9sorerie nette", "3 200 000", "2 150 000", "+1 050 000", "+48.8%"],
    ]

    table = Table(data, colWidths=[130, 90, 90, 90, 60])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A237E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8EAF6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(table)

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: mixed_content.pdf
# Page 1: text, Page 2: table + text, tests hybrid extraction.
# ═══════════════════════════════════════════════════════════════════════════════

@register("mixed_content")
def gen_mixed_content() -> bytes:
    """Mixed content: text + tables across pages. Tests hybrid extraction."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Mixed Content Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    # Page 1: Pure text
    story.append(Paragraph("Section 1: Executive Summary", styles["Heading1"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This report presents the annual financial review for fiscal year 2024. "
        "The company demonstrated strong growth across all segments, "
        "with total revenue increasing by 15.2% year-over-year. "
        "Operating margins improved from 38.4% to 40.0%, "
        "driven by operational efficiencies and scale benefits.",
        styles["BodyText"]
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Key highlights include: record revenue of 15.25 million EUR, "
        "net income growth of 15.1%, and a reduction in financial debt "
        "of 12.7%. The balance sheet remains strong with net cash "
        "position of 3.2 million EUR.",
        styles["BodyText"]
    ))
    story.append(PageBreak())

    # Page 2: Table + text
    story.append(Paragraph("Section 2: Quarterly Breakdown", styles["Heading1"]))
    story.append(Spacer(1, 12))

    data = [
        ["Quarter", "Revenue", "EBITDA", "Margin"],
        ["Q1", "3 500 000", "1 400 000", "40.0%"],
        ["Q2", "3 750 000", "1 537 500", "41.0%"],
        ["Q3", "4 000 000", "1 640 000", "41.0%"],
        ["Q4", "4 000 000", "1 560 000", "39.0%"],
    ]

    table = Table(data, colWidths=[80, 110, 110, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004D40")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Note: All figures are in EUR. EBITDA margins remained stable "
        "throughout the year, with a slight dip in Q4 due to seasonal effects.",
        styles["BodyText"]
    ))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: empty.pdf
# Empty PDF with no content. Tests edge case handling.
# ═══════════════════════════════════════════════════════════════════════════════

@register("empty")
def gen_empty() -> bytes:
    """Empty PDF with no text content. Tests edge case handling."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    # Just create a blank page
    c.showPage()
    c.save()
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: single_word.pdf
# Minimal PDF with just one word. Tests minimal content extraction.
# ═══════════════════════════════════════════════════════════════════════════════

@register("single_word")
def gen_single_word() -> bytes:
    """PDF with a single word. Tests minimal content extraction."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "Korev")
    c.showPage()
    c.save()
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: dense_text.pdf
# Many paragraphs of text. Tests performance and word count accuracy.
# ═══════════════════════════════════════════════════════════════════════════════

@register("dense_text")
def gen_dense_text() -> bytes:
    """Dense text document. Tests high word-count extraction."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Dense Text Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Dense Text Analysis Document", styles["Title"]))
    story.append(Spacer(1, 12))

    # Generate deterministic dense content
    paragraphs = [
        (
            "The regulatory framework governing financial institutions in the "
            "European Union has undergone significant transformation following "
            "the implementation of Basel III requirements. Credit institutions "
            "are now required to maintain higher capital adequacy ratios, with "
            "Common Equity Tier 1 capital requirements set at a minimum of "
            "4.5 percent of risk-weighted assets."
        ),
        (
            "Market risk management practices have evolved to incorporate "
            "stress testing methodologies mandated by the European Banking "
            "Authority. Institutions must demonstrate their ability to "
            "withstand adverse macroeconomic scenarios, including GDP "
            "contractions of up to 5.0 percent and unemployment increases "
            "of 3.0 percentage points above baseline projections."
        ),
        (
            "Operational risk quantification follows the standardized approach "
            "for most institutions, with larger firms employing advanced "
            "measurement approaches. Loss data collection spans seven event "
            "types: internal fraud, external fraud, employment practices, "
            "clients and products, damage to physical assets, business "
            "disruption, and execution and delivery failures."
        ),
        (
            "Liquidity coverage ratios require institutions to hold high-quality "
            "liquid assets sufficient to cover net cash outflows over a "
            "30-day stress period. The minimum requirement stands at 100 "
            "percent, with Level 1 assets including central bank reserves "
            "and sovereign debt instruments rated above AA-minus."
        ),
        (
            "Anti-money laundering compliance frameworks incorporate "
            "customer due diligence procedures, transaction monitoring "
            "systems, and suspicious activity reporting mechanisms. "
            "Financial institutions must maintain records for a minimum "
            "of five years following the termination of a business "
            "relationship or the completion of an occasional transaction."
        ),
    ]

    for i, para in enumerate(paragraphs):
        story.append(Paragraph(f"{i + 1}. Regulatory Analysis", styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(para, styles["BodyText"]))
        story.append(Spacer(1, 10))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: unicode_content.pdf
# French legal text with accents, special chars.
# ═══════════════════════════════════════════════════════════════════════════════

@register("unicode_content")
def gen_unicode_content() -> bytes:
    """French legal text with accents and special characters."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Unicode Content Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(
        "R\u00e9glementation Fran\u00e7aise - Texte de R\u00e9f\u00e9rence",
        styles["Title"]
    ))
    story.append(Spacer(1, 12))

    french_paragraphs = [
        (
            "Article L.225-35 du Code de commerce : Le conseil d\u2019administration "
            "d\u00e9termine les orientations de l\u2019activit\u00e9 de la soci\u00e9t\u00e9 et "
            "veille \u00e0 leur mise en \u0153uvre, conform\u00e9ment \u00e0 son int\u00e9r\u00eat "
            "social, en prenant en consid\u00e9ration les enjeux sociaux et "
            "environnementaux de son activit\u00e9."
        ),
        (
            "Arr\u00eat de la Cour de cassation, Chambre commerciale, du 15 mars 2023 : "
            "La responsabilit\u00e9 des dirigeants peut \u00eatre engag\u00e9e en cas de "
            "manquement \u00e0 l\u2019obligation de loyaut\u00e9 envers les actionnaires. "
            "Cette obligation implique une information compl\u00e8te, sinc\u00e8re et "
            "pr\u00e9cise sur la situation financi\u00e8re de l\u2019entreprise."
        ),
        (
            "D\u00e9cret n\u00b0 2024-567 relatif aux obligations de transparence : "
            "Les soci\u00e9t\u00e9s dont le chiffre d\u2019affaires exc\u00e8de 750 millions "
            "d\u2019euros sont tenues de publier un rapport pays par pays "
            "conform\u00e9ment aux dispositions de l\u2019article 223 quinquies C "
            "du code g\u00e9n\u00e9ral des imp\u00f4ts."
        ),
    ]

    for para in french_paragraphs:
        story.append(Paragraph(para, styles["BodyText"]))
        story.append(Spacer(1, 10))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: corrupted.pdf
# Invalid bytes. Tests error handling.
# ═══════════════════════════════════════════════════════════════════════════════

@register("corrupted")
def gen_corrupted() -> bytes:
    """Invalid/corrupted PDF bytes. Tests error handling."""
    # Start with PDF header but corrupt the rest
    return b"%PDF-1.4\n%%EOF\nGARBAGE_DATA_NOT_A_REAL_PDF"


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE: two_tables.pdf
# Two tables on the same page with text between them.
# ═══════════════════════════════════════════════════════════════════════════════

@register("two_tables")
def gen_two_tables() -> bytes:
    """Two tables on one page with text between them."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title="Two Tables Test Fixture",
        author="Korev AI Test Suite",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Comparative Analysis", styles["Title"]))
    story.append(Spacer(1, 12))

    # Table 1
    story.append(Paragraph("Table 1: Revenue by Region", styles["Heading2"]))
    story.append(Spacer(1, 8))
    data1 = [
        ["Region", "2024", "2023"],
        ["Europe", "8 500 000", "7 200 000"],
        ["North America", "4 250 000", "3 900 000"],
        ["Asia Pacific", "2 500 000", "2 700 000"],
    ]
    t1 = Table(data1, colWidths=[120, 100, 100])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D47A1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t1)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "Europe remains the dominant revenue source, contributing 55.7% "
        "of total revenue. Asia Pacific showed a 7.4% decline.",
        styles["BodyText"]
    ))
    story.append(Spacer(1, 20))

    # Table 2
    story.append(Paragraph("Table 2: Headcount by Region", styles["Heading2"]))
    story.append(Spacer(1, 8))
    data2 = [
        ["Region", "Employees", "Contractors"],
        ["Europe", "450", "120"],
        ["North America", "280", "85"],
        ["Asia Pacific", "190", "45"],
    ]
    t2 = Table(data2, colWidths=[120, 100, 100])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATE ALL FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

def generate_all(output_dir: Path | None = None) -> dict[str, Path]:
    """Generate all PDF fixtures. Returns dict of name -> path."""
    output_dir = output_dir or FIXTURES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = {}
    for name, generator in _GENERATORS.items():
        filepath = output_dir / f"{name}.pdf"
        pdf_bytes = generator()
        filepath.write_bytes(pdf_bytes)
        generated[name] = filepath

    return generated


def get_fixture_path(name: str) -> Path:
    """Get path to a fixture PDF, generating it if needed."""
    filepath = FIXTURES_DIR / f"{name}.pdf"
    if not filepath.exists():
        if name not in _GENERATORS:
            raise ValueError(f"Unknown fixture: {name}. Available: {list(_GENERATORS.keys())}")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = _GENERATORS[name]()
        filepath.write_bytes(pdf_bytes)
    return filepath


def get_fixture_bytes(name: str) -> bytes:
    """Get fixture PDF as bytes, generating if needed."""
    if name not in _GENERATORS:
        raise ValueError(f"Unknown fixture: {name}. Available: {list(_GENERATORS.keys())}")
    return _GENERATORS[name]()


def list_fixtures() -> list[str]:
    """List all available fixture names."""
    return sorted(_GENERATORS.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--list" in sys.argv:
        print("Available PDF fixtures:")
        for name in list_fixtures():
            func = _GENERATORS[name]
            print(f"  {name:25s} - {func.__doc__.strip()}")
        sys.exit(0)

    print(f"Generating PDF fixtures in {FIXTURES_DIR}...")
    generated = generate_all()
    for name, path in sorted(generated.items()):
        size = path.stat().st_size
        print(f"  {name:25s} -> {path.name} ({size:,} bytes)")
    print(f"\nGenerated {len(generated)} fixtures.")
