#!/opt/homebrew/bin/python3.11
"""
KOREV Evidence — Générateur PDF branded
========================================

Convertit n'importe quel fichier Markdown ou HTML en PDF
avec la charte graphique Evidence (Playfair Display, PRISM design system).

Usage:
    python scripts/evidence_pdf.py <fichier.md>
    python scripts/evidence_pdf.py <fichier.html>
    python scripts/evidence_pdf.py <fichier.md> -o sortie.pdf
    python scripts/evidence_pdf.py <fichier.md> --open
    python scripts/evidence_pdf.py <fichier.md> --title "Mon Titre"
    python scripts/evidence_pdf.py <fichier.md> --dark

Exemples:
    python scripts/evidence_pdf.py docs/mon_rapport.md --open
    python scripts/evidence_pdf.py docs/analyse.md -o ~/Desktop/analyse.pdf --title "Analyse Juridique" --open
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import markdown
except ImportError:
    print("❌ Module 'markdown' manquant. Installation...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

try:
    import weasyprint
except ImportError:
    print("❌ Module 'weasyprint' manquant. Installation...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint"])
    import weasyprint


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE HTML — Charte graphique KOREV Evidence
# ═══════════════════════════════════════════════════════════════════

EVIDENCE_TEMPLATE = """<!DOCTYPE html>
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
            --prism-dark-surface: #161B22;
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
            margin-top: 0;
            margin-bottom: 0;
            margin-left: 0;
            margin-right: 0;
            @top-left {{ content: none; }}
            @top-right {{ content: none; }}
            @bottom-left {{ content: none; }}
            @bottom-right {{ content: none; }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 10pt;
            line-height: 1.65;
            color: var(--prism-text-primary);
        }}

        /* ── COVER PAGE ────────────────────────────────────── */
        .cover {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            width: 210mm;
            height: 297mm;
            background: var(--prism-dark);
            color: white;
            page-break-after: always;
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
            line-height: 1.4;
            max-width: 420px;
        }}

        .cover__meta {{
            font-size: 8pt;
            color: #4A5568;
            margin-top: 80px;
        }}

        .cover__meta span {{ display: block; margin-bottom: 2px; }}

        .cover__classification {{
            font-weight: 600;
            color: var(--prism-accent-light);
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-size: 7pt;
            position: absolute;
            top: 20mm;
            right: 22mm;
        }}

        /* ── CONTENT ───────────────────────────────────────── */
        .content {{
            padding-top: 4px;
        }}

        /* ── HEADINGS ──────────────────────────────────────── */
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
            margin-top: 12px;
            margin-bottom: 5px;
        }}

        p {{
            margin-bottom: 8px;
            color: var(--prism-text-secondary);
            orphans: 3;
            widows: 3;
        }}

        strong {{ font-weight: 600; color: var(--prism-text-primary); }}

        /* ── TABLES ────────────────────────────────────────── */
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

        /* ── LISTS ─────────────────────────────────────────── */
        ul, ol {{
            padding-left: 18px;
            margin-bottom: 8px;
        }}

        li {{
            margin-bottom: 4px;
            color: var(--prism-text-secondary);
            font-size: 9.5pt;
        }}

        li strong {{ color: var(--prism-text-primary); }}

        /* ── BLOCKQUOTES ───────────────────────────────────── */
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

        /* ── CODE ──────────────────────────────────────────── */
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

        pre code {{
            background: none;
            color: inherit;
            padding: 0;
        }}

        /* ── HORIZONTAL RULE ───────────────────────────────── */
        hr {{
            border: none;
            border-top: 1px solid var(--prism-border);
            margin: 16px 0;
        }}

        /* ── LINKS ─────────────────────────────────────────── */
        a {{
            color: var(--prism-accent);
            text-decoration: none;
        }}

        /* ── IMAGES ────────────────────────────────────────── */
        img {{
            max-width: 100%;
            height: auto;
        }}
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


def md_to_html(md_text: str) -> str:
    """Convert markdown to HTML with tables and code extensions."""
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "nl2br", "sane_lists"],
    )


def extract_title_from_md(md_text: str) -> str:
    """Extract the first H1 heading as title."""
    for line in md_text.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return "Document KOREV Evidence"


def generate_pdf(
    input_path: str,
    output_path: str = None,
    title: str = None,
    open_after: bool = False,
    header_right: str = "Document",
):
    """Generate a branded Evidence PDF from a Markdown or HTML file."""

    input_file = Path(input_path).resolve()

    if not input_file.exists():
        print(f"❌ Fichier introuvable : {input_file}")
        sys.exit(1)

    suffix = input_file.suffix.lower()

    # Read input
    raw = input_file.read_text(encoding="utf-8")

    # Determine content
    if suffix in (".md", ".markdown"):
        if title is None:
            title = extract_title_from_md(raw)
        html_content = md_to_html(raw)
    elif suffix in (".html", ".htm"):
        # If it's already a full HTML file, convert directly
        if "<html" in raw.lower():
            print("📄 Fichier HTML complet détecté — conversion directe...")
            if output_path is None:
                output_path = str(input_file.with_suffix(".pdf"))
            weasyprint.HTML(string=raw).write_pdf(output_path)
            size_kb = os.path.getsize(output_path) / 1024
            print(f"✅ PDF généré : {output_path} ({size_kb:.0f} Ko)")
            if open_after:
                subprocess.run(["open", output_path])
            return output_path
        else:
            html_content = raw
            if title is None:
                title = "Document KOREV Evidence"
    else:
        # Treat as markdown
        if title is None:
            title = extract_title_from_md(raw)
        html_content = md_to_html(raw)

    # Output path
    if output_path is None:
        output_path = str(input_file.with_suffix(".pdf"))

    # Build full HTML
    full_html = EVIDENCE_TEMPLATE.format(
        title=title,
        content=html_content,
        date=datetime.now().strftime("%Y-%m-%d"),
        header_right=header_right,
    )

    # Generate PDF
    print(f"🔄 Génération du PDF...")
    weasyprint.HTML(string=full_html).write_pdf(output_path)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ PDF généré : {output_path} ({size_kb:.0f} Ko)")

    if open_after:
        subprocess.run(["open", output_path])

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="KOREV Evidence — Générateur PDF branded",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/evidence_pdf.py docs/mon_rapport.md --open
  python scripts/evidence_pdf.py docs/analyse.md -o ~/Desktop/analyse.pdf
  python scripts/evidence_pdf.py docs/rapport.md --title "Rapport Stratégique" --open
        """,
    )
    parser.add_argument("input", help="Fichier Markdown (.md) ou HTML (.html) à convertir")
    parser.add_argument("-o", "--output", help="Chemin du PDF de sortie (défaut: même nom .pdf)")
    parser.add_argument("--title", help="Titre sur la page de couverture")
    parser.add_argument("--header", default="Document", help="Texte en haut à droite de chaque page (défaut: 'Document')")
    parser.add_argument("--open", action="store_true", help="Ouvrir le PDF après génération")

    args = parser.parse_args()

    generate_pdf(
        input_path=args.input,
        output_path=args.output,
        title=args.title,
        open_after=args.open,
        header_right=args.header,
    )


if __name__ == "__main__":
    main()
