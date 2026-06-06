#!/usr/bin/env python3
"""
Génère la couverture et compile le PDF du dossier stratégique
"""

import os
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports pour la génération PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import markdown
from bs4 import BeautifulSoup
import re

# Configuration
OUTPUT_DIR = PROJECT_ROOT / "docs" / "reports"
CHARTS_DIR = OUTPUT_DIR / "charts"
FONTS_DIR = PROJECT_ROOT / "fonts"

# Couleurs corporate
COLORS = {
    'primary': HexColor('#2C3E50'),
    'secondary': HexColor('#3498DB'),
    'accent': HexColor('#D4AF37'),  # Gold
    'text': HexColor('#2C3E50'),
    'light_gray': HexColor('#ECF0F1'),
    'white': HexColor('#FFFFFF'),
}

def register_fonts():
    """Enregistre les polices DejaVu"""
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', str(FONTS_DIR / 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(FONTS_DIR / 'DejaVuSans-Bold.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVuSerif', str(FONTS_DIR / 'DejaVuSerif.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold', str(FONTS_DIR / 'DejaVuSerif-Bold.ttf')))
        return True
    except Exception as e:
        print(f"Warning: Could not register fonts: {e}")
        return False


def create_cover_page(c: canvas.Canvas, width: float, height: float):
    """Crée la page de couverture"""
    # Fond principal
    c.setFillColor(COLORS['primary'])
    c.rect(0, 0, width, height, fill=1)
    
    # Bande dorée en haut
    c.setFillColor(COLORS['accent'])
    c.rect(0, height - 1*cm, width, 0.3*cm, fill=1)
    
    # Zone centrale plus claire
    c.setFillColor(HexColor('#34495E'))
    c.roundRect(2*cm, height/2 - 4*cm, width - 4*cm, 10*cm, 10, fill=1)
    
    # Titre principal
    c.setFillColor(COLORS['white'])
    c.setFont('DejaVuSans-Bold', 32)
    c.drawCentredString(width/2, height/2 + 3.5*cm, "KOREV Evidence")
    
    # Sous-titre
    c.setFont('DejaVuSans', 18)
    c.drawCentredString(width/2, height/2 + 2*cm, "Dossier Stratégique")
    
    # Ligne de séparation
    c.setStrokeColor(COLORS['accent'])
    c.setLineWidth(2)
    c.line(width/2 - 5*cm, height/2 + 1*cm, width/2 + 5*cm, height/2 + 1*cm)
    
    # Description
    c.setFont('DejaVuSans', 12)
    c.drawCentredString(width/2, height/2 - 0.5*cm, "Aide à la décision evidence-grade")
    c.drawCentredString(width/2, height/2 - 1.2*cm, "pour l'IA en environnement régulé")
    
    # Badge Evidence-Grade
    c.setFillColor(COLORS['accent'])
    c.roundRect(width/2 - 3*cm, height/2 - 3.5*cm, 6*cm, 1.2*cm, 5, fill=1)
    c.setFillColor(COLORS['primary'])
    c.setFont('DejaVuSans-Bold', 10)
    c.drawCentredString(width/2, height/2 - 3.1*cm, "EVIDENCE-GRADE")
    
    # Informations en bas
    c.setFillColor(COLORS['white'])
    c.setFont('DejaVuSans', 10)
    
    # Classification
    c.drawString(2*cm, 3*cm, "Classification: Confidentiel — Board & Investisseurs")
    
    # Date
    date_str = datetime.now().strftime("%d/%m/%Y")
    c.drawString(2*cm, 2.3*cm, f"Date: {date_str}")
    
    # Version
    c.drawString(2*cm, 1.6*cm, "Version: 1.0 — Méthodologie Evidence-grade")
    
    # Bande dorée en bas
    c.setFillColor(COLORS['accent'])
    c.rect(0, 0, width, 0.3*cm, fill=1)
    
    c.showPage()


def create_toc_page(c: canvas.Canvas, width: float, height: float):
    """Crée la table des matières"""
    c.setFillColor(COLORS['text'])
    
    # Titre
    c.setFont('DejaVuSans-Bold', 24)
    c.drawString(2*cm, height - 3*cm, "Table des matières")
    
    # Ligne
    c.setStrokeColor(COLORS['accent'])
    c.setLineWidth(2)
    c.line(2*cm, height - 3.5*cm, width - 2*cm, height - 3.5*cm)
    
    # Sections
    sections = [
        ("A.", "Executive Summary", 3),
        ("B.", "Reformulation du problème stratégique", 4),
        ("C.", "Hypothèses structurantes", 5),
        ("D.", "Analyse marché (France & UE)", 6),
        ("E.", "Positionnement & différenciation", 8),
        ("F.", "Modèle économique & pricing", 9),
        ("G.", "Prévisionnel financier (3 scénarios)", 10),
        ("H.", "Trajectoire de déploiement", 13),
        ("I.", "Risques majeurs & mitigations", 14),
        ("J.", "Limites, incertitudes et FAIL_CLOSED", 15),
    ]
    
    y = height - 5*cm
    for idx, title, page in sections:
        # Index
        c.setFont('DejaVuSans-Bold', 12)
        c.setFillColor(COLORS['accent'])
        c.drawString(2*cm, y, idx)
        
        # Titre
        c.setFillColor(COLORS['text'])
        c.setFont('DejaVuSans', 12)
        c.drawString(3*cm, y, title)
        
        # Points de conduite
        dots = "." * int((width - 7*cm - c.stringWidth(title, 'DejaVuSans', 12)) / c.stringWidth(".", 'DejaVuSans', 12))
        c.setFillColor(COLORS['light_gray'])
        c.drawString(3*cm + c.stringWidth(title, 'DejaVuSans', 12) + 0.3*cm, y, dots)
        
        # Numéro de page
        c.setFillColor(COLORS['text'])
        c.drawRightString(width - 2*cm, y, str(page))
        
        y -= 0.8*cm
    
    c.showPage()


def markdown_to_paragraphs(md_content: str, styles: dict) -> list:
    """Convertit le Markdown en éléments ReportLab"""
    elements = []
    
    # Convertir Markdown en HTML
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    soup = BeautifulSoup(html, 'html.parser')
    
    for element in soup.children:
        if element.name == 'h1':
            elements.append(PageBreak())
            elements.append(Paragraph(element.get_text(), styles['Heading1']))
            elements.append(Spacer(1, 0.5*cm))
        elif element.name == 'h2':
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph(element.get_text(), styles['Heading2']))
            elements.append(Spacer(1, 0.3*cm))
        elif element.name == 'h3':
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph(element.get_text(), styles['Heading3']))
            elements.append(Spacer(1, 0.2*cm))
        elif element.name == 'p':
            str(element)
            # Vérifier si c'est une image
            if element.find('img'):
                img = element.find('img')
                img_src = img.get('src', '')
                if img_src.startswith('./charts/'):
                    img_path = CHARTS_DIR / img_src.replace('./charts/', '')
                    if img_path.exists():
                        elements.append(Spacer(1, 0.3*cm))
                        elements.append(Image(str(img_path), width=15*cm, height=9*cm))
                        elements.append(Spacer(1, 0.3*cm))
            else:
                elements.append(Paragraph(element.get_text(), styles['Normal']))
                elements.append(Spacer(1, 0.2*cm))
        elif element.name == 'ul':
            for li in element.find_all('li', recursive=False):
                bullet_text = f"• {li.get_text()}"
                elements.append(Paragraph(bullet_text, styles['Bullet']))
        elif element.name == 'ol':
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                num_text = f"{i}. {li.get_text()}"
                elements.append(Paragraph(num_text, styles['Normal']))
        elif element.name == 'table':
            # Traitement des tableaux
            table_data = []
            for row in element.find_all('tr'):
                row_data = []
                for cell in row.find_all(['th', 'td']):
                    cell_text = cell.get_text().strip()
                    # Limiter la largeur du texte
                    if len(cell_text) > 50:
                        cell_text = cell_text[:47] + "..."
                    row_data.append(Paragraph(cell_text, styles['TableCell']))
                if row_data:
                    table_data.append(row_data)
            
            if table_data:
                # Créer le tableau
                col_count = len(table_data[0]) if table_data else 0
                col_width = (17*cm) / max(col_count, 1)
                
                t = Table(table_data, colWidths=[col_width] * col_count)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
                    ('TEXTCOLOR', (0, 0), (-1, 0), COLORS['white']),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, COLORS['light_gray']),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLORS['white'], HexColor('#F8F9FA')]),
                ]))
                elements.append(Spacer(1, 0.3*cm))
                elements.append(t)
                elements.append(Spacer(1, 0.3*cm))
        elif element.name == 'hr':
            elements.append(Spacer(1, 0.5*cm))
        elif element.name == 'blockquote':
            elements.append(Paragraph(element.get_text(), styles['Quote']))
    
    return elements


def create_pdf_from_markdown(md_file: Path, output_file: Path):
    """Crée le PDF complet à partir du Markdown"""
    print(f"Création du PDF : {output_file}")
    
    # Enregistrer les polices
    has_fonts = register_fonts()
    
    # Définir les styles
    styles = getSampleStyleSheet()
    
    # Style personnalisé
    font_name = 'DejaVuSans' if has_fonts else 'Helvetica'
    font_bold = 'DejaVuSans-Bold' if has_fonts else 'Helvetica-Bold'
    
    styles.add(ParagraphStyle(
        name='Heading1Custom',
        parent=styles['Heading1'],
        fontName=font_bold,
        fontSize=22,
        textColor=COLORS['primary'],
        spaceAfter=12,
        spaceBefore=20,
    ))
    
    styles.add(ParagraphStyle(
        name='Heading2Custom',
        parent=styles['Heading2'],
        fontName=font_bold,
        fontSize=16,
        textColor=COLORS['primary'],
        spaceAfter=8,
        spaceBefore=15,
    ))
    
    styles.add(ParagraphStyle(
        name='Heading3Custom',
        parent=styles['Heading3'],
        fontName=font_bold,
        fontSize=12,
        textColor=COLORS['secondary'],
        spaceAfter=6,
        spaceBefore=10,
    ))
    
    styles.add(ParagraphStyle(
        name='NormalCustom',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=COLORS['text'],
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    ))
    
    styles.add(ParagraphStyle(
        name='BulletCustom',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=COLORS['text'],
        leftIndent=20,
        spaceAfter=4,
    ))
    
    styles.add(ParagraphStyle(
        name='TableCellCustom',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        textColor=COLORS['text'],
    ))
    
    styles.add(ParagraphStyle(
        name='QuoteCustom',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=HexColor('#7F8C8D'),
        leftIndent=30,
        rightIndent=30,
        spaceBefore=10,
        spaceAfter=10,
    ))
    
    # Créer le mapping de styles
    style_map = {
        'Heading1': styles['Heading1Custom'],
        'Heading2': styles['Heading2Custom'],
        'Heading3': styles['Heading3Custom'],
        'Normal': styles['NormalCustom'],
        'Bullet': styles['BulletCustom'],
        'TableCell': styles['TableCellCustom'],
        'Quote': styles['QuoteCustom'],
    }
    
    # Lire le contenu Markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Supprimer le front matter YAML
    md_content = re.sub(r'^---\n.*?\n---\n', '', md_content, flags=re.DOTALL)
    
    # Créer le PDF
    width, height = A4
    
    # D'abord créer les pages de couverture et TOC
    c = canvas.Canvas(str(output_file), pagesize=A4)
    create_cover_page(c, width, height)
    create_toc_page(c, width, height)
    c.save()
    
    # Ensuite créer le contenu avec Platypus
    content_file = output_file.parent / "content_temp.pdf"
    doc = SimpleDocTemplate(
        str(content_file),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Convertir le Markdown
    elements = markdown_to_paragraphs(md_content, style_map)
    
    # Générer
    doc.build(elements)
    
    # Fusionner les PDFs (couverture + contenu)
    try:
        from PyPDF2 import PdfMerger
        merger = PdfMerger()
        merger.append(str(output_file))
        merger.append(str(content_file))
        
        final_file = output_file.parent / output_file.name.replace('.pdf', '_final.pdf')
        merger.write(str(final_file))
        merger.close()
        
        # Remplacer
        import shutil
        shutil.move(str(final_file), str(output_file))
        content_file.unlink()
        
        print(f"  → PDF final : {output_file}")
    except ImportError:
        print("  → PyPDF2 non disponible, PDF partiel créé")
        # Utiliser seulement le contenu
        import shutil
        shutil.move(str(content_file), str(output_file))


def main():
    """Point d'entrée"""
    print("=" * 70)
    print("KOREV Evidence — Génération PDF du Dossier Stratégique")
    print("=" * 70)
    
    # Trouver le fichier MD le plus récent
    md_files = list(OUTPUT_DIR.glob("KOREV_Evidence_Dossier_Strategique_*.md"))
    if not md_files:
        print("Erreur: Aucun fichier Markdown trouvé. Exécutez d'abord generate_strategic_dossier.py")
        return
    
    md_file = max(md_files, key=lambda f: f.stat().st_mtime)
    print(f"Fichier source : {md_file.name}")
    
    # Générer le PDF
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"KOREV_Evidence_Dossier_Strategique_{timestamp}.pdf"
    
    create_pdf_from_markdown(md_file, output_file)
    
    print("=" * 70)
    print(f"PDF généré : {output_file}")
    print("=" * 70)
    
    return output_file


if __name__ == "__main__":
    main()
