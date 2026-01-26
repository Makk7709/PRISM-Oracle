"""
Evidence Document Renderer — AST to PDF.

Prend un Document (AST) et produit un PDF professionnel.
"""

from io import BytesIO
from typing import Optional, List
from datetime import datetime
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, gray
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    ListFlowable, ListItem, Preformatted, HRFlowable, KeepTogether
)

from .ast import (
    Document, DocumentElement, ConfidentialityLevel,
    Paragraph as AstParagraph, Heading, BulletList, NumberedList,
    Table as AstTable, CodeBlock, BlockQuote, HorizontalRule,
    PageBreak as AstPageBreak, Figure, KeyValue, Callout, TextSpan
)
from .templates import Template, get_template
from .layout import (
    generate_styles, create_page_callback, build_table,
    CoverPage, PageInfo, _sanitize_text, format_inline
)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def render_to_pdf(doc: Document) -> bytes:
    """
    Rend un Document en PDF (bytes).
    
    Args:
        doc: Document AST à rendre
        
    Returns:
        PDF sous forme de bytes
    """
    buffer = BytesIO()
    _render_to_stream(doc, buffer)
    return buffer.getvalue()


def render_to_file(doc: Document, path: str) -> str:
    """
    Rend un Document en fichier PDF.
    
    Args:
        doc: Document AST à rendre
        path: Chemin du fichier de sortie
        
    Returns:
        Chemin du fichier créé
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    
    with open(path, 'wb') as f:
        _render_to_stream(doc, f)
    
    return path


def _render_to_stream(doc: Document, stream) -> None:
    """Render document to a stream (file or BytesIO)."""
    
    # Get template
    template = get_template(doc.template)
    
    # Generate styles
    styles = generate_styles(template)
    
    # Page info for tracking
    page_info = PageInfo()
    
    # Create document
    pdf_doc = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=template.left_margin * cm,
        rightMargin=template.right_margin * cm,
        topMargin=template.top_margin * cm,
        bottomMargin=template.bottom_margin * cm,
        title=doc.title,
        author=doc.metadata.author
    )
    
    # Build elements
    elements = []
    
    # Cover page
    if doc.show_cover_page:
        cover = CoverPage(
            title=doc.title,
            template=template,
            metadata={
                "author": doc.metadata.author,
                "version": doc.metadata.version,
                "confidentiality": doc.metadata.confidentiality.value,
                "date": doc.metadata.created_at.strftime("%Y-%m-%d") if doc.metadata.created_at else None
            },
            style=template.cover_page_style
        )
        elements.append(cover)
        elements.append(PageBreak())
    
    # Table of contents placeholder
    if doc.show_toc:
        elements.append(Paragraph("Table des Matières", styles['H1']))
        elements.append(Spacer(1, 20))
        # TODO: Implement TOC in 2-pass
        elements.append(Paragraph(
            "<i>Table des matières générée automatiquement</i>",
            styles['Body']
        ))
        elements.append(PageBreak())
    
    # Main content
    for element in doc.elements:
        rendered = _render_element(element, template, styles)
        if rendered:
            if isinstance(rendered, list):
                elements.extend(rendered)
            else:
                elements.append(rendered)
    
    # Sources section
    if doc.show_sources and doc.metadata.sources:
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(
            width="100%", thickness=1,
            color=HexColor('#e2e8f0'),
            spaceBefore=10, spaceAfter=10
        ))
        elements.append(Paragraph("Sources & Références", styles['H2']))
        
        for i, source in enumerate(doc.metadata.sources, 1):
            source_text = f"[{i}] <b>{_sanitize_text(source.title)}</b>"
            if source.author:
                source_text += f" — {_sanitize_text(source.author)}"
            if source.date:
                source_text += f" ({source.date})"
            if source.url:
                source_text += f"<br/><font color='#3182ce'>{_sanitize_text(source.url)}</font>"
            if source.confidence:
                source_text += f" [Confiance: {int(source.confidence * 100)}%]"
            
            elements.append(Paragraph(source_text, styles['Source']))
    
    # Assumptions section
    if doc.show_assumptions and doc.metadata.assumptions:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Hypothèses & Prémisses", styles['H2']))
        
        for assumption in doc.metadata.assumptions:
            impact_color = {
                "low": "#38a169",
                "medium": "#d69e2e",
                "high": "#e53e3e"
            }.get(assumption.impact, "#718096")
            
            elements.append(Paragraph(
                f"<b>[{assumption.id}]</b> {_sanitize_text(assumption.text)} "
                f"<font color='{impact_color}'>[Impact: {assumption.impact}]</font>",
                styles['Assumption']
            ))
    
    # Audit trail
    if doc.show_audit_trail:
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(
            width="100%", thickness=1,
            color=HexColor('#e2e8f0'),
            spaceBefore=10, spaceAfter=10
        ))
        elements.append(Paragraph("Audit Trail", styles['H3']))
        
        audit_items = []
        if doc.metadata.generation_id:
            audit_items.append(f"Generation ID: {doc.metadata.generation_id}")
        if doc.metadata.model_used:
            audit_items.append(f"Model: {doc.metadata.model_used}")
        if doc.metadata.created_at:
            audit_items.append(f"Generated: {doc.metadata.created_at.isoformat()}")
        if doc.metadata.confidence_score:
            audit_items.append(f"Confidence Score: {int(doc.metadata.confidence_score * 100)}%")
        
        for item in audit_items:
            elements.append(Paragraph(
                f"<font color='#718096' size='8'>{item}</font>",
                styles['Body']
            ))
    
    # Footer with generation info
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"<font color='#a0aec0' size='8'>Document généré par Korev Evidence — "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}</font>",
        styles['Body']
    ))
    
    # Create page callback
    page_callback = create_page_callback(
        template=template,
        confidentiality=doc.metadata.confidentiality,
        watermark=doc.watermark,
        page_info=page_info
    )
    
    # Build PDF
    pdf_doc.build(
        elements,
        onFirstPage=page_callback,
        onLaterPages=page_callback
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ELEMENT RENDERERS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_element(element: DocumentElement, template: Template, styles: dict):
    """Render a single AST element to ReportLab flowable(s)."""
    
    if isinstance(element, AstParagraph):
        return _render_paragraph(element, styles)
    
    elif isinstance(element, Heading):
        return _render_heading(element, styles)
    
    elif isinstance(element, BulletList):
        return _render_bullet_list(element, styles, template)
    
    elif isinstance(element, NumberedList):
        return _render_numbered_list(element, styles, template)
    
    elif isinstance(element, AstTable):
        return _render_table(element, template)
    
    elif isinstance(element, CodeBlock):
        return _render_code_block(element, styles)
    
    elif isinstance(element, BlockQuote):
        return _render_blockquote(element, styles)
    
    elif isinstance(element, HorizontalRule):
        return HRFlowable(
            width="100%", thickness=1,
            color=HexColor('#e2e8f0'),
            spaceBefore=10, spaceAfter=10
        )
    
    elif isinstance(element, AstPageBreak):
        return PageBreak()
    
    elif isinstance(element, KeyValue):
        return Paragraph(
            f"<b>{_sanitize_text(element.key)}:</b> {_sanitize_text(element.value)}",
            styles['Body']
        )
    
    elif isinstance(element, Callout):
        return _render_callout(element, styles)
    
    elif isinstance(element, Figure):
        # TODO: Implement figure rendering
        return Paragraph(
            f"<i>[Figure: {_sanitize_text(element.caption or element.path)}]</i>",
            styles['Body']
        )
    
    return None


def _render_paragraph(para: AstParagraph, styles: dict):
    """Render a paragraph."""
    if isinstance(para.content, str):
        text = format_inline(para.content)
    else:
        # List of TextSpan
        parts = []
        for span in para.content:
            part = _sanitize_text(span.text)
            if span.bold:
                part = f"<b>{part}</b>"
            if span.italic:
                part = f"<i>{part}</i>"
            if span.code:
                part = f'<font name="Courier" color="#c53030">{part}</font>'
            if span.link:
                part = f'<font color="#3182ce"><u>{part}</u></font>'
            parts.append(part)
        text = ''.join(parts)
    
    try:
        return Paragraph(text, styles['Body'])
    except:
        # Fallback
        return Paragraph(_sanitize_text(str(para.content)), styles['Body'])


def _render_heading(heading: Heading, styles: dict):
    """Render a heading."""
    style_name = f'H{min(heading.level, 4)}'
    text = format_inline(heading.text)
    
    try:
        return Paragraph(text, styles[style_name])
    except:
        return Paragraph(_sanitize_text(heading.text), styles[style_name])


def _render_bullet_list(lst: BulletList, styles: dict, template: Template):
    """Render a bullet list."""
    items = []
    accent = HexColor(template.accent_color)
    
    for item in lst.items:
        text = format_inline(item)
        try:
            para = Paragraph(text, styles['ListItem'])
        except:
            para = Paragraph(_sanitize_text(item), styles['ListItem'])
        items.append(ListItem(para, bulletColor=accent))
    
    if items:
        try:
            return ListFlowable(items, bulletType='bullet', start='•')
        except:
            # Fallback: return as paragraphs
            return [Paragraph(f"• {_sanitize_text(item)}", styles['Body']) 
                    for item in lst.items]
    return None


def _render_numbered_list(lst: NumberedList, styles: dict, template: Template):
    """Render a numbered list."""
    items = []
    
    for item in lst.items:
        text = format_inline(item)
        try:
            para = Paragraph(text, styles['ListItem'])
        except:
            para = Paragraph(_sanitize_text(item), styles['ListItem'])
        items.append(ListItem(para))
    
    if items:
        try:
            return ListFlowable(items, bulletType='1', start=lst.start)
        except:
            return [Paragraph(f"{i}. {_sanitize_text(item)}", styles['Body']) 
                    for i, item in enumerate(lst.items, lst.start)]
    return None


def _render_table(table: AstTable, template: Template) -> List:
    """Render a table."""
    return build_table(
        headers=table.headers,
        rows=table.rows,
        template=template,
        caption=table.caption
    )


def _render_code_block(code: CodeBlock, styles: dict):
    """Render a code block."""
    try:
        return Preformatted(_sanitize_text(code.code), styles['Code'])
    except:
        return Paragraph(
            f"<font name='Courier'>{_sanitize_text(code.code)}</font>",
            styles['Body']
        )


def _render_blockquote(quote: BlockQuote, styles: dict):
    """Render a blockquote."""
    text = format_inline(quote.text)
    if quote.source:
        text += f"<br/><font color='#718096'>— {_sanitize_text(quote.source)}</font>"
    
    try:
        return Paragraph(text, styles['BlockQuote'])
    except:
        return Paragraph(_sanitize_text(quote.text), styles['BlockQuote'])


def _render_callout(callout: Callout, styles: dict):
    """Render a callout box."""
    style_name = f'Callout_{callout.type}'
    if style_name not in styles:
        style_name = 'Callout_info'
    
    text = ""
    if callout.title:
        text = f"<b>{_sanitize_text(callout.title)}</b><br/>"
    text += format_inline(callout.text)
    
    try:
        return Paragraph(text, styles[style_name])
    except:
        return Paragraph(_sanitize_text(callout.text), styles['Body'])
