"""
KOREV Evidence — Moteur PDF centralisé (WeasyPrint + PRISM Design System).

Ce module est LE point d'entrée unique pour toute génération de PDF dans Evidence.
Il produit des PDFs avec la charte graphique PRISM : Playfair Display, Inter,
couleurs Evidence, tableaux sombres, cover page branded.

Usage:
    from python.helpers.evidence_pdf_engine import markdown_to_pdf, markdown_to_pdf_bytes

    # Vers fichier
    markdown_to_pdf(content, output_path, title="Mon Document")

    # En mémoire (bytes)
    pdf_bytes = markdown_to_pdf_bytes(content, title="Mon Document")
"""

import os
import re
import logging
import traceback
from datetime import datetime
from typing import Optional

logger = logging.getLogger("evidence_pdf_engine")

# ═══════════════════════════════════════════════════════════════════════════════
# PRISM HTML TEMPLATE — Charte graphique KOREV Evidence
# ═══════════════════════════════════════════════════════════════════════════════
# Uses $PLACEHOLDER$ sentinel tokens (not {}) to avoid Python .format()
# collisions with CSS braces and LLM-generated content containing {}.

_PRISM_CSS = """
        @font-face {
            font-family: 'Inter';
            src: local('Inter'), url('file:///usr/share/fonts/truetype/evidence/Inter-Variable.ttf') format('truetype');
            font-weight: 100 900;
            font-display: swap;
        }
        @font-face {
            font-family: 'Playfair Display';
            src: local('Playfair Display'), url('file:///usr/share/fonts/truetype/evidence/PlayfairDisplay-Variable.ttf') format('truetype');
            font-weight: 400 900;
            font-style: normal;
            font-display: swap;
        }
        @font-face {
            font-family: 'Playfair Display';
            src: local('Playfair Display Italic'), url('file:///usr/share/fonts/truetype/evidence/PlayfairDisplay-Italic-Variable.ttf') format('truetype');
            font-weight: 400 900;
            font-style: italic;
            font-display: swap;
        }

        :root {
            --prism-accent: #4A7CFF;
            --prism-accent-light: #6B95FF;
            --prism-accent-bg: #F0F4FF;
            --prism-dark: #0D1117;
            --prism-text-primary: #1A1D23;
            --prism-text-secondary: #4A5568;
            --prism-text-muted: #8B95A5;
            --prism-border: #E2E8F0;
            --prism-border-light: #F1F5F9;
            --prism-bg-warm: #FAFBFC;
            --prism-green: #38A169;
            --prism-red: #E53E3E;
        }

        @page {
            size: A4;
            margin: 20mm 22mm 25mm 22mm;

            @top-left {
                content: "KOREV Evidence";
                font-family: 'Playfair Display', 'DejaVu Serif', Georgia, serif;
                font-size: 8pt;
                color: #8B95A5;
            }

            @top-right {
                content: "$HEADER_RIGHT$";
                font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Helvetica, sans-serif;
                font-size: 7pt;
                color: #4A7CFF;
                text-transform: uppercase;
                letter-spacing: 0.1em;
            }

            @bottom-left {
                content: "KOREV Evidence \2014  Confidentiel";
                font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Helvetica, sans-serif;
                font-size: 7pt;
                color: #8B95A5;
            }

            @bottom-right {
                content: "Page " counter(page) " / " counter(pages);
                font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Helvetica, sans-serif;
                font-size: 7pt;
                color: #8B95A5;
            }
        }

        @page :first {
            margin: 0;
            @top-left { content: none; }
            @top-right { content: none; }
            @bottom-left { content: none; }
            @bottom-right { content: none; }
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.65;
            color: var(--prism-text-primary);
        }

        .cover {
            position: relative;
            width: 210mm;
            height: 297mm;
            background: var(--prism-dark);
            color: white;
            text-align: center;
            padding-top: 90mm;
            page-break-after: always;
            overflow: hidden;
        }

        .cover__logo {
            margin-bottom: 24px;
        }

        .cover__logo svg {
            width: 80px;
            height: 80px;
        }

        .cover__badge {
            font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Helvetica, sans-serif;
            font-size: 8pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.25em;
            color: var(--prism-accent-light);
            border: 1px solid rgba(74, 124, 255, 0.3);
            padding: 6px 16px;
            border-radius: 4px;
            display: inline-block;
            margin-bottom: 40px;
        }

        .cover__title {
            font-family: 'Playfair Display', 'DejaVu Serif', Georgia, 'Times New Roman', serif;
            font-size: 34pt;
            font-weight: 400;
            line-height: 1.15;
            margin-bottom: 16px;
            letter-spacing: -0.02em;
        }

        .cover__title b { font-weight: 700; }
        .cover__title i { font-style: italic; font-weight: 400; }

        .cover__subtitle {
            font-family: 'Playfair Display', 'DejaVu Serif', Georgia, 'Times New Roman', serif;
            font-size: 14pt;
            color: #A0AEC0;
            margin-bottom: 50px;
            margin-left: auto;
            margin-right: auto;
            line-height: 1.4;
            max-width: 420px;
        }

        .cover__meta {
            font-size: 8pt;
            color: #718096;
            margin-top: 80px;
        }

        .cover__meta span { display: block; margin-bottom: 2px; }

        .content { padding-top: 4px; }

        h1 {
            font-family: 'Playfair Display', 'DejaVu Serif', Georgia, 'Times New Roman', serif;
            font-size: 18pt;
            font-weight: 600;
            color: var(--prism-text-primary);
            margin-top: 28px;
            margin-bottom: 10px;
            letter-spacing: -0.01em;
            page-break-after: avoid;
        }

        h2 {
            font-family: 'Playfair Display', 'DejaVu Serif', Georgia, 'Times New Roman', serif;
            font-size: 13pt;
            font-weight: 600;
            color: var(--prism-accent);
            margin-top: 22px;
            margin-bottom: 8px;
            padding-bottom: 5px;
            border-bottom: 1px solid var(--prism-border);
            page-break-after: avoid;
        }

        h3 {
            font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Helvetica, sans-serif;
            font-size: 11pt;
            font-weight: 700;
            color: var(--prism-text-primary);
            margin-top: 16px;
            margin-bottom: 6px;
            page-break-after: avoid;
        }

        h4 {
            font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Helvetica, sans-serif;
            font-size: 10pt;
            font-weight: 600;
            color: var(--prism-text-secondary);
        }

        p {
            margin-bottom: 8px;
            color: var(--prism-text-secondary);
            orphans: 3;
            widows: 3;
        }

        strong { font-weight: 600; color: var(--prism-text-primary); }
        a { color: var(--prism-accent); text-decoration: none; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 14px 0;
            font-size: 8.5pt;
            table-layout: fixed;
            page-break-inside: auto;
        }

        thead { display: table-header-group; }

        thead th {
            background: var(--prism-dark);
            color: white;
            font-weight: 600;
            text-align: left;
            padding: 7px 9px;
            font-size: 7.5pt;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        thead th:first-child { border-radius: 4px 0 0 0; }
        thead th:last-child { border-radius: 0 4px 0 0; }

        tbody td {
            padding: 6px 9px;
            border-bottom: 1px solid var(--prism-border-light);
            vertical-align: top;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        tbody tr:nth-child(even) { background: var(--prism-bg-warm); }

        ul, ol { padding-left: 18px; margin-bottom: 8px; }
        li { margin-bottom: 4px; color: var(--prism-text-secondary); font-size: 9.5pt; }
        li strong { color: var(--prism-text-primary); }

        blockquote {
            border-left: 3px solid var(--prism-accent);
            padding: 10px 14px;
            margin: 12px 0;
            background: var(--prism-accent-bg);
            border-radius: 0 4px 4px 0;
            font-style: italic;
            color: var(--prism-text-secondary);
        }

        blockquote p { margin-bottom: 4px; }

        code {
            font-family: 'DejaVu Sans Mono', 'SF Mono', 'Fira Code', 'Courier New', monospace;
            font-size: 8.5pt;
            background: var(--prism-bg-warm);
            padding: 1px 4px;
            border-radius: 3px;
            color: var(--prism-accent);
        }

        pre {
            background: var(--prism-dark);
            color: #E2E8F0;
            padding: 12px 14px;
            border-radius: 6px;
            font-size: 8pt;
            line-height: 1.5;
            overflow-wrap: break-word;
            white-space: pre-wrap;
            margin: 10px 0;
        }

        pre code { background: none; color: inherit; padding: 0; }

        hr { border: none; border-top: 1px solid var(--prism-border); margin: 16px 0; }
        img { max-width: 100%; height: auto; }
"""


def _build_full_html(
    html_content: str,
    title: str,
    date_str: str,
    header_right: str,
) -> str:
    """Assemble the PRISM HTML document via safe string concatenation.

    Avoids str.format() entirely — CSS braces and LLM-generated content
    with {} are left untouched.
    """
    css = _PRISM_CSS.replace("$HEADER_RIGHT$", _html_escape(header_right))

    return (
        '<!DOCTYPE html>\n<html lang="fr">\n<head>\n'
        '    <meta charset="UTF-8">\n'
        f'    <title>{_html_escape(title)}</title>\n'
        f'    <style>{css}</style>\n'
        '</head>\n<body>\n\n'
        '<!-- COVER -->\n'
        '<div class="cover">\n'
        f'    <div class="cover__logo">{_get_logo_svg()}</div>\n'
        '    <div class="cover__badge">KOREV Evidence</div>\n'
        '    <div class="cover__title"><b>KOREV</b> <i>Evidence</i></div>\n'
        f'    <div class="cover__subtitle">{_html_escape(title)}</div>\n'
        '    <div class="cover__meta">\n'
        '        <span>Auteur : KOREV Evidence</span>\n'
        f'        <span>Date : {_html_escape(date_str)}</span>\n'
        '    </div>\n'
        '</div>\n\n'
        '<!-- CONTENT -->\n'
        '<div class="content">\n'
        f'{html_content}\n'
        '</div>\n\n'
        '</body>\n</html>'
    )


def _get_logo_svg() -> str:
    """Return the KOREV Evidence logo SVG for the cover page.

    Tries to load from webui/public/ first, falls back to a minimal text mark.
    """
    logo_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "webui", "public", "korev-evidence-logo-light.svg"),
        "/app/webui/public/korev-evidence-logo-light.svg",
    ]
    for p in logo_paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                svg = f.read()
                svg = svg.replace('width="1024"', 'width="80"')
                svg = svg.replace('height="1024"', 'height="80"')
                return svg
        except (OSError, IOError):
            continue
    return ""


def _html_escape(text: str) -> str:
    """Minimal HTML escaping for attribute/text values."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN → HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _md_to_html(md_text: str) -> str:
    """Convert markdown to HTML with tables, code, etc."""
    try:
        import markdown
        return markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "toc", "sane_lists"],
        )
    except ImportError:
        logger.warning("markdown library not available, using basic conversion")
        html = md_text
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = html.replace('\n\n', '</p><p>')
        return f'<p>{html}</p>'


def _extract_title(md_text: str) -> str:
    """Extract first H1 heading as title."""
    for line in md_text.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return "Document KOREV Evidence"


def _sanitize_html_for_weasyprint(html: str) -> str:
    """Remove or neutralize content that can crash tinycss2/WeasyPrint.

    Known triggers:
    - Stray <style> blocks injected by LLM content
    - Inline style attributes with malformed CSS
    - Control characters
    """
    html = re.sub(
        r'<style[^>]*>.*?</style>',
        '',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', html)
    return html


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def markdown_to_pdf(
    content: str,
    output_path: str,
    title: Optional[str] = None,
    header_right: str = "Document",
    enable_charts: bool = True,
) -> str:
    """
    Génère un PDF branded Evidence depuis du Markdown.

    Args:
        content: Contenu Markdown
        output_path: Chemin du PDF de sortie
        title: Titre sur la page de couverture (auto-détecté si None)
        header_right: Texte en haut à droite de chaque page
        enable_charts: Auto-generate PRISM charts from markdown tables

    Returns:
        Chemin du fichier PDF généré
    """
    if title is None:
        title = _extract_title(content)

    charts = []
    if enable_charts:
        charts = _generate_strategic_charts(content, output_path)

    html_content = _md_to_html(content)

    if charts:
        html_content = _inject_charts_html(html_content, charts)

    date_str = datetime.now().strftime("%Y-%m-%d")
    full_html = _build_full_html(html_content, title, date_str, header_right)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    try:
        import weasyprint
        sanitized = _sanitize_html_for_weasyprint(full_html)
        weasyprint.HTML(string=sanitized).write_pdf(output_path)
        logger.info(f"PRISM PDF generated (WeasyPrint): {output_path}")
        return output_path
    except ImportError:
        logger.warning("weasyprint not installed — using PRISM ReportLab engine")
    except Exception:
        logger.error(
            "WeasyPrint rendering failed — using PRISM ReportLab engine\n%s",
            traceback.format_exc(),
        )

    return _reportlab_prism(content, output_path, title, header_right, charts=charts)


def markdown_to_pdf_bytes(
    content: str,
    title: Optional[str] = None,
    header_right: str = "Document",
    enable_charts: bool = True,
) -> bytes:
    """
    Génère un PDF branded Evidence en mémoire (bytes).

    Args:
        content: Contenu Markdown
        title: Titre sur la page de couverture
        header_right: Texte en haut à droite
        enable_charts: Auto-generate PRISM charts from markdown tables

    Returns:
        PDF en bytes
    """
    if title is None:
        title = _extract_title(content)

    charts = []
    if enable_charts:
        charts = _generate_strategic_charts(content)

    html_content = _md_to_html(content)

    if charts:
        html_content = _inject_charts_html(html_content, charts)

    date_str = datetime.now().strftime("%Y-%m-%d")
    full_html = _build_full_html(html_content, title, date_str, header_right)

    try:
        import weasyprint
        sanitized = _sanitize_html_for_weasyprint(full_html)
        return weasyprint.HTML(string=sanitized).write_pdf()
    except ImportError:
        logger.warning("weasyprint not installed — using PRISM ReportLab engine")
    except Exception:
        logger.error(
            "WeasyPrint rendering failed — using PRISM ReportLab engine\n%s",
            traceback.format_exc(),
        )

    return _reportlab_prism_bytes(content, title, header_right)


def html_to_pdf(html_content: str, output_path: str) -> str:
    """
    Convertit du HTML complet en PDF (pour les brochures HTML custom).
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    try:
        import weasyprint
        sanitized = _sanitize_html_for_weasyprint(html_content)
        weasyprint.HTML(string=sanitized).write_pdf(output_path)
        return output_path
    except Exception as e:
        logger.error(f"HTML to PDF failed: {e}")
        raise


def html_to_pdf_bytes(html_content: str) -> bytes:
    """Convertit du HTML complet en PDF bytes."""
    try:
        import weasyprint
        sanitized = _sanitize_html_for_weasyprint(html_content)
        return weasyprint.HTML(string=sanitized).write_pdf()
    except Exception as e:
        logger.error(f"HTML to PDF bytes failed: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# PRISM REPORTLAB ENGINE — Premium fallback with full PRISM styling
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# CHART INTEGRATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_strategic_charts(content: str, output_path: str = "") -> list:
    """Generate PRISM charts from markdown tables (soft dependency)."""
    try:
        from python.helpers.strategic_charts import generate_charts_from_markdown
        chart_dir = None
        if output_path:
            chart_dir = os.path.join(
                os.path.dirname(output_path) or ".", "chart_assets"
            )
        return generate_charts_from_markdown(content, output_dir=chart_dir)
    except ImportError:
        logger.debug("strategic_charts module not available — skipping charts")
        return []
    except Exception:
        logger.warning("Chart generation failed:\n%s", traceback.format_exc())
        return []


def _inject_charts_html(html_content: str, charts: list) -> str:
    """Inject chart images as base64 <img> after their source tables in HTML."""
    try:
        from python.helpers.strategic_charts import inject_charts_into_html
        return inject_charts_into_html(html_content, charts)
    except Exception:
        logger.warning("Chart HTML injection failed:\n%s", traceback.format_exc())
        return html_content


# ═══════════════════════════════════════════════════════════════════════════════
# PRISM REPORTLAB ENGINE — Premium fallback with full PRISM styling
# ═══════════════════════════════════════════════════════════════════════════════

_PRISM_ACCENT_HEX = "#4A7CFF"
_PRISM_DARK_HEX = "#0D1117"
_PRISM_TEXT_PRIMARY_HEX = "#1A1D23"
_PRISM_TEXT_SECONDARY_HEX = "#4A5568"
_PRISM_BORDER_HEX = "#E2E8F0"
_PRISM_BG_WARM_HEX = "#FAFBFC"
_PRISM_ACCENT_BG_HEX = "#F0F4FF"


def _hex_to_color(hex_str: str):
    """Convert hex color to ReportLab Color."""
    from reportlab.lib.colors import HexColor
    return HexColor(hex_str)


def _prism_styles():
    """Build PRISM-branded ReportLab paragraph styles."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

    base_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    italic_font = "Helvetica-Oblique"
    mono_font = "Courier"

    return {
        "cover_badge": ParagraphStyle(
            "cover_badge",
            fontName=bold_font,
            fontSize=8,
            leading=10,
            textColor=_hex_to_color(_PRISM_ACCENT_HEX),
            alignment=TA_CENTER,
            spaceAfter=30,
            textTransform="uppercase",
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName=bold_font,
            fontSize=28,
            leading=34,
            textColor=_hex_to_color("#FFFFFF"),
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontName=italic_font,
            fontSize=13,
            leading=18,
            textColor=_hex_to_color("#A0AEC0"),
            alignment=TA_CENTER,
            spaceAfter=40,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName=base_font,
            fontSize=8,
            leading=11,
            textColor=_hex_to_color("#718096"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "prism_h1",
            fontName=bold_font,
            fontSize=16,
            leading=20,
            textColor=_hex_to_color(_PRISM_TEXT_PRIMARY_HEX),
            spaceBefore=20,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "prism_h2",
            fontName=bold_font,
            fontSize=12,
            leading=16,
            textColor=_hex_to_color(_PRISM_ACCENT_HEX),
            spaceBefore=16,
            spaceAfter=6,
            keepWithNext=True,
            borderWidth=0,
            borderPadding=0,
        ),
        "h3": ParagraphStyle(
            "prism_h3",
            fontName=bold_font,
            fontSize=10,
            leading=13,
            textColor=_hex_to_color(_PRISM_TEXT_PRIMARY_HEX),
            spaceBefore=12,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "h4": ParagraphStyle(
            "prism_h4",
            fontName=bold_font,
            fontSize=9,
            leading=12,
            textColor=_hex_to_color(_PRISM_TEXT_SECONDARY_HEX),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "prism_body",
            fontName=base_font,
            fontSize=9,
            leading=14,
            textColor=_hex_to_color(_PRISM_TEXT_SECONDARY_HEX),
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "prism_bullet",
            fontName=base_font,
            fontSize=9,
            leading=13,
            textColor=_hex_to_color(_PRISM_TEXT_SECONDARY_HEX),
            leftIndent=16,
            bulletIndent=6,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "prism_code",
            fontName=mono_font,
            fontSize=7.5,
            leading=10,
            textColor=_hex_to_color("#E2E8F0"),
            backColor=_hex_to_color(_PRISM_DARK_HEX),
            leftIndent=8,
            rightIndent=8,
            spaceBefore=6,
            spaceAfter=6,
            borderPadding=(8, 8, 8, 8),
        ),
        "blockquote": ParagraphStyle(
            "prism_blockquote",
            fontName=italic_font,
            fontSize=9,
            leading=13,
            textColor=_hex_to_color(_PRISM_TEXT_SECONDARY_HEX),
            leftIndent=14,
            borderColor=_hex_to_color(_PRISM_ACCENT_HEX),
            borderWidth=2,
            borderPadding=(6, 8, 6, 10),
            backColor=_hex_to_color(_PRISM_ACCENT_BG_HEX),
            spaceAfter=8,
        ),
    }


def _make_safe(text: str) -> str:
    """Escape text for ReportLab XML paragraphs, preserving bold/italic."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`', r'<font face="Courier" size="8" color="#4A7CFF">\1</font>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" color="#4A7CFF">\1</a>', text)
    return text


def _parse_md_table(lines: list) -> list:
    """Parse consecutive markdown table lines into list of rows (list of cells)."""
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and not all(set(c) <= {"-", ":", " "} for c in cells):
            rows.append(cells)
    return rows


def _reportlab_prism(
    content: str,
    output_path: str,
    title: str,
    header_right: str = "Document",
    charts: Optional[list] = None,
) -> str:
    """PRISM-branded ReportLab PDF with cover page, styled headings, tables and charts."""
    try:
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
            KeepTogether,
        )
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib.colors import HexColor, white, Color

        page_w, page_h = A4
        styles = _prism_styles()
        elements = []

        display_title = title if len(title) <= 60 else title[:57] + "..."
        date_str = datetime.now().strftime("%d/%m/%Y")

        # ── CONTENT ──────────────────────────────────────────────────
        lines = content.split("\n")
        i = 0
        in_code_block = False
        code_lines = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped.startswith("```"):
                if in_code_block:
                    code_text = _make_safe("\n".join(code_lines))
                    if code_text.strip():
                        elements.append(Paragraph(code_text, styles["code"]))
                    code_lines = []
                    in_code_block = False
                else:
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            if stripped.startswith("|") and "|" in stripped[1:]:
                table_start_line = i
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                rows = _parse_md_table(table_lines)
                if rows:
                    elements.append(Spacer(1, 6))
                    elements.append(_build_prism_table(rows, styles))
                    elements.append(Spacer(1, 6))
                    chart_img = _find_chart_for_table(table_start_line, charts)
                    if chart_img:
                        elements.append(_embed_chart_image(chart_img, page_w - 5 * cm))
                        elements.append(Spacer(1, 8))
                continue

            if not stripped:
                elements.append(Spacer(1, 4))
            elif stripped.startswith("#### "):
                elements.append(Paragraph(_make_safe(stripped[5:]), styles["h4"]))
            elif stripped.startswith("### "):
                elements.append(Paragraph(_make_safe(stripped[4:]), styles["h3"]))
            elif stripped.startswith("## "):
                text = _make_safe(stripped[3:])
                elements.append(Spacer(1, 4))
                elements.append(Paragraph(text, styles["h2"]))
                elements.append(_h2_rule(page_w - 5 * cm))
            elif stripped.startswith("# "):
                elements.append(Paragraph(_make_safe(stripped[2:]), styles["h1"]))
            elif stripped.startswith("> "):
                elements.append(Paragraph(_make_safe(stripped[2:]), styles["blockquote"]))
            elif stripped.startswith("- ") or stripped.startswith("* "):
                bullet_text = _make_safe(stripped[2:])
                elements.append(
                    Paragraph(
                        f'<bullet bulletColor="#4A7CFF">\u2022</bullet> {bullet_text}',
                        styles["bullet"],
                    )
                )
            elif re.match(r'^\d+\.\s', stripped):
                num_text = _make_safe(re.sub(r'^\d+\.\s', '', stripped))
                num = re.match(r'^(\d+)', stripped).group(1)
                elements.append(
                    Paragraph(
                        f'<bullet bulletColor="#4A7CFF">{num}.</bullet> {num_text}',
                        styles["bullet"],
                    )
                )
            elif stripped.startswith("<!--CHART:") and stripped.endswith("-->"):
                chart_path = stripped[10:-3].strip()
                if os.path.isfile(chart_path):
                    elements.append(_embed_chart_image(chart_path, page_w - 5 * cm))
                    elements.append(Spacer(1, 8))
            elif stripped == "---" or stripped == "***":
                elements.append(Spacer(1, 4))
                elements.append(_hr_line(page_w - 5 * cm))
                elements.append(Spacer(1, 4))
            else:
                elements.append(Paragraph(_make_safe(stripped), styles["body"]))

            i += 1

        if code_lines:
            code_text = _make_safe("\n".join(code_lines))
            elements.append(Paragraph(code_text, styles["code"]))

        def _draw_cover_page(canvas, doc):
            """Full-bleed dark cover on page 1 only."""
            canvas.saveState()
            canvas.setFillColor(HexColor(_PRISM_DARK_HEX))
            canvas.rect(0, 0, page_w, page_h, fill=True, stroke=False)

            mid_x = page_w / 2
            badge_y = page_h * 0.62
            canvas.setFont("Helvetica-Bold", 9)
            canvas.setFillColor(HexColor(_PRISM_ACCENT_HEX))
            canvas.drawCentredString(mid_x, badge_y, "KOREV EVIDENCE")

            canvas.setFont("Helvetica-Bold", 30)
            canvas.setFillColor(white)
            canvas.drawCentredString(mid_x, badge_y - 50, "KOREV Evidence")

            canvas.setFont("Helvetica-Oblique", 13)
            canvas.setFillColor(HexColor("#A0AEC0"))
            canvas.drawCentredString(mid_x, badge_y - 85, display_title)

            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(HexColor("#718096"))
            canvas.drawCentredString(
                mid_x, badge_y - 165,
                f"Auteur : KOREV Evidence  |  Date : {date_str}",
            )

            canvas.setFillColor(HexColor(_PRISM_ACCENT_HEX))
            canvas.rect(page_w * 0.3, 30, page_w * 0.4, 2, fill=True, stroke=False)
            canvas.restoreState()

        def _draw_header_footer(canvas, doc):
            """Headers/footers on content pages (page 2+)."""
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(HexColor("#8B95A5"))
            canvas.drawString(2.5 * cm, page_h - 1.2 * cm, "KOREV Evidence")
            canvas.setFillColor(HexColor(_PRISM_ACCENT_HEX))
            canvas.setFont("Helvetica", 6.5)
            canvas.drawRightString(
                page_w - 2.5 * cm, page_h - 1.2 * cm,
                header_right.upper(),
            )
            canvas.setFillColor(HexColor("#8B95A5"))
            canvas.setFont("Helvetica", 7)
            canvas.drawString(2.5 * cm, 1.2 * cm, "KOREV Evidence — Confidentiel")
            canvas.drawRightString(
                page_w - 2.5 * cm, 1.2 * cm,
                f"Page {doc.page}",
            )
            canvas.restoreState()

        elements.insert(0, PageBreak())

        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2.2 * cm, bottomMargin=2.5 * cm,
            title=title,
        )
        doc.build(
            elements,
            onFirstPage=_draw_cover_page,
            onLaterPages=_draw_header_footer,
        )
        logger.info(f"PRISM PDF generated (ReportLab): {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"PRISM ReportLab engine failed: {e}\n{traceback.format_exc()}")
        md_path = output_path.replace('.pdf', '.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return md_path


def _find_chart_for_table(table_line_index: int, charts: Optional[list]) -> Optional[str]:
    """Find a chart image matching a table by line index."""
    if not charts:
        return None
    for chart in charts:
        if abs(chart.table_line_index - table_line_index) <= 2:
            if os.path.isfile(chart.image_path):
                return chart.image_path
    return None


def _embed_chart_image(image_path: str, max_width: float):
    """Create a centered ReportLab Image flowable from a chart PNG."""
    from reportlab.platypus import Image
    from reportlab.lib.units import cm

    try:
        img = Image(image_path)
        iw, ih = img.drawWidth, img.drawHeight
        if iw > max_width:
            scale = max_width / iw
            img.drawWidth = max_width
            img.drawHeight = ih * scale
        img.hAlign = "CENTER"
        return img
    except Exception as exc:
        logger.warning(f"Failed to embed chart image {image_path}: {exc}")
        from reportlab.platypus import Spacer
        return Spacer(1, 1)


def _build_prism_table(rows: list, styles: dict):
    """Build a styled PRISM table from parsed markdown rows."""
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import cm

    if not rows:
        return Paragraph("", styles["body"])

    table_data = []
    for row_cells in rows:
        table_data.append([
            Paragraph(_make_safe(cell), styles["body"])
            for cell in row_cells
        ])

    n_cols = max(len(r) for r in table_data) if table_data else 1
    col_widths = [None] * n_cols

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(_PRISM_DARK_HEX)),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, 0), 0, white),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor(_PRISM_BORDER_HEX)),
        ("ROUNDEDCORNERS", [4, 4, 0, 0]),
    ]

    for row_idx in range(1, len(table_data)):
        if row_idx % 2 == 0:
            style_cmds.append(
                ("BACKGROUND", (0, row_idx), (-1, row_idx), HexColor(_PRISM_BG_WARM_HEX))
            )

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _h2_rule(width: float):
    """Thin accent line under H2 headings."""
    from reportlab.graphics.shapes import Drawing, Line
    d = Drawing(width, 2)
    d.add(Line(0, 1, width, 1, strokeColor=_hex_to_color(_PRISM_BORDER_HEX), strokeWidth=0.5))
    return d


def _hr_line(width: float):
    """Horizontal rule."""
    from reportlab.graphics.shapes import Drawing, Line
    d = Drawing(width, 2)
    d.add(Line(0, 1, width, 1, strokeColor=_hex_to_color(_PRISM_BORDER_HEX), strokeWidth=0.5))
    return d


def _reportlab_prism_bytes(content: str, title: str, header_right: str = "Document") -> bytes:
    """PRISM ReportLab engine returning bytes."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        path = _reportlab_prism(content, tmp.name, title, header_right)
        with open(path, 'rb') as f:
            data = f.read()
        try:
            os.unlink(path)
        except OSError:
            pass
        return data


# Legacy aliases
def _reportlab_fallback(content: str, output_path: str, title: str) -> str:
    return _reportlab_prism(content, output_path, title)


def _reportlab_fallback_bytes(content: str, title: str) -> bytes:
    return _reportlab_prism_bytes(content, title)
