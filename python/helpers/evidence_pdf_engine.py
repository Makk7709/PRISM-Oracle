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
import logging
from io import BytesIO
from datetime import datetime
from typing import Optional

logger = logging.getLogger("evidence_pdf_engine")

# ═══════════════════════════════════════════════════════════════════════════════
# PRISM HTML TEMPLATE — Charte graphique KOREV Evidence
# ═══════════════════════════════════════════════════════════════════════════════

EVIDENCE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

        :root {{
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
        }}

        @page {{
            size: A4;
            margin: 20mm 22mm 25mm 22mm;

            @top-left {{
                content: "KOREV Evidence";
                font-family: 'Playfair Display', Georgia, serif;
                font-size: 8pt;
                color: #8B95A5;
            }}

            @top-right {{
                content: "{header_right}";
                font-family: 'Inter', sans-serif;
                font-size: 7pt;
                color: #4A7CFF;
                text-transform: uppercase;
                letter-spacing: 0.1em;
            }}

            @bottom-left {{
                content: "KOREV Evidence — Confidentiel";
                font-family: 'Inter', sans-serif;
                font-size: 7pt;
                color: #8B95A5;
            }}

            @bottom-right {{
                content: "Page " counter(page) " / " counter(pages);
                font-family: 'Inter', sans-serif;
                font-size: 7pt;
                color: #8B95A5;
            }}
        }}

        @page :first {{
            margin: 0;
            @top-left {{ content: none; }}
            @top-right {{ content: none; }}
            @bottom-left {{ content: none; }}
            @bottom-right {{ content: none; }}
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 10pt;
            line-height: 1.65;
            color: var(--prism-text-primary);
        }}

        /* ── COVER PAGE ──────────────────────────────────── */
        /* WeasyPrint: no flexbox — use block layout + padding for centering */
        .cover {{
            position: relative;
            width: 210mm;
            height: 297mm;
            background: var(--prism-dark);
            color: white;
            text-align: center;
            padding-top: 90mm;
            page-break-after: always;
            overflow: hidden;
        }}

        .cover__badge {{
            font-family: 'Inter', sans-serif;
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
        }}

        .cover__title {{
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 34pt;
            font-weight: 400;
            line-height: 1.15;
            margin-bottom: 16px;
            letter-spacing: -0.02em;
        }}

        .cover__title b {{ font-weight: 700; }}
        .cover__title i {{ font-style: italic; font-weight: 400; }}

        .cover__subtitle {{
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 14pt;
            color: #A0AEC0;
            margin-bottom: 50px;
            margin-left: auto;
            margin-right: auto;
            line-height: 1.4;
            max-width: 420px;
        }}

        .cover__meta {{
            font-size: 8pt;
            color: #718096;
            margin-top: 80px;
        }}

        .cover__meta span {{ display: block; margin-bottom: 2px; }}

        /* ── CONTENT ─────────────────────────────────────── */
        .content {{ padding-top: 4px; }}

        /* ── HEADINGS ────────────────────────────────────── */
        h1 {{
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 18pt;
            font-weight: 600;
            color: var(--prism-text-primary);
            margin-top: 28px;
            margin-bottom: 10px;
            letter-spacing: -0.01em;
            page-break-after: avoid;
        }}

        h2 {{
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 13pt;
            font-weight: 600;
            color: var(--prism-accent);
            margin-top: 22px;
            margin-bottom: 8px;
            padding-bottom: 5px;
            border-bottom: 1px solid var(--prism-border);
            page-break-after: avoid;
        }}

        h3 {{
            font-family: 'Inter', sans-serif;
            font-size: 11pt;
            font-weight: 700;
            color: var(--prism-text-primary);
            margin-top: 16px;
            margin-bottom: 6px;
            page-break-after: avoid;
        }}

        h4 {{
            font-family: 'Inter', sans-serif;
            font-size: 10pt;
            font-weight: 600;
            color: var(--prism-text-secondary);
        }}

        p {{
            margin-bottom: 8px;
            color: var(--prism-text-secondary);
            orphans: 3;
            widows: 3;
        }}

        strong {{ font-weight: 600; color: var(--prism-text-primary); }}
        a {{ color: var(--prism-accent); text-decoration: none; }}

        /* ── TABLES ──────────────────────────────────────── */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 14px 0;
            font-size: 8.5pt;
            table-layout: fixed;
            page-break-inside: auto;
        }}

        thead {{ display: table-header-group; }}

        thead th {{
            background: var(--prism-dark);
            color: white;
            font-weight: 600;
            text-align: left;
            padding: 7px 9px;
            font-size: 7.5pt;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        thead th:first-child {{ border-radius: 4px 0 0 0; }}
        thead th:last-child {{ border-radius: 0 4px 0 0; }}

        tbody td {{
            padding: 6px 9px;
            border-bottom: 1px solid var(--prism-border-light);
            vertical-align: top;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}

        tbody tr:nth-child(even) {{ background: var(--prism-bg-warm); }}

        /* ── LISTS ───────────────────────────────────────── */
        ul, ol {{ padding-left: 18px; margin-bottom: 8px; }}
        li {{ margin-bottom: 4px; color: var(--prism-text-secondary); font-size: 9.5pt; }}
        li strong {{ color: var(--prism-text-primary); }}

        /* ── BLOCKQUOTES ─────────────────────────────────── */
        blockquote {{
            border-left: 3px solid var(--prism-accent);
            padding: 10px 14px;
            margin: 12px 0;
            background: var(--prism-accent-bg);
            border-radius: 0 4px 4px 0;
            font-style: italic;
            color: var(--prism-text-secondary);
        }}

        blockquote p {{ margin-bottom: 4px; }}

        /* ── CODE ────────────────────────────────────────── */
        code {{
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 8.5pt;
            background: var(--prism-bg-warm);
            padding: 1px 4px;
            border-radius: 3px;
            color: var(--prism-accent);
        }}

        pre {{
            background: var(--prism-dark);
            color: #E2E8F0;
            padding: 12px 14px;
            border-radius: 6px;
            font-size: 8pt;
            line-height: 1.5;
            overflow-wrap: break-word;
            white-space: pre-wrap;
            margin: 10px 0;
        }}

        pre code {{ background: none; color: inherit; padding: 0; }}

        /* ── MISC ────────────────────────────────────────── */
        hr {{ border: none; border-top: 1px solid var(--prism-border); margin: 16px 0; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>

<!-- COVER -->
<div class="cover">
    <div class="cover__badge">KOREV Evidence</div>
    <div class="cover__title"><b>KOREV</b> <i>Evidence</i></div>
    <div class="cover__subtitle">{title}</div>
    <div class="cover__meta">
        <span>Auteur : KOREV Evidence</span>
        <span>Date : {date}</span>
    </div>
</div>

<!-- CONTENT -->
<div class="content">
{content}
</div>

</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN → HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _md_to_html(md_text: str) -> str:
    """Convert markdown to HTML with tables, code, etc."""
    try:
        import markdown
        return markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "toc", "nl2br", "sane_lists"],
        )
    except ImportError:
        logger.warning("markdown library not available, using basic conversion")
        # Basic fallback: just wrap in paragraphs
        import re
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


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def markdown_to_pdf(
    content: str,
    output_path: str,
    title: Optional[str] = None,
    header_right: str = "Document",
) -> str:
    """
    Génère un PDF branded Evidence depuis du Markdown.

    Args:
        content: Contenu Markdown
        output_path: Chemin du PDF de sortie
        title: Titre sur la page de couverture (auto-détecté si None)
        header_right: Texte en haut à droite de chaque page

    Returns:
        Chemin du fichier PDF généré
    """
    if title is None:
        title = _extract_title(content)

    html_content = _md_to_html(content)
    full_html = EVIDENCE_HTML_TEMPLATE.format(
        title=title,
        content=html_content,
        date=datetime.now().strftime("%Y-%m-%d"),
        header_right=header_right,
    )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    try:
        import weasyprint
        weasyprint.HTML(string=full_html).write_pdf(output_path)
        logger.info(f"PDF generated: {output_path}")
        return output_path
    except ImportError:
        logger.error("weasyprint not installed — falling back to legacy ReportLab")
        return _reportlab_fallback(content, output_path, title)
    except Exception as e:
        logger.error(f"WeasyPrint failed: {e} — falling back to legacy ReportLab")
        return _reportlab_fallback(content, output_path, title)


def markdown_to_pdf_bytes(
    content: str,
    title: Optional[str] = None,
    header_right: str = "Document",
) -> bytes:
    """
    Génère un PDF branded Evidence en mémoire (bytes).

    Args:
        content: Contenu Markdown
        title: Titre sur la page de couverture
        header_right: Texte en haut à droite

    Returns:
        PDF en bytes
    """
    if title is None:
        title = _extract_title(content)

    html_content = _md_to_html(content)
    full_html = EVIDENCE_HTML_TEMPLATE.format(
        title=title,
        content=html_content,
        date=datetime.now().strftime("%Y-%m-%d"),
        header_right=header_right,
    )

    try:
        import weasyprint
        return weasyprint.HTML(string=full_html).write_pdf()
    except ImportError:
        logger.error("weasyprint not installed — falling back to legacy ReportLab")
        return _reportlab_fallback_bytes(content, title)
    except Exception as e:
        logger.error(f"WeasyPrint failed: {e} — falling back to legacy ReportLab")
        return _reportlab_fallback_bytes(content, title)


def html_to_pdf(html_content: str, output_path: str) -> str:
    """
    Convertit du HTML complet en PDF (pour les brochures HTML custom).
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    try:
        import weasyprint
        weasyprint.HTML(string=html_content).write_pdf(output_path)
        return output_path
    except Exception as e:
        logger.error(f"HTML to PDF failed: {e}")
        raise


def html_to_pdf_bytes(html_content: str) -> bytes:
    """Convertit du HTML complet en PDF bytes."""
    try:
        import weasyprint
        return weasyprint.HTML(string=html_content).write_pdf()
    except Exception as e:
        logger.error(f"HTML to PDF bytes failed: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTLAB FALLBACK (avoids circular dependency with pdf_generator.py)
# ═══════════════════════════════════════════════════════════════════════════════

def _reportlab_fallback(content: str, output_path: str, title: str) -> str:
    """Direct ReportLab fallback — does NOT call pdf_generator.generate_pdf."""
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                leftMargin=2.5*cm, rightMargin=2.5*cm,
                                topMargin=2.5*cm, bottomMargin=2.5*cm,
                                title=title)
        styles = getSampleStyleSheet()
        elements = []

        if title:
            elements.append(Paragraph(title, styles['Title']))
            elements.append(Spacer(1, 20))

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 6))
            elif line.startswith('# '):
                elements.append(Paragraph(line[2:], styles['Heading1']))
            elif line.startswith('## '):
                elements.append(Paragraph(line[3:], styles['Heading2']))
            elif line.startswith('### '):
                elements.append(Paragraph(line[4:], styles['Heading3']))
            else:
                safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                elements.append(Paragraph(safe, styles['Normal']))

        doc.build(elements)
        logger.info(f"ReportLab fallback PDF: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"ReportLab fallback failed: {e}")
        md_path = output_path.replace('.pdf', '.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return md_path


def _reportlab_fallback_bytes(content: str, title: str) -> bytes:
    """Direct ReportLab fallback returning bytes."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        path = _reportlab_fallback(content, tmp.name, title)
        with open(path, 'rb') as f:
            return f.read()
