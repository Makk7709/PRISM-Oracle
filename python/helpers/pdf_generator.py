"""
Professional PDF Generator with full Markdown support.

Converts Markdown content to well-formatted PDFs with:
- Headers (H1-H6)
- Paragraphs with bold, italic, inline code
- Bullet and numbered lists
- Tables
- Code blocks with syntax highlighting
- Blockquotes
- Page numbers and headers
- Professional styling
"""

import re
import os
from io import BytesIO
from typing import Optional, List, Tuple
from datetime import datetime

# ReportLab imports
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm, inch
from reportlab.lib.colors import HexColor, black, gray, white, lightgrey
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, ListFlowable, ListItem, Preformatted,
    Image, HRFlowable
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ═══════════════════════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════════════════════

def create_styles():
    """Create professional styles for the PDF."""
    styles = getSampleStyleSheet()
    
    # Colors
    primary_color = HexColor('#1a365d')  # Dark blue
    secondary_color = HexColor('#2c5282')
    accent_color = HexColor('#3182ce')
    text_color = HexColor('#2d3748')
    light_bg = HexColor('#f7fafc')
    
    # Title style
    styles.add(ParagraphStyle(
        name='DocTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=primary_color,
        spaceAfter=20,
        spaceBefore=0,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
    ))
    
    # H1 style
    styles.add(ParagraphStyle(
        name='H1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=primary_color,
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
        borderColor=accent_color,
    ))
    
    # H2 style
    styles.add(ParagraphStyle(
        name='H2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=secondary_color,
        spaceAfter=10,
        spaceBefore=16,
        fontName='Helvetica-Bold',
    ))
    
    # H3 style
    styles.add(ParagraphStyle(
        name='H3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=secondary_color,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold',
    ))
    
    # H4 style
    styles.add(ParagraphStyle(
        name='H4',
        parent=styles['Heading4'],
        fontSize=11,
        textColor=text_color,
        spaceAfter=6,
        spaceBefore=10,
        fontName='Helvetica-Bold',
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='Body',
        parent=styles['Normal'],
        fontSize=10,
        textColor=text_color,
        spaceAfter=8,
        spaceBefore=0,
        fontName='Helvetica',
        leading=14,
        alignment=TA_JUSTIFY,
    ))
    
    # Blockquote
    styles.add(ParagraphStyle(
        name='BlockQuote',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#4a5568'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=20,
        borderWidth=2,
        borderColor=accent_color,
        borderPadding=10,
        backColor=light_bg,
        fontName='Helvetica-Oblique',
    ))
    
    # Code block
    styles.add(ParagraphStyle(
        name='Code',
        parent=styles['Code'],
        fontSize=9,
        textColor=HexColor('#1a202c'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=10,
        rightIndent=10,
        backColor=HexColor('#edf2f7'),
        borderWidth=1,
        borderColor=HexColor('#e2e8f0'),
        borderPadding=8,
        fontName='Courier',
        leading=12,
    ))
    
    # Inline code
    styles.add(ParagraphStyle(
        name='InlineCode',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#c53030'),
        backColor=HexColor('#fed7d7'),
        fontName='Courier',
    ))
    
    # List item
    styles.add(ParagraphStyle(
        name='ListItem',
        parent=styles['Normal'],
        fontSize=10,
        textColor=text_color,
        spaceAfter=4,
        spaceBefore=2,
        leftIndent=20,
        fontName='Helvetica',
    ))
    
    # Table header
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=white,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    ))
    
    # Table cell
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=9,
        textColor=text_color,
        fontName='Helvetica',
        alignment=TA_LEFT,
    ))
    
    # Footer
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=gray,
        fontName='Helvetica',
        alignment=TA_CENTER,
    ))
    
    return styles


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN PARSER
# ═══════════════════════════════════════════════════════════════════════════════

class MarkdownToPDF:
    """Convert Markdown to PDF elements."""
    
    def __init__(self, styles):
        self.styles = styles
        self.elements = []
        
    def convert_inline(self, text: str) -> str:
        """Convert inline markdown (bold, italic, code, links)."""
        # Escape XML characters first
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        
        # Italic: *text* or _text_
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'(?<![_\w])_(.+?)_(?![_\w])', r'<i>\1</i>', text)
        
        # Inline code: `code`
        text = re.sub(r'`([^`]+)`', r'<font name="Courier" color="#c53030">\1</font>', text)
        
        # Links: [text](url) - just show text in blue
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'<font color="#3182ce"><u>\1</u></font>', text)
        
        # Strikethrough: ~~text~~
        text = re.sub(r'~~(.+?)~~', r'<strike>\1</strike>', text)
        
        return text
    
    def parse_table(self, lines: List[str]) -> Optional[Table]:
        """Parse markdown table into ReportLab Table."""
        if len(lines) < 2:
            return None
        
        # Parse header
        header_line = lines[0].strip()
        if not header_line.startswith('|'):
            return None
        
        headers = [cell.strip() for cell in header_line.split('|')[1:-1]]
        
        # Skip separator line
        # Parse rows
        data = [headers]
        for line in lines[2:]:
            if line.strip().startswith('|'):
                cells = [cell.strip() for cell in line.strip().split('|')[1:-1]]
                if cells:
                    data.append(cells)
        
        if not data:
            return None
        
        # Create table with styles
        table = Table(data, repeatRows=1)
        
        # Style the table
        style = TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Body style
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('TEXTCOLOR', (0, 1), (-1, -1), HexColor('#2d3748')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f7fafc')]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e0')),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ])
        
        table.setStyle(style)
        return table
    
    def parse(self, markdown: str) -> List:
        """Parse markdown content into PDF elements."""
        self.elements = []
        lines = markdown.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                i += 1
                continue
            
            # Code block (```)
            if line.strip().startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                code_text = '\n'.join(code_lines)
                self.elements.append(Preformatted(code_text, self.styles['Code']))
                self.elements.append(Spacer(1, 6))
                i += 1
                continue
            
            # Table detection
            if line.strip().startswith('|') and i + 1 < len(lines):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i])
                    i += 1
                table = self.parse_table(table_lines)
                if table:
                    self.elements.append(Spacer(1, 6))
                    self.elements.append(table)
                    self.elements.append(Spacer(1, 10))
                continue
            
            # Headers
            if line.startswith('######'):
                text = self.convert_inline(line[6:].strip())
                self.elements.append(Paragraph(text, self.styles['H4']))
            elif line.startswith('#####'):
                text = self.convert_inline(line[5:].strip())
                self.elements.append(Paragraph(text, self.styles['H4']))
            elif line.startswith('####'):
                text = self.convert_inline(line[4:].strip())
                self.elements.append(Paragraph(text, self.styles['H4']))
            elif line.startswith('###'):
                text = self.convert_inline(line[3:].strip())
                self.elements.append(Paragraph(text, self.styles['H3']))
            elif line.startswith('##'):
                text = self.convert_inline(line[2:].strip())
                self.elements.append(Paragraph(text, self.styles['H2']))
            elif line.startswith('#'):
                text = self.convert_inline(line[1:].strip())
                self.elements.append(Paragraph(text, self.styles['H1']))
            
            # Blockquote
            elif line.strip().startswith('>'):
                quote_text = line.strip()[1:].strip()
                text = self.convert_inline(quote_text)
                self.elements.append(Paragraph(text, self.styles['BlockQuote']))
            
            # Horizontal rule
            elif line.strip() in ['---', '***', '___']:
                self.elements.append(HRFlowable(
                    width="100%",
                    thickness=1,
                    color=HexColor('#e2e8f0'),
                    spaceBefore=10,
                    spaceAfter=10
                ))
            
            # Bullet list
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                list_items = []
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    item_text = lines[i].strip()[2:]
                    text = self.convert_inline(item_text)
                    list_items.append(ListItem(Paragraph(text, self.styles['ListItem']), bulletColor=HexColor('#3182ce')))
                    i += 1
                self.elements.append(ListFlowable(list_items, bulletType='bullet', start='•'))
                self.elements.append(Spacer(1, 6))
                continue
            
            # Numbered list
            elif re.match(r'^\d+\.\s', line.strip()):
                list_items = []
                while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                    item_text = re.sub(r'^\d+\.\s', '', lines[i].strip())
                    text = self.convert_inline(item_text)
                    list_items.append(ListItem(Paragraph(text, self.styles['ListItem'])))
                    i += 1
                self.elements.append(ListFlowable(list_items, bulletType='1'))
                self.elements.append(Spacer(1, 6))
                continue
            
            # Regular paragraph
            else:
                text = self.convert_inline(line.strip())
                if text:
                    self.elements.append(Paragraph(text, self.styles['Body']))
            
            i += 1
        
        return self.elements


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def add_page_number(canvas, doc):
    """Add page number and header to each page."""
    canvas.saveState()
    
    # Page number
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(gray)
    canvas.drawRightString(doc.pagesize[0] - 2*cm, 1.5*cm, text)
    
    # Footer line
    canvas.setStrokeColor(HexColor('#e2e8f0'))
    canvas.setLineWidth(0.5)
    canvas.line(2*cm, 2*cm, doc.pagesize[0] - 2*cm, 2*cm)
    
    # Header line (subtle)
    canvas.line(2*cm, doc.pagesize[1] - 2*cm, doc.pagesize[0] - 2*cm, doc.pagesize[1] - 2*cm)
    
    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdf(
    content: str,
    output_path: str,
    title: Optional[str] = None,
    author: str = "Korev Evidence",
    pagesize = A4
) -> str:
    """
    Generate a professional PDF from Markdown content.
    
    Args:
        content: Markdown content to convert
        output_path: Path for the output PDF
        title: Optional document title (added as first element)
        author: PDF metadata author
        pagesize: Page size (A4 or letter)
    
    Returns:
        Path to the generated PDF
    """
    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=pagesize,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
        title=title or "Document",
        author=author
    )
    
    # Create styles
    styles = create_styles()
    
    # Parse markdown
    parser = MarkdownToPDF(styles)
    elements = []
    
    # Add title if provided
    if title:
        elements.append(Paragraph(title, styles['DocTitle']))
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=HexColor('#3182ce'),
            spaceBefore=10,
            spaceAfter=20
        ))
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append(Paragraph(
        f"<font color='#718096' size='9'>Generated: {timestamp}</font>",
        styles['Body']
    ))
    elements.append(Spacer(1, 20))
    
    # Add content
    elements.extend(parser.parse(content))
    
    # Build PDF
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    return output_path


def markdown_to_pdf_bytes(
    content: str,
    title: Optional[str] = None,
    author: str = "Korev Evidence"
) -> bytes:
    """
    Generate PDF as bytes (for streaming or in-memory use).
    
    Args:
        content: Markdown content
        title: Optional document title
        author: PDF metadata author
    
    Returns:
        PDF as bytes
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
        title=title or "Document",
        author=author
    )
    
    styles = create_styles()
    parser = MarkdownToPDF(styles)
    elements = []
    
    if title:
        elements.append(Paragraph(title, styles['DocTitle']))
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=HexColor('#3182ce'),
            spaceBefore=10,
            spaceAfter=20
        ))
    
    elements.extend(parser.parse(content))
    
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    return buffer.getvalue()
