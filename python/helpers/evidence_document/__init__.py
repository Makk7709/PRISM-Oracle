"""
Evidence Document System — Professional document generation.

Architecture:
- ast.py: Document AST (structured representation)
- templates.py: Template definitions (KOREV Evidence)
- layout.py: Layout engine (ReportLab rendering)
- renderer.py: Main renderer (AST -> PDF)
- fonts.py: TTF font registration (Unicode support)

Typography:
- DejaVu Sans: Primary sans-serif (full Unicode)
- DejaVu Serif: Serif for legal/academic
- DejaVu Mono: Monospace for code

Usage:
    from python.helpers.evidence_document import Document, render_to_pdf
    
    doc = Document(title="Analyse", template="consulting_premium")
    doc.add(Heading("Summary", level=1))
    doc.add(Paragraph("..."))
    
    pdf_bytes = render_to_pdf(doc)
"""

# Auto-register TTF fonts on import
try:
    from .fonts import register_fonts
    register_fonts()
except ImportError:
    pass  # Fonts will fall back to Helvetica

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
