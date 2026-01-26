"""
Markdown to Document AST Parser.

Convertit du Markdown en Document AST pour compatibilité avec l'ancien système.
Permet une transition douce vers l'AST structuré.

Usage:
    from python.helpers.evidence_document import parse_markdown
    
    doc = parse_markdown(
        markdown_content,
        title="Mon Rapport",
        template="consulting_premium"
    )
    pdf_bytes = render_to_pdf(doc)
"""

import re
from typing import List, Optional, Tuple

from .ast import (
    Document, DocumentMetadata, ConfidentialityLevel,
    Paragraph, Heading, BulletList, NumberedList, Table,
    CodeBlock, BlockQuote, HorizontalRule, PageBreak
)
from .templates import detect_template


def parse_markdown(
    content: str,
    title: Optional[str] = None,
    template: Optional[str] = None,
    author: str = "Korev Evidence",
    confidentiality: str = "internal"
) -> Document:
    """
    Parse Markdown content into a Document AST.
    
    Args:
        content: Markdown text
        title: Document title (auto-detected if not provided)
        template: Template name (auto-detected from content if not provided)
        author: Author name
        confidentiality: Confidentiality level
        
    Returns:
        Document AST ready for rendering
    """
    # Auto-detect template from content
    if not template:
        template = detect_template(content)
    
    # Parse confidentiality
    try:
        conf_level = ConfidentialityLevel(confidentiality)
    except ValueError:
        conf_level = ConfidentialityLevel.INTERNAL
    
    # Create metadata
    metadata = DocumentMetadata(
        author=author,
        confidentiality=conf_level
    )
    
    # Parse content
    elements = _parse_markdown_content(content)
    
    # Auto-detect title from first H1 if not provided
    if not title:
        for elem in elements:
            if isinstance(elem, Heading) and elem.level == 1:
                title = elem.text
                break
        if not title:
            title = "Document"
    
    # Create document
    doc = Document(
        title=title,
        template=template,
        metadata=metadata,
        elements=elements
    )
    
    return doc


def _parse_markdown_content(markdown: str) -> List:
    """Parse markdown content into AST elements."""
    elements = []
    
    if not markdown:
        return elements
    
    # Normalize line endings
    markdown = markdown.replace('\r\n', '\n').replace('\r', '\n')
    lines = markdown.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip empty lines
        if not line.strip():
            i += 1
            continue
        
        # Code block
        if line.strip().startswith('```'):
            code_lines, i = _parse_code_block(lines, i)
            if code_lines is not None:
                lang = line.strip()[3:].strip() or None
                elements.append(CodeBlock(code='\n'.join(code_lines), language=lang))
            continue
        
        # Table
        if line.strip().startswith('|') and i + 1 < len(lines):
            table, i = _parse_table(lines, i)
            if table:
                elements.append(table)
            continue
        
        # Headers
        if line.startswith('#'):
            heading, level = _parse_heading(line)
            if heading:
                elements.append(Heading(text=heading, level=level))
            i += 1
            continue
        
        # Blockquote
        if line.strip().startswith('>'):
            quote = line.strip()[1:].strip()
            elements.append(BlockQuote(text=quote))
            i += 1
            continue
        
        # Horizontal rule
        if line.strip() in ['---', '***', '___']:
            elements.append(HorizontalRule())
            i += 1
            continue
        
        # Bullet list
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            items, i = _parse_bullet_list(lines, i)
            if items:
                elements.append(BulletList(items=items))
            continue
        
        # Numbered list
        if re.match(r'^\d+\.\s', line.strip()):
            items, i = _parse_numbered_list(lines, i)
            if items:
                elements.append(NumberedList(items=items))
            continue
        
        # Regular paragraph
        text = line.strip()
        if text:
            elements.append(Paragraph(content=text))
        
        i += 1
    
    return elements


def _parse_heading(line: str) -> Tuple[Optional[str], int]:
    """Parse a heading line."""
    if line.startswith('######'):
        return line[6:].strip(), 6
    elif line.startswith('#####'):
        return line[5:].strip(), 5
    elif line.startswith('####'):
        return line[4:].strip(), 4
    elif line.startswith('###'):
        return line[3:].strip(), 3
    elif line.startswith('##'):
        return line[2:].strip(), 2
    elif line.startswith('#'):
        return line[1:].strip(), 1
    return None, 0


def _parse_code_block(lines: List[str], start: int) -> Tuple[Optional[List[str]], int]:
    """Parse a code block."""
    code_lines = []
    i = start + 1
    
    while i < len(lines):
        if lines[i].strip().startswith('```'):
            return code_lines, i + 1
        code_lines.append(lines[i])
        i += 1
    
    # Unclosed code block - return what we have
    return code_lines, i


def _parse_table(lines: List[str], start: int) -> Tuple[Optional[Table], int]:
    """Parse a markdown table."""
    table_lines = []
    i = start
    
    while i < len(lines) and lines[i].strip().startswith('|'):
        table_lines.append(lines[i])
        i += 1
    
    if len(table_lines) < 2:
        return None, i
    
    # Parse header
    header_line = table_lines[0].strip()
    headers = [cell.strip() for cell in header_line.split('|')[1:-1]]
    
    if not headers:
        return None, i
    
    # Skip separator line (index 1)
    # Parse rows
    rows = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().split('|')[1:-1]]
        if cells:
            # Pad to match headers
            while len(cells) < len(headers):
                cells.append('')
            rows.append(cells[:len(headers)])
    
    return Table(headers=headers, rows=rows), i


def _parse_bullet_list(lines: List[str], start: int) -> Tuple[List[str], int]:
    """Parse a bullet list."""
    items = []
    i = start
    
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('- '):
            items.append(line[2:])
        elif line.startswith('* '):
            items.append(line[2:])
        else:
            break
        i += 1
    
    return items, i


def _parse_numbered_list(lines: List[str], start: int) -> Tuple[List[str], int]:
    """Parse a numbered list."""
    items = []
    i = start
    
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r'^\d+\.\s(.+)$', line)
        if match:
            items.append(match.group(1))
        else:
            break
        i += 1
    
    return items, i
