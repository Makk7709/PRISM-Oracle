"""
Legal Sources — Legal Document Chunker

Découpage intelligent des documents juridiques avec préservation
de la structure (articles, alinéas, sections).
"""

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Generator, List, Optional, Tuple

from ..models import LegalChunk, LegalDoc, Provenance


class ChunkingStrategy(str, Enum):
    """Stratégies de découpage."""
    FIXED_SIZE = "fixed_size"      # Taille fixe avec overlap
    ARTICLE = "article"            # Par article complet
    PARAGRAPH = "paragraph"        # Par paragraphe/alinéa
    SEMANTIC = "semantic"          # Sémantique (nécessite modèle)


@dataclass
class ChunkerConfig:
    """Configuration du chunker."""
    strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH
    chunk_size: int = 1000  # Caractères max
    chunk_overlap: int = 100
    min_chunk_size: int = 100
    preserve_sentences: bool = True
    include_context: bool = True  # Inclure titre/citation dans chaque chunk


class LegalChunker:
    """
    Chunker spécialisé pour documents juridiques.
    
    Respecte la structure des documents:
    - Codes: par article puis par alinéa
    - Décisions: par paragraphe avec contexte
    - Lois: par article
    
    Garanties:
    - Déterminisme: même doc => mêmes chunks
    - Provenance: chaque chunk conserve sa source
    - Intégrité: hash stable pour chaque chunk
    """
    
    def __init__(self, config: Optional[ChunkerConfig] = None):
        self.config = config or ChunkerConfig()
    
    def chunk_document(self, doc: LegalDoc) -> Generator[LegalChunk, None, None]:
        """
        Découpe un document en chunks indexables.
        
        Args:
            doc: Document juridique à découper
        
        Yields:
            LegalChunk pour chaque segment
        """
        if not doc.text:
            return
        
        if self.config.strategy == ChunkingStrategy.FIXED_SIZE:
            yield from self._chunk_fixed_size(doc)
        elif self.config.strategy == ChunkingStrategy.ARTICLE:
            yield from self._chunk_by_article(doc)
        elif self.config.strategy == ChunkingStrategy.PARAGRAPH:
            yield from self._chunk_by_paragraph(doc)
        else:
            # Default to paragraph
            yield from self._chunk_by_paragraph(doc)
    
    def _chunk_fixed_size(self, doc: LegalDoc) -> Generator[LegalChunk, None, None]:
        """Découpage à taille fixe avec overlap."""
        text = doc.text
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        if len(text) <= chunk_size:
            yield self._create_chunk(doc, text, 0, "complete")
            return
        
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Ajuster pour ne pas couper au milieu d'un mot
            if end < len(text) and self.config.preserve_sentences:
                # Chercher la fin de phrase la plus proche
                sentence_end = self._find_sentence_boundary(text, end)
                if sentence_end > start + self.config.min_chunk_size:
                    end = sentence_end
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.config.min_chunk_size:
                pinpoint = f"chars {start}-{end}"
                yield self._create_chunk(doc, chunk_text, chunk_index, pinpoint)
                chunk_index += 1
            
            start = end - overlap
            if start >= len(text):
                break
    
    def _chunk_by_article(self, doc: LegalDoc) -> Generator[LegalChunk, None, None]:
        """Découpage par article (pour codes)."""
        # Pour un article de code, on garde l'article entier s'il est petit
        # sinon on découpe par alinéa
        text = doc.text
        
        if len(text) <= self.config.chunk_size:
            pinpoint = f"Art. {doc.article_number}" if doc.article_number else "article complet"
            yield self._create_chunk(doc, text, 0, pinpoint)
            return
        
        # Découper par alinéa si trop long
        yield from self._chunk_by_paragraph(doc)
    
    def _chunk_by_paragraph(self, doc: LegalDoc) -> Generator[LegalChunk, None, None]:
        """
        Découpage par paragraphe/alinéa.
        
        Reconnaît les structures juridiques:
        - Alinéas numérotés (1°, 2°, a), b))
        - Paragraphes séparés par double saut de ligne
        - Attendus dans les décisions
        """
        text = doc.text
        paragraphs = self._split_into_paragraphs(text, doc)
        
        chunk_index = 0
        current_chunk = ""
        current_pinpoints = []
        
        for para_text, para_type in paragraphs:
            # Vérifier si on peut ajouter au chunk courant
            if len(current_chunk) + len(para_text) <= self.config.chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para_text
                current_pinpoints.append(para_type)
            else:
                # Émettre le chunk courant s'il est assez grand
                if len(current_chunk) >= self.config.min_chunk_size:
                    pinpoint = self._format_pinpoint(current_pinpoints, doc)
                    yield self._create_chunk(doc, current_chunk, chunk_index, pinpoint)
                    chunk_index += 1
                
                # Commencer un nouveau chunk
                current_chunk = para_text
                current_pinpoints = [para_type]
        
        # Émettre le dernier chunk
        if len(current_chunk) >= self.config.min_chunk_size:
            pinpoint = self._format_pinpoint(current_pinpoints, doc)
            yield self._create_chunk(doc, current_chunk, chunk_index, pinpoint)
    
    def _split_into_paragraphs(
        self,
        text: str,
        doc: LegalDoc,
    ) -> List[Tuple[str, str]]:
        """
        Sépare le texte en paragraphes avec leur type.
        
        Returns:
            Liste de (texte, type) où type est "al. 1", "1°", "attendu", etc.
        """
        paragraphs = []
        
        # Patterns pour identifier les structures
        alinea_pattern = r"^(\d+)[°\)]\s+"  # 1°, 2°, 1), 2)
        lettre_pattern = r"^([a-z])\)\s+"   # a), b)
        attendu_pattern = r"^(Attendu|Considérant|Vu)\s+"
        tiret_pattern = r"^[-–]\s+"
        
        # Séparer par double saut de ligne d'abord
        raw_paragraphs = re.split(r"\n\s*\n", text)
        
        for i, para in enumerate(raw_paragraphs):
            para = para.strip()
            if not para:
                continue
            
            # Identifier le type
            if re.match(alinea_pattern, para):
                match = re.match(alinea_pattern, para)
                para_type = f"{match.group(1)}°"
            elif re.match(lettre_pattern, para):
                match = re.match(lettre_pattern, para)
                para_type = f"{match.group(1)})"
            elif re.match(attendu_pattern, para, re.IGNORECASE):
                para_type = "attendu"
            elif re.match(tiret_pattern, para):
                para_type = "tiret"
            else:
                para_type = f"al. {i + 1}"
            
            paragraphs.append((para, para_type))
        
        # Si pas de paragraphes distincts, découper par phrases
        if len(paragraphs) <= 1 and len(text) > self.config.chunk_size:
            paragraphs = self._split_by_sentences(text)
        
        return paragraphs
    
    def _split_by_sentences(self, text: str) -> List[Tuple[str, str]]:
        """Découpe par phrases si pas de structure de paragraphes."""
        # Pattern pour fin de phrase
        sentence_pattern = r"(?<=[.!?])\s+(?=[A-ZÀ-Ö])"
        
        sentences = re.split(sentence_pattern, text)
        return [(s.strip(), f"phrase {i+1}") for i, s in enumerate(sentences) if s.strip()]
    
    def _find_sentence_boundary(self, text: str, position: int) -> int:
        """Trouve la fin de phrase la plus proche de position."""
        # Chercher en arrière d'abord
        for i in range(position, max(position - 200, 0), -1):
            if text[i] in ".!?" and (i + 1 >= len(text) or text[i + 1].isspace()):
                return i + 1
        
        # Puis en avant
        for i in range(position, min(position + 100, len(text))):
            if text[i] in ".!?" and (i + 1 >= len(text) or text[i + 1].isspace()):
                return i + 1
        
        return position
    
    def _format_pinpoint(self, pinpoints: List[str], doc: LegalDoc) -> str:
        """Formate le pinpoint pour un chunk."""
        if not pinpoints:
            return ""
        
        # Pour un article de code
        if doc.article_number:
            if len(pinpoints) == 1:
                return f"Art. {doc.article_number}, {pinpoints[0]}"
            return f"Art. {doc.article_number}, {pinpoints[0]}-{pinpoints[-1]}"
        
        # Pour une décision
        if len(pinpoints) == 1:
            return pinpoints[0]
        return f"{pinpoints[0]} à {pinpoints[-1]}"
    
    def _create_chunk(
        self,
        doc: LegalDoc,
        text: str,
        index: int,
        pinpoint: str,
    ) -> LegalChunk:
        """Crée un chunk avec provenance complète."""
        # Contexte optionnel
        if self.config.include_context:
            context = f"[{doc.citation}]\n\n"
            text = context + text
        
        # Provenance
        provenance = Provenance(
            source=doc.source,
            source_name=doc.provenance.source_name if doc.provenance else "",
            origin_id=doc.origin_id,
            origin_url=doc.provenance.origin_url if doc.provenance else None,
            retrieved_at=doc.provenance.retrieved_at if doc.provenance else None,
            license=doc.provenance.license if doc.provenance else "Licence Ouverte 2.0",
            content_hash=hashlib.sha256(text.encode()).hexdigest()[:12],
            pinpoint=pinpoint,
            chunk_index=index,
        )
        
        return LegalChunk(
            chunk_id="",  # Auto-calculé
            doc_id=doc.doc_id,
            chunk_index=index,
            text=text,
            source=doc.source,
            document_type=doc.document_type,
            citation=doc.citation,
            pinpoint=pinpoint,
            provenance=provenance,
        )


def chunk_documents(
    docs: List[LegalDoc],
    config: Optional[ChunkerConfig] = None,
) -> Generator[LegalChunk, None, None]:
    """
    Découpe une liste de documents en chunks.
    
    Args:
        docs: Documents à découper
        config: Configuration du chunker
    
    Yields:
        LegalChunk pour chaque segment
    """
    chunker = LegalChunker(config)
    
    for doc in docs:
        yield from chunker.chunk_document(doc)
