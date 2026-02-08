"""
Professional PDF Generator with full Markdown support and Templates.

Converts Markdown content to well-formatted PDFs with:
- Headers (H1-H6)
- Paragraphs with bold, italic, inline code
- Bullet and numbered lists
- Tables
- Code blocks with syntax highlighting
- Blockquotes
- Page numbers and headers
- Professional styling

Templates disponibles:
- consulting_premium: Rapport stratégique premium KOREV Evidence
- legal_formal: Document juridique style greffe/tribunal
- scientific_academic: Rapport scientifique/académique
- patent: Rédaction de brevet style INPI/EPO
- financial: Rapport financier/audit
- executive: Note de synthèse executive
- medical: Rapport médical/clinique
- technical: Documentation technique
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

# Import templates
from python.helpers.pdf_templates import PDFTemplate, get_template, detect_template, TEMPLATES


# ═══════════════════════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════════════════════

def create_styles(template: Optional[PDFTemplate] = None):
    """Create professional styles for the PDF based on template."""
    styles = getSampleStyleSheet()
    
    # Use template colors or defaults
    if template:
        primary_color = HexColor(template.primary_color)
        secondary_color = HexColor(template.secondary_color)
        accent_color = HexColor(template.accent_color)
        text_color = HexColor(template.text_color)
        light_bg = HexColor(template.light_bg)
        title_font = template.title_font
        body_font = template.body_font
        code_font = template.code_font
        title_size = template.title_size
        h1_size = template.h1_size
        h2_size = template.h2_size
        h3_size = template.h3_size
        body_size = template.body_size
    else:
        primary_color = HexColor('#1a365d')
        secondary_color = HexColor('#2c5282')
        accent_color = HexColor('#3182ce')
        text_color = HexColor('#2d3748')
        light_bg = HexColor('#f7fafc')
        title_font = 'Helvetica-Bold'
        body_font = 'Helvetica'
        code_font = 'Courier'
        title_size = 24
        h1_size = 18
        h2_size = 14
        h3_size = 12
        body_size = 10
    
    # Title style
    styles.add(ParagraphStyle(
        name='DocTitle',
        parent=styles['Heading1'],
        fontSize=title_size,
        textColor=primary_color,
        spaceAfter=20,
        spaceBefore=0,
        fontName=title_font,
        alignment=TA_LEFT,
    ))
    
    # H1 style
    styles.add(ParagraphStyle(
        name='H1',
        parent=styles['Heading1'],
        fontSize=h1_size,
        textColor=primary_color,
        spaceAfter=12,
        spaceBefore=20,
        fontName=title_font,
        borderWidth=0,
        borderPadding=0,
        borderColor=accent_color,
    ))
    
    # H2 style
    styles.add(ParagraphStyle(
        name='H2',
        parent=styles['Heading2'],
        fontSize=h2_size,
        textColor=secondary_color,
        spaceAfter=10,
        spaceBefore=16,
        fontName=title_font,
    ))
    
    # H3 style
    styles.add(ParagraphStyle(
        name='H3',
        parent=styles['Heading3'],
        fontSize=h3_size,
        textColor=secondary_color,
        spaceAfter=8,
        spaceBefore=12,
        fontName=title_font,
    ))
    
    # H4 style
    styles.add(ParagraphStyle(
        name='H4',
        parent=styles['Heading4'],
        fontSize=h3_size - 1,
        textColor=text_color,
        spaceAfter=6,
        spaceBefore=10,
        fontName=title_font,
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='Body',
        parent=styles['Normal'],
        fontSize=body_size,
        textColor=text_color,
        spaceAfter=8,
        spaceBefore=0,
        fontName=body_font,
        leading=body_size + 4,
        alignment=TA_JUSTIFY,
    ))
    
    # Blockquote
    styles.add(ParagraphStyle(
        name='BlockQuote',
        parent=styles['Normal'],
        fontSize=body_size,
        textColor=HexColor('#4a5568'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=20,
        borderWidth=2,
        borderColor=accent_color,
        borderPadding=10,
        backColor=light_bg,
        fontName=body_font + '-Oblique' if 'Helvetica' in body_font else body_font,
    ))
    
    # Code block - use unique name to avoid conflict with built-in
    styles.add(ParagraphStyle(
        name='CodeBlock',
        parent=styles['Normal'],
        fontSize=body_size - 1,
        textColor=HexColor('#1a202c'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=10,
        rightIndent=10,
        backColor=HexColor('#edf2f7'),
        borderWidth=1,
        borderColor=HexColor('#e2e8f0'),
        borderPadding=8,
        fontName=code_font,
        leading=body_size + 2,
    ))
    
    # Inline code
    styles.add(ParagraphStyle(
        name='InlineCode',
        parent=styles['Normal'],
        fontSize=body_size - 1,
        textColor=HexColor('#c53030'),
        backColor=HexColor('#fed7d7'),
        fontName=code_font,
    ))
    
    # List item
    styles.add(ParagraphStyle(
        name='ListItem',
        parent=styles['Normal'],
        fontSize=body_size,
        textColor=text_color,
        spaceAfter=4,
        spaceBefore=2,
        leftIndent=20,
        fontName=body_font,
    ))
    
    # Table header
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=body_size - 1,
        textColor=white,
        fontName=title_font,
        alignment=TA_CENTER,
    ))
    
    # Table cell
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=body_size - 1,
        textColor=text_color,
        fontName=body_font,
        alignment=TA_LEFT,
    ))
    
    # Footer
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=gray,
        fontName=body_font,
        alignment=TA_CENTER,
    ))
    
    # Confidential notice style
    styles.add(ParagraphStyle(
        name='Confidential',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#c53030'),
        fontName=title_font,
        alignment=TA_CENTER,
    ))
    
    # Section header for suggested sections
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=h2_size,
        textColor=primary_color,
        spaceAfter=10,
        spaceBefore=20,
        fontName=title_font,
        borderWidth=0,
        borderPadding=0,
        borderBottomWidth=1,
        borderBottomColor=accent_color,
    ))
    
    return styles, template


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN PARSER
# ═══════════════════════════════════════════════════════════════════════════════

class MarkdownToPDF:
    """Convert Markdown to PDF elements with robust error handling."""
    
    def __init__(self, styles, template: Optional[PDFTemplate] = None):
        self.styles = styles
        self.template = template
        self.elements = []
        
    def sanitize_text(self, text: str) -> str:
        """Sanitize text for ReportLab XML parsing."""
        if not text:
            return ""
        
        # Remove problematic Unicode characters that ReportLab can't handle
        # Keep common emojis but replace others
        import unicodedata
        
        result = []
        for char in text:
            try:
                # Check if character is printable
                cat = unicodedata.category(char)
                if cat.startswith('C') and char not in '\n\t':
                    # Control character - skip
                    continue
                result.append(char)
            except:
                continue
        
        text = ''.join(result)
        
        # Escape XML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Fix common problematic patterns
        text = text.replace('\x00', '')  # Null bytes
        text = text.replace('\r\n', '\n')  # Windows line endings
        text = text.replace('\r', '\n')
        
        return text
        
    def convert_inline(self, text: str) -> str:
        """Convert inline markdown (bold, italic, code, links)."""
        if not text:
            return ""
        
        # Sanitize first
        text = self.sanitize_text(text)
        
        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text, flags=re.DOTALL)
        
        # Italic: *text* or _text_ (be careful not to break bold)
        text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'<i>\1</i>', text)
        
        # Inline code: `code`
        text = re.sub(r'`([^`]+)`', r'<font name="Courier" color="#c53030">\1</font>', text)
        
        # Links: [text](url) - just show text in blue
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'<font color="#3182ce"><u>\1</u></font>', text)
        
        # Strikethrough: ~~text~~
        text = re.sub(r'~~(.+?)~~', r'<strike>\1</strike>', text, flags=re.DOTALL)
        
        return text
    
    def safe_paragraph(self, text: str, style) -> Optional[Paragraph]:
        """Create a Paragraph with error handling."""
        try:
            if not text or not text.strip():
                return None
            return Paragraph(text, style)
        except Exception as e:
            # Fallback: strip all formatting and use plain text
            try:
                plain_text = re.sub(r'<[^>]+>', '', text)
                plain_text = self.sanitize_text(plain_text)
                if plain_text.strip():
                    return Paragraph(plain_text, style)
            except:
                pass
            return None
    
    def parse_table(self, lines: List[str], template: Optional[PDFTemplate] = None) -> Optional[Table]:
        """Parse markdown table into ReportLab Table."""
        try:
            if len(lines) < 2:
                return None
            
            # Parse header
            header_line = lines[0].strip()
            if not header_line.startswith('|'):
                return None
            
            headers = [self.sanitize_text(cell.strip()) for cell in header_line.split('|')[1:-1]]
            if not headers:
                return None
            
            # Skip separator line (line[1])
            # Parse rows
            data = [headers]
            for line in lines[2:]:
                if line.strip().startswith('|'):
                    cells = [self.sanitize_text(cell.strip()) for cell in line.strip().split('|')[1:-1]]
                    # Pad cells to match header count
                    while len(cells) < len(headers):
                        cells.append('')
                    if cells:
                        data.append(cells[:len(headers)])  # Trim excess columns
            
            if len(data) < 1:
                return None
            
            # Get colors from template
            if template:
                header_bg = HexColor(template.header_bg)
                light_bg = HexColor(template.light_bg)
                text_color = HexColor(template.text_color)
            else:
                header_bg = HexColor('#2c5282')
                light_bg = HexColor('#f7fafc')
                text_color = HexColor('#2d3748')
            
            # Create table with styles
            table = Table(data, repeatRows=1)
            
            # Style the table
            style = TableStyle([
                # Header style
                ('BACKGROUND', (0, 0), (-1, 0), header_bg),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Body style
                ('BACKGROUND', (0, 1), (-1, -1), white),
                ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_bg]),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
                ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e0')),
                
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                
                # Word wrap
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ])
            
            table.setStyle(style)
            return table
        except Exception as e:
            # Table parsing failed - return None
            return None
    
    def parse(self, markdown: str) -> List:
        """Parse markdown content into PDF elements with robust error handling."""
        self.elements = []
        
        if not markdown:
            return self.elements
        
        # Normalize line endings
        markdown = markdown.replace('\r\n', '\n').replace('\r', '\n')
        lines = markdown.split('\n')
        i = 0
        
        while i < len(lines):
            try:
                line = lines[i]
                
                # Skip empty lines but add small spacing
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
                    if code_text.strip():
                        try:
                            # Sanitize code for display
                            safe_code = self.sanitize_text(code_text)
                            self.elements.append(Preformatted(safe_code, self.styles['CodeBlock']))
                            self.elements.append(Spacer(1, 6))
                        except:
                            # Fallback: add as plain paragraph
                            para = self.safe_paragraph(code_text, self.styles['Body'])
                            if para:
                                self.elements.append(para)
                    i += 1
                    continue
                
                # Table detection
                if line.strip().startswith('|') and i + 1 < len(lines):
                    table_lines = []
                    while i < len(lines) and lines[i].strip().startswith('|'):
                        table_lines.append(lines[i])
                        i += 1
                    table = self.parse_table(table_lines, self.template)
                    if table:
                        self.elements.append(Spacer(1, 6))
                        self.elements.append(table)
                        self.elements.append(Spacer(1, 10))
                    continue
                
                # Headers
                if line.startswith('######'):
                    text = self.convert_inline(line[6:].strip())
                    para = self.safe_paragraph(text, self.styles['H4'])
                    if para:
                        self.elements.append(para)
                elif line.startswith('#####'):
                    text = self.convert_inline(line[5:].strip())
                    para = self.safe_paragraph(text, self.styles['H4'])
                    if para:
                        self.elements.append(para)
                elif line.startswith('####'):
                    text = self.convert_inline(line[4:].strip())
                    para = self.safe_paragraph(text, self.styles['H4'])
                    if para:
                        self.elements.append(para)
                elif line.startswith('###'):
                    text = self.convert_inline(line[3:].strip())
                    para = self.safe_paragraph(text, self.styles['H3'])
                    if para:
                        self.elements.append(para)
                elif line.startswith('##'):
                    text = self.convert_inline(line[2:].strip())
                    para = self.safe_paragraph(text, self.styles['H2'])
                    if para:
                        self.elements.append(para)
                elif line.startswith('#'):
                    text = self.convert_inline(line[1:].strip())
                    para = self.safe_paragraph(text, self.styles['H1'])
                    if para:
                        self.elements.append(para)
                
                # Blockquote
                elif line.strip().startswith('>'):
                    quote_text = line.strip()[1:].strip()
                    text = self.convert_inline(quote_text)
                    para = self.safe_paragraph(text, self.styles['BlockQuote'])
                    if para:
                        self.elements.append(para)
                
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
                        para = self.safe_paragraph(text, self.styles['ListItem'])
                        if para:
                            list_items.append(ListItem(para, bulletColor=HexColor('#3182ce')))
                        i += 1
                    if list_items:
                        try:
                            self.elements.append(ListFlowable(list_items, bulletType='bullet', start='•'))
                        except:
                            # Fallback: add items as regular paragraphs with bullet
                            for item in list_items:
                                self.elements.append(item.value)
                        self.elements.append(Spacer(1, 6))
                    continue
                
                # Numbered list
                elif re.match(r'^\d+\.\s', line.strip()):
                    list_items = []
                    while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                        item_text = re.sub(r'^\d+\.\s', '', lines[i].strip())
                        text = self.convert_inline(item_text)
                        para = self.safe_paragraph(text, self.styles['ListItem'])
                        if para:
                            list_items.append(ListItem(para))
                        i += 1
                    if list_items:
                        try:
                            self.elements.append(ListFlowable(list_items, bulletType='1'))
                        except:
                            # Fallback
                            for idx, item in enumerate(list_items, 1):
                                self.elements.append(item.value)
                        self.elements.append(Spacer(1, 6))
                    continue
                
                # Regular paragraph
                else:
                    text = self.convert_inline(line.strip())
                    para = self.safe_paragraph(text, self.styles['Body'])
                    if para:
                        self.elements.append(para)
                
                i += 1
                
            except Exception as e:
                # Log error but continue processing
                i += 1
                continue
        
        return self.elements


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CALLBACK FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_page_callback(template: Optional[PDFTemplate] = None):
    """Create a page callback function with template-specific styling."""
    
    def add_page_elements(canvas, doc):
        """Add page number, header, footer based on template."""
        canvas.saveState()
        
        page_num = canvas.getPageNumber()
        
        # Get template settings
        if template:
            primary_color = HexColor(template.primary_color)
            accent_color = HexColor(template.accent_color)
            header_text = template.header_text
            footer_text = template.footer_text
            confidential = template.confidential_notice
            show_header = template.show_header
            show_footer = template.show_footer
            show_page_num = template.show_page_numbers
        else:
            primary_color = HexColor('#1a365d')
            accent_color = HexColor('#3182ce')
            header_text = ""
            footer_text = ""
            confidential = ""
            show_header = True
            show_footer = True
            show_page_num = True
        
        width, height = doc.pagesize
        
        # Header
        if show_header:
            # Header line
            canvas.setStrokeColor(accent_color)
            canvas.setLineWidth(1)
            canvas.line(2*cm, height - 2*cm, width - 2*cm, height - 2*cm)
            
            # Header text (left)
            if header_text:
                canvas.setFont('Helvetica-Bold', 8)
                canvas.setFillColor(primary_color)
                canvas.drawString(2*cm, height - 1.5*cm, header_text)
            
            # Confidential notice (right)
            if confidential:
                canvas.setFont('Helvetica-Bold', 8)
                canvas.setFillColor(HexColor('#c53030'))
                canvas.drawRightString(width - 2*cm, height - 1.5*cm, confidential)
        
        # Footer
        if show_footer:
            # Footer line
            canvas.setStrokeColor(HexColor('#e2e8f0'))
            canvas.setLineWidth(0.5)
            canvas.line(2*cm, 2*cm, width - 2*cm, 2*cm)
            
            # Footer text (center)
            if footer_text:
                text = footer_text.replace("{page}", str(page_num))
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(gray)
                canvas.drawCentredString(width / 2, 1.2*cm, text)
            
            # Page number (right)
            if show_page_num:
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(gray)
                canvas.drawRightString(width - 2*cm, 1.2*cm, f"Page {page_num}")
        
        canvas.restoreState()
    
    return add_page_elements


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdf(
    content: str,
    output_path: str,
    title: Optional[str] = None,
    author: str = "KOREV Evidence",
    template_name: Optional[str] = None,
    user_request: Optional[str] = None,
    pagesize = A4
) -> str:
    """
    Generate a professional PDF from Markdown content with template support.
    
    Args:
        content: Markdown content to convert
        output_path: Path for the output PDF
        title: Optional document title (added as first element)
        author: PDF metadata author
        template_name: Explicit template name (consulting_premium, legal_formal, scientific_academic, patent_ip, etc.)
        user_request: User's original request (for automatic template detection)
        pagesize: Page size (A4 or letter)
    
    Returns:
        Path to the generated PDF
    
    Templates disponibles:
        - consulting_premium: Rapport stratégique premium KOREV Evidence
        - legal_formal: Document juridique (tribunal/greffe)
        - scientific_academic: Publication scientifique
        - patent: Brevet INPI/EPO
        - financial: Rapport financier/audit
        - executive: Note de synthèse executive
        - medical: Rapport médical/clinique
        - technical: Documentation technique
        - default: Document professionnel standard
    """
    # Detect or get template
    if template_name:
        template = get_template(template_name)
    elif user_request:
        detected_name = detect_template(user_request)
        template = get_template(detected_name)
    else:
        template = get_template("default")
    
    # Create document with template margins
    doc = SimpleDocTemplate(
        output_path,
        pagesize=pagesize,
        leftMargin=template.left_margin * cm,
        rightMargin=template.right_margin * cm,
        topMargin=template.top_margin * cm,
        bottomMargin=template.bottom_margin * cm,
        title=title or "Document",
        author=author
    )
    
    # Create styles with template
    styles, _ = create_styles(template)
    
    # Parse markdown with template
    parser = MarkdownToPDF(styles, template)
    elements = []
    
    # Add title if provided
    if title:
        try:
            elements.append(Paragraph(parser.sanitize_text(title), styles['DocTitle']))
        except:
            elements.append(Paragraph(title, styles['DocTitle']))
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=HexColor(template.accent_color),
            spaceBefore=10,
            spaceAfter=20
        ))
    
    # Add template info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    template_label = f"Template: {template.display_name}" if template.name != "default" else ""
    meta_text = f"<font color='#718096' size='9'>Generated: {timestamp}"
    if template_label:
        meta_text += f" | {template_label}"
    meta_text += "</font>"
    elements.append(Paragraph(meta_text, styles['Body']))
    elements.append(Spacer(1, 20))
    
    # Add content
    elements.extend(parser.parse(content))
    
    # Create page callback with template
    page_callback = create_page_callback(template)
    
    # Build PDF
    doc.build(elements, onFirstPage=page_callback, onLaterPages=page_callback)
    
    return output_path


def markdown_to_pdf_bytes(
    content: str,
    title: Optional[str] = None,
    author: str = "KOREV Evidence",
    template_name: Optional[str] = None,
    user_request: Optional[str] = None
) -> bytes:
    """
    Generate PDF as bytes (for streaming or in-memory use) with template support.
    
    Args:
        content: Markdown content
        title: Optional document title
        author: PDF metadata author
        template_name: Explicit template name
        user_request: User's request for auto-detection
    
    Returns:
        PDF as bytes
    """
    buffer = BytesIO()
    
    # Detect or get template
    if template_name:
        template = get_template(template_name)
    elif user_request:
        detected_name = detect_template(user_request)
        template = get_template(detected_name)
    else:
        template = get_template("default")
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=template.left_margin * cm,
        rightMargin=template.right_margin * cm,
        topMargin=template.top_margin * cm,
        bottomMargin=template.bottom_margin * cm,
        title=title or "Document",
        author=author
    )
    
    styles, _ = create_styles(template)
    parser = MarkdownToPDF(styles, template)
    elements = []
    
    if title:
        try:
            elements.append(Paragraph(parser.sanitize_text(title), styles['DocTitle']))
        except:
            elements.append(Paragraph(title, styles['DocTitle']))
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=HexColor(template.accent_color),
            spaceBefore=10,
            spaceAfter=20
        ))
    
    elements.extend(parser.parse(content))
    
    page_callback = create_page_callback(template)
    doc.build(elements, onFirstPage=page_callback, onLaterPages=page_callback)
    
    return buffer.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def list_available_templates() -> List[dict]:
    """List all available templates with their descriptions."""
    return [
        {
            "name": name,
            "display_name": t.display_name,
            "description": t.description,
            "suggested_sections": t.suggested_sections
        }
        for name, t in TEMPLATES.items()
    ]


def get_template_sections(template_name: str) -> List[str]:
    """Get suggested sections for a template."""
    template = get_template(template_name)
    return template.suggested_sections
