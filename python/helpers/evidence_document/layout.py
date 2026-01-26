"""
Evidence Document Layout Engine — ReportLab rendering.

Génère des styles ReportLab de manière déterministe depuis un Template.
Gère: header/footer, watermark, numérotation, tables, code blocks.
"""

from io import BytesIO
from typing import Optional, List, Tuple, Callable
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, gray, Color
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, Preformatted,
    HRFlowable, KeepTogether, Flowable
)
from reportlab.pdfgen import canvas as pdf_canvas

from .templates import Template
from .ast import ConfidentialityLevel


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM FLOWABLES
# ═══════════════════════════════════════════════════════════════════════════════

class WatermarkFlowable(Flowable):
    """Watermark diagonal sur la page."""
    
    def __init__(self, text: str, color: Color = None):
        super().__init__()
        self.text = text
        self.color = color or HexColor("#E0E0E0")
    
    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(self.color)
        canvas.setFont("Helvetica-Bold", 60)
        canvas.rotate(45)
        canvas.drawString(100, -200, self.text)
        canvas.restoreState()


class CoverPage(Flowable):
    """Page de garde Evidence."""
    
    def __init__(self, title: str, template: Template, metadata: dict,
                 style: str = "standard"):
        super().__init__()
        self.title = title
        self.template = template
        self.metadata = metadata
        self.style = style
        # Use smaller dimensions to fit in frame
        self.width = 0
        self.height = 0
    
    def wrap(self, availWidth, availHeight):
        # Return dimensions that fit in the available space
        self.width = availWidth
        self.height = min(availHeight - 50, 600)  # Leave room for page break
        return (self.width, self.height)
    
    def draw(self):
        canvas = self.canv
        canvas.saveState()
        
        primary = HexColor(self.template.primary_color)
        accent = HexColor(self.template.accent_color)
        
        if self.style == "elaborate" and self.width > 100:
            # Ligne accent
            canvas.setStrokeColor(accent)
            canvas.setLineWidth(3)
            canvas.line(0, self.height * 0.6, self.width, self.height * 0.6)
        
        # Titre principal
        title_font = self.template.title_font
        title_size = 28
        canvas.setFillColor(primary)
        canvas.setFont(title_font, title_size)
        
        # Word wrap du titre avec mesure réelle
        title_lines = self._wrap_text(self.title, self.width - 1*cm, title_font, title_size)
        y_pos = self.height * 0.7
        for line in title_lines:
            canvas.drawString(0, y_pos, line)
            y_pos -= 35
        
        # Métadonnées
        canvas.setFillColor(HexColor(self.template.text_color))
        canvas.setFont(self.template.body_font, 11)
        
        meta_y = self.height * 0.35
        
        if self.metadata.get("confidentiality"):
            conf_label = self.template.confidential_labels.get(
                self.metadata["confidentiality"], ""
            )
            if conf_label:
                canvas.setFillColor(HexColor("#C53030"))
                canvas.setFont(self.template.title_font, 12)
                canvas.drawString(0, meta_y, conf_label)
                meta_y -= 22
        
        canvas.setFillColor(HexColor(self.template.text_color))
        canvas.setFont(self.template.body_font, 10)
        
        if self.metadata.get("author"):
            canvas.drawString(0, meta_y, f"Auteur: {self.metadata['author']}")
            meta_y -= 16
        
        if self.metadata.get("version"):
            canvas.drawString(0, meta_y, f"Version: {self.metadata['version']}")
            meta_y -= 16
        
        if self.metadata.get("date"):
            canvas.drawString(0, meta_y, f"Date: {self.metadata['date']}")
            meta_y -= 16
        
        # Pied de page
        canvas.setFont(self.template.body_font, 9)
        canvas.setFillColor(gray)
        canvas.drawString(0, 10, "Généré par Korev Evidence")
        
        canvas.restoreState()
    
    def _wrap_text(self, text: str, max_width: float, font_name: str, font_size: int) -> List[str]:
        """
        Wrap text to fit within width using actual font metrics.
        
        Uses pdfmetrics.stringWidth for accurate measurement.
        """
        from reportlab.pdfbase import pdfmetrics
        
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        space_width = pdfmetrics.stringWidth(' ', font_name, font_size)
        
        for word in words:
            word_width = pdfmetrics.stringWidth(word, font_name, font_size)
            
            # Check if word fits on current line
            if current_line:
                test_width = current_width + space_width + word_width
            else:
                test_width = word_width
            
            if test_width <= max_width:
                current_line.append(word)
                current_width = test_width
            else:
                # Start new line
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text[:50] + "..."]  # Fallback for very long words


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_styles(template: Template) -> dict:
    """
    Génère les styles ReportLab depuis un Template.
    Retourne un dictionnaire de ParagraphStyle.
    """
    base_styles = getSampleStyleSheet()
    
    # Couleurs
    primary = HexColor(template.primary_color)
    secondary = HexColor(template.secondary_color)
    accent = HexColor(template.accent_color)
    text_color = HexColor(template.text_color)
    light_bg = HexColor(template.light_bg)
    
    styles = {}
    
    # Titre document
    styles['DocTitle'] = ParagraphStyle(
        name='DocTitle',
        parent=base_styles['Heading1'],
        fontSize=template.title_size,
        textColor=primary,
        spaceAfter=20,
        spaceBefore=0,
        fontName=template.title_font,
        alignment=TA_LEFT,
    )
    
    # Headers H1-H4
    styles['H1'] = ParagraphStyle(
        name='H1',
        parent=base_styles['Heading1'],
        fontSize=template.h1_size,
        textColor=primary,
        spaceAfter=12,
        spaceBefore=20,
        fontName=template.title_font,
    )
    
    styles['H2'] = ParagraphStyle(
        name='H2',
        parent=base_styles['Heading2'],
        fontSize=template.h2_size,
        textColor=secondary,
        spaceAfter=10,
        spaceBefore=16,
        fontName=template.title_font,
    )
    
    styles['H3'] = ParagraphStyle(
        name='H3',
        parent=base_styles['Heading3'],
        fontSize=template.h3_size,
        textColor=secondary,
        spaceAfter=8,
        spaceBefore=12,
        fontName=template.title_font,
    )
    
    styles['H4'] = ParagraphStyle(
        name='H4',
        parent=base_styles['Heading4'],
        fontSize=template.h4_size,
        textColor=text_color,
        spaceAfter=6,
        spaceBefore=10,
        fontName=template.title_font,
    )
    
    # Body
    styles['Body'] = ParagraphStyle(
        name='Body',
        parent=base_styles['Normal'],
        fontSize=template.body_size,
        textColor=text_color,
        spaceAfter=8,
        spaceBefore=0,
        fontName=template.body_font,
        leading=template.body_size + 4,
        alignment=TA_JUSTIFY,
    )
    
    # Blockquote
    styles['BlockQuote'] = ParagraphStyle(
        name='BlockQuote',
        parent=base_styles['Normal'],
        fontSize=template.body_size,
        textColor=HexColor('#4a5568'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=20,
        borderWidth=2,
        borderColor=accent,
        borderPadding=10,
        backColor=light_bg,
        fontName=template.body_font,
    )
    
    # Code
    styles['Code'] = ParagraphStyle(
        name='Code',
        parent=base_styles['Code'],
        fontSize=template.body_size - 1,
        textColor=HexColor('#1a202c'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=10,
        rightIndent=10,
        backColor=HexColor('#edf2f7'),
        borderWidth=1,
        borderColor=HexColor('#e2e8f0'),
        borderPadding=8,
        fontName=template.code_font,
        leading=template.body_size + 2,
    )
    
    # List item
    styles['ListItem'] = ParagraphStyle(
        name='ListItem',
        parent=base_styles['Normal'],
        fontSize=template.body_size,
        textColor=text_color,
        spaceAfter=4,
        spaceBefore=2,
        leftIndent=20,
        fontName=template.body_font,
    )
    
    # Callout styles
    for callout_type, color in [
        ('info', '#3182ce'),
        ('warning', '#d69e2e'),
        ('danger', '#e53e3e'),
        ('success', '#38a169')
    ]:
        styles[f'Callout_{callout_type}'] = ParagraphStyle(
            name=f'Callout_{callout_type}',
            parent=base_styles['Normal'],
            fontSize=template.body_size,
            textColor=HexColor('#2d3748'),
            spaceAfter=10,
            spaceBefore=10,
            leftIndent=15,
            borderWidth=3,
            borderColor=HexColor(color),
            borderPadding=10,
            backColor=HexColor('#f7fafc'),
            fontName=template.body_font,
        )
    
    # Table styles
    styles['TableHeader'] = ParagraphStyle(
        name='TableHeader',
        parent=base_styles['Normal'],
        fontSize=template.body_size - 1,
        textColor=white,
        fontName=template.title_font,
        alignment=TA_CENTER,
    )
    
    styles['TableCell'] = ParagraphStyle(
        name='TableCell',
        parent=base_styles['Normal'],
        fontSize=template.body_size - 1,
        textColor=text_color,
        fontName=template.body_font,
        alignment=TA_LEFT,
    )
    
    # Sources/References
    styles['Source'] = ParagraphStyle(
        name='Source',
        parent=base_styles['Normal'],
        fontSize=template.body_size - 2,
        textColor=HexColor('#718096'),
        spaceAfter=4,
        leftIndent=20,
        fontName=template.body_font,
    )
    
    # Assumption
    styles['Assumption'] = ParagraphStyle(
        name='Assumption',
        parent=base_styles['Normal'],
        fontSize=template.body_size - 1,
        textColor=HexColor('#744210'),
        spaceAfter=4,
        leftIndent=15,
        backColor=HexColor('#fffaf0'),
        borderPadding=5,
        fontName=template.body_font,
    )
    
    return styles


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════

class PageInfo:
    """Stocke les infos de pagination (pour total pages)."""
    def __init__(self):
        self.page_count = 0


def create_page_callback(
    template: Template,
    confidentiality: Optional[ConfidentialityLevel] = None,
    watermark: Optional[str] = None,
    page_info: Optional[PageInfo] = None
) -> Callable:
    """
    Crée le callback pour header/footer/watermark sur chaque page.
    """
    
    def draw_page(canvas: pdf_canvas.Canvas, doc):
        canvas.saveState()
        
        width, height = doc.pagesize
        page_num = canvas.getPageNumber()
        
        if page_info:
            page_info.page_count = max(page_info.page_count, page_num)
        
        primary = HexColor(template.primary_color)
        accent = HexColor(template.accent_color)
        
        # Watermark
        if watermark:
            canvas.setFillColor(HexColor("#E8E8E8"))
            canvas.setFont("Helvetica-Bold", 50)
            canvas.saveState()
            canvas.translate(width/2, height/2)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, watermark)
            canvas.restoreState()
        
        # Header
        if template.show_header:
            # Ligne
            canvas.setStrokeColor(accent)
            canvas.setLineWidth(1)
            canvas.line(
                template.left_margin * cm,
                height - template.top_margin * cm + 0.5*cm,
                width - template.right_margin * cm,
                height - template.top_margin * cm + 0.5*cm
            )
            
            # Texte header gauche
            if template.header_text:
                canvas.setFont(template.title_font, 8)
                canvas.setFillColor(primary)
                canvas.drawString(
                    template.left_margin * cm,
                    height - template.top_margin * cm + 0.8*cm,
                    template.header_text
                )
            
            # Confidentialité à droite
            if confidentiality:
                conf_label = template.confidential_labels.get(
                    confidentiality.value, ""
                )
                if conf_label:
                    canvas.setFont(template.title_font, 8)
                    canvas.setFillColor(HexColor("#C53030"))
                    canvas.drawRightString(
                        width - template.right_margin * cm,
                        height - template.top_margin * cm + 0.8*cm,
                        conf_label
                    )
        
        # Footer
        if template.show_footer:
            # Ligne
            canvas.setStrokeColor(HexColor('#e2e8f0'))
            canvas.setLineWidth(0.5)
            canvas.line(
                template.left_margin * cm,
                template.bottom_margin * cm - 0.5*cm,
                width - template.right_margin * cm,
                template.bottom_margin * cm - 0.5*cm
            )
            
            # Texte footer centre
            if template.footer_text:
                footer_text = template.footer_text.replace("{page}", str(page_num))
                # {total} sera remplacé en 2-pass si implémenté
                footer_text = footer_text.replace("{total}", "?")
                canvas.setFont(template.body_font, 8)
                canvas.setFillColor(gray)
                canvas.drawCentredString(
                    width / 2,
                    template.bottom_margin * cm - 0.8*cm,
                    footer_text
                )
            
            # Numéro de page à droite
            if template.show_page_numbers:
                canvas.setFont(template.body_font, 8)
                canvas.setFillColor(gray)
                canvas.drawRightString(
                    width - template.right_margin * cm,
                    template.bottom_margin * cm - 0.8*cm,
                    f"Page {page_num}"
                )
        
        canvas.restoreState()
    
    return draw_page


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_table(
    headers: List[str],
    rows: List[List[str]],
    template: Template,
    caption: Optional[str] = None
) -> List:
    """Construit une table ReportLab avec styles."""
    
    elements = []
    
    # Sanitize data
    safe_headers = [_sanitize_text(h) for h in headers]
    safe_rows = [[_sanitize_text(cell) for cell in row] for row in rows]
    
    # Pad rows to match header length
    for row in safe_rows:
        while len(row) < len(safe_headers):
            row.append("")
        while len(row) > len(safe_headers):
            row.pop()
    
    data = [safe_headers] + safe_rows
    
    table = Table(data, repeatRows=1)
    
    header_bg = HexColor(template.header_bg)
    light_bg = HexColor(template.light_bg)
    text_color = HexColor(template.text_color)
    
    style = TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), template.title_font),
        ('FONTSIZE', (0, 0), (-1, 0), template.body_size - 1),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Body
        ('BACKGROUND', (0, 1), (-1, -1), white),
        ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
        ('FONTNAME', (0, 1), (-1, -1), template.body_font),
        ('FONTSIZE', (0, 1), (-1, -1), template.body_size - 1),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_bg]),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e0')),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ])
    
    table.setStyle(style)
    elements.append(table)
    
    # Caption
    if caption:
        styles = generate_styles(template)
        cap_style = ParagraphStyle(
            name='TableCaption',
            parent=styles['Body'],
            fontSize=template.body_size - 2,
            textColor=gray,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=12,
        )
        elements.append(Paragraph(f"<i>{_sanitize_text(caption)}</i>", cap_style))
    
    return elements


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _sanitize_text(text: str) -> str:
    """Sanitize text for ReportLab XML."""
    if not text:
        return ""
    
    # Remove control characters
    import unicodedata
    result = []
    for char in text:
        cat = unicodedata.category(char)
        if cat.startswith('C') and char not in '\n\t':
            continue
        result.append(char)
    
    text = ''.join(result)
    
    # XML escape
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    return text


# NOTE: format_inline() has been REMOVED.
# All text formatting now goes through renderer.py:spans_to_rl_xml()
# which uses TextSpan for safe, deterministic formatting.
# 
# If you need inline formatting:
#   1. Use TextSpan in your AST: Paragraph(content=[TextSpan(text="bold", bold=True)])
#   2. Or use plain text: Paragraph(content="plain text")
#
# NEVER use regex-based markdown parsing for board-level documents.
