"""
Evidence Document System — Professional document generation.

Architecture:
- ast.py: Document AST (structured representation)
- templates.py: Template definitions (sans marques)
- layout.py: Layout engine (ReportLab rendering)
- renderer.py: Main renderer (AST -> PDF)

Usage:
    from python.helpers.evidence_document import Document, render_to_pdf
    
    doc = Document(title="Analyse", template="consulting_premium")
    doc.add(Heading("Summary", level=1))
    doc.add(Paragraph("..."))
    
    pdf_bytes = render_to_pdf(doc)
"""

from .ast import (
    Document,
    DocumentMetadata,
    DocumentSource,
    Assumption,
    ConfidentialityLevel,
    # Elements
    Paragraph,
    Heading,
    BulletList,
    NumberedList,
    Table,
    CodeBlock,
    BlockQuote,
    HorizontalRule,
    PageBreak,
    Figure,
    KeyValue,
    Callout,
    TextSpan,
)

from .templates import (
    Template,
    get_template,
    list_templates,
    detect_template,
    TEMPLATES,
)

from .renderer import render_to_pdf, render_to_file
from .markdown_parser import parse_markdown

__all__ = [
    # Document
    "Document",
    "DocumentMetadata",
    "DocumentSource",
    "Assumption",
    "ConfidentialityLevel",
    # Elements
    "Paragraph",
    "Heading",
    "BulletList",
    "NumberedList",
    "Table",
    "CodeBlock",
    "BlockQuote",
    "HorizontalRule",
    "PageBreak",
    "Figure",
    "KeyValue",
    "Callout",
    "TextSpan",
    # Templates
    "Template",
    "get_template",
    "list_templates",
    "detect_template",
    "TEMPLATES",
    # Rendering
    "render_to_pdf",
    "render_to_file",
    # Markdown compatibility
    "parse_markdown",
]
