"""
Evidence Document AST — Structured document representation.

Au lieu de parser du Markdown brut, Evidence produit un AST structuré
qui est ensuite rendu en PDF de manière déterministe et testable.

Usage:
    doc = Document(
        title="Analyse Stratégique",
        template="consulting_premium",
        metadata=DocumentMetadata(
            author="Evidence",
            confidentiality="CONFIDENTIEL",
            version="1.0"
        )
    )
    doc.add(Heading("Executive Summary", level=1))
    doc.add(Paragraph("Recommandation: Procéder à l'acquisition."))
    doc.add(BulletList(["Point 1", "Point 2"]))
    doc.add(Table(headers=["Métrique", "Valeur"], rows=[["CA", "€10M"]]))
    
    pdf_bytes = render_document(doc)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Any, Dict
from enum import Enum
from datetime import datetime
import hashlib
import json


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ConfidentialityLevel(str, Enum):
    """Niveaux de confidentialité."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    STRICTLY_CONFIDENTIAL = "strictly_confidential"
    SECRET = "secret"


class HeadingLevel(int, Enum):
    """Niveaux de titre."""
    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4


# ═══════════════════════════════════════════════════════════════════════════════
# AST NODES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TextSpan:
    """Texte avec formatage inline."""
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "type": "text_span",
            "text": self.text,
            "bold": self.bold,
            "italic": self.italic,
            "code": self.code,
            "link": self.link
        }


@dataclass
class Paragraph:
    """Paragraphe de texte."""
    content: Union[str, List[TextSpan]]
    
    def to_dict(self) -> dict:
        if isinstance(self.content, str):
            return {"type": "paragraph", "content": self.content}
        return {
            "type": "paragraph",
            "content": [span.to_dict() for span in self.content]
        }


@dataclass
class Heading:
    """Titre (H1-H4)."""
    text: str
    level: int = 1  # 1-4
    
    def to_dict(self) -> dict:
        return {"type": "heading", "text": self.text, "level": self.level}


@dataclass
class BulletList:
    """Liste à puces."""
    items: List[str]
    
    def to_dict(self) -> dict:
        return {"type": "bullet_list", "items": self.items}


@dataclass
class NumberedList:
    """Liste numérotée."""
    items: List[str]
    start: int = 1
    
    def to_dict(self) -> dict:
        return {"type": "numbered_list", "items": self.items, "start": self.start}


@dataclass
class Table:
    """Tableau."""
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "type": "table",
            "headers": self.headers,
            "rows": self.rows,
            "caption": self.caption
        }


@dataclass
class CodeBlock:
    """Bloc de code."""
    code: str
    language: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "type": "code_block",
            "code": self.code,
            "language": self.language
        }


@dataclass
class BlockQuote:
    """Citation/blockquote."""
    text: str
    source: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "type": "block_quote",
            "text": self.text,
            "source": self.source
        }


@dataclass
class HorizontalRule:
    """Ligne horizontale."""
    
    def to_dict(self) -> dict:
        return {"type": "horizontal_rule"}


@dataclass
class PageBreak:
    """Saut de page."""
    
    def to_dict(self) -> dict:
        return {"type": "page_break"}


@dataclass
class Figure:
    """Figure/image avec légende."""
    path: str
    caption: Optional[str] = None
    width: Optional[float] = None  # Pourcentage (0-1)
    
    def to_dict(self) -> dict:
        return {
            "type": "figure",
            "path": self.path,
            "caption": self.caption,
            "width": self.width
        }


@dataclass
class KeyValue:
    """Paire clé-valeur pour métadonnées inline."""
    key: str
    value: str
    
    def to_dict(self) -> dict:
        return {"type": "key_value", "key": self.key, "value": self.value}


@dataclass
class Callout:
    """Encadré d'attention (info, warning, danger)."""
    text: str
    type: str = "info"  # info, warning, danger, success
    title: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "type": "callout",
            "text": self.text,
            "callout_type": self.type,
            "title": self.title
        }


# Type union pour tous les éléments
DocumentElement = Union[
    Paragraph, Heading, BulletList, NumberedList, Table,
    CodeBlock, BlockQuote, HorizontalRule, PageBreak,
    Figure, KeyValue, Callout
]


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT METADATA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DocumentSource:
    """Source citée dans le document."""
    id: str
    title: str
    url: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    confidence: Optional[float] = None  # 0-1
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "date": self.date,
            "confidence": self.confidence
        }


@dataclass
class Assumption:
    """Hypothèse ou prémisse du document."""
    id: str
    text: str
    impact: str = "medium"  # low, medium, high
    
    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "impact": self.impact}


@dataclass
class DocumentMetadata:
    """Métadonnées du document."""
    author: str = "KOREV Evidence"
    created_at: Optional[datetime] = None
    version: str = "1.0"
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL
    language: str = "fr"
    
    # Evidence-specific
    sources: List[DocumentSource] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)
    confidence_score: Optional[float] = None  # 0-1 global confidence
    
    # Audit trail (sans PII)
    model_used: Optional[str] = None
    generation_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "version": self.version,
            "confidentiality": self.confidentiality.value,
            "language": self.language,
            "sources": [s.to_dict() for s in self.sources],
            "assumptions": [a.to_dict() for a in self.assumptions],
            "confidence_score": self.confidence_score,
            "model_used": self.model_used,
            "generation_id": self.generation_id
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Document:
    """
    Document structuré pour Evidence.
    
    Représentation AST du document qui sera rendu en PDF.
    """
    title: str
    template: str = "standard"
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    elements: List[DocumentElement] = field(default_factory=list)
    
    # Options d'affichage
    show_cover_page: bool = True
    show_toc: bool = False
    show_sources: bool = True
    show_assumptions: bool = True
    show_audit_trail: bool = False
    watermark: Optional[str] = None
    
    def add(self, element: DocumentElement) -> "Document":
        """Ajoute un élément au document."""
        self.elements.append(element)
        return self
    
    def add_source(self, source: DocumentSource) -> "Document":
        """Ajoute une source."""
        self.metadata.sources.append(source)
        return self
    
    def add_assumption(self, assumption: Assumption) -> "Document":
        """Ajoute une hypothèse."""
        self.metadata.assumptions.append(assumption)
        return self
    
    def to_dict(self) -> dict:
        """Sérialise en dictionnaire (pour JSON)."""
        return {
            "title": self.title,
            "template": self.template,
            "metadata": self.metadata.to_dict(),
            "elements": [e.to_dict() for e in self.elements],
            "options": {
                "show_cover_page": self.show_cover_page,
                "show_toc": self.show_toc,
                "show_sources": self.show_sources,
                "show_assumptions": self.show_assumptions,
                "show_audit_trail": self.show_audit_trail,
                "watermark": self.watermark
            }
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Sérialise en JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def compute_hash(self) -> str:
        """Calcule un hash du contenu (pour snapshot tests)."""
        # Exclure les timestamps pour la reproductibilité
        data = self.to_dict()
        data["metadata"]["created_at"] = None
        data["metadata"]["generation_id"] = None
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """Désérialise depuis un dictionnaire."""
        # Parse metadata
        meta_data = data.get("metadata", {})
        sources = [
            DocumentSource(**s) for s in meta_data.get("sources", [])
        ]
        assumptions = [
            Assumption(**a) for a in meta_data.get("assumptions", [])
        ]
        
        confidentiality = meta_data.get("confidentiality", "internal")
        if isinstance(confidentiality, str):
            confidentiality = ConfidentialityLevel(confidentiality)
        
        metadata = DocumentMetadata(
            author=meta_data.get("author", "KOREV Evidence"),
            version=meta_data.get("version", "1.0"),
            confidentiality=confidentiality,
            language=meta_data.get("language", "fr"),
            sources=sources,
            assumptions=assumptions,
            confidence_score=meta_data.get("confidence_score"),
            model_used=meta_data.get("model_used"),
            generation_id=meta_data.get("generation_id")
        )
        
        # Parse elements
        elements = []
        for elem in data.get("elements", []):
            element = _parse_element(elem)
            if element:
                elements.append(element)
        
        # Options
        options = data.get("options", {})
        
        return cls(
            title=data.get("title", "Document"),
            template=data.get("template", "standard"),
            metadata=metadata,
            elements=elements,
            show_cover_page=options.get("show_cover_page", True),
            show_toc=options.get("show_toc", False),
            show_sources=options.get("show_sources", True),
            show_assumptions=options.get("show_assumptions", True),
            show_audit_trail=options.get("show_audit_trail", False),
            watermark=options.get("watermark")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Document":
        """Désérialise depuis JSON."""
        return cls.from_dict(json.loads(json_str))


def _parse_element(data: dict) -> Optional[DocumentElement]:
    """Parse un élément depuis son dictionnaire."""
    elem_type = data.get("type")
    
    if elem_type == "paragraph":
        content = data.get("content", "")
        if isinstance(content, list):
            spans = [TextSpan(**s) for s in content if s.get("type") == "text_span"]
            return Paragraph(content=spans)
        return Paragraph(content=content)
    
    elif elem_type == "heading":
        return Heading(text=data.get("text", ""), level=data.get("level", 1))
    
    elif elem_type == "bullet_list":
        return BulletList(items=data.get("items", []))
    
    elif elem_type == "numbered_list":
        return NumberedList(items=data.get("items", []), start=data.get("start", 1))
    
    elif elem_type == "table":
        return Table(
            headers=data.get("headers", []),
            rows=data.get("rows", []),
            caption=data.get("caption")
        )
    
    elif elem_type == "code_block":
        return CodeBlock(code=data.get("code", ""), language=data.get("language"))
    
    elif elem_type == "block_quote":
        return BlockQuote(text=data.get("text", ""), source=data.get("source"))
    
    elif elem_type == "horizontal_rule":
        return HorizontalRule()
    
    elif elem_type == "page_break":
        return PageBreak()
    
    elif elem_type == "figure":
        return Figure(
            path=data.get("path", ""),
            caption=data.get("caption"),
            width=data.get("width")
        )
    
    elif elem_type == "key_value":
        return KeyValue(key=data.get("key", ""), value=data.get("value", ""))
    
    elif elem_type == "callout":
        return Callout(
            text=data.get("text", ""),
            type=data.get("callout_type", "info"),
            title=data.get("title")
        )
    
    return None
