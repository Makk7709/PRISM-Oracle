"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    REPORT ASSEMBLER — Chunked Generation                     ║
║                                                                              ║
║  Génère des rapports longs section par section.                              ║
║                                                                              ║
║  Stratégie:                                                                  ║
║  1. Outline → sections définies                                              ║
║  2. Chaque section générée avec contexte minimal (outline + citations)       ║
║  3. Écriture progressive (append)                                            ║
║  4. Pas de limite artificielle                                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("report_assembler")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION OUTLINE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SectionOutline:
    """Structure d'une section à générer."""
    title: str
    level: int = 2  # Header level (2 = ##, 3 = ###, etc.)
    description: str = ""
    key_points: List[str] = field(default_factory=list)
    citations_required: List[str] = field(default_factory=list)  # Source IDs
    subsections: List["SectionOutline"] = field(default_factory=list)
    
    # Contraintes
    min_words: int = 100
    max_words: int = 2000
    
    # État
    generated: bool = False


@dataclass
class ChunkContext:
    """Contexte pour la génération d'un chunk."""
    # Report info
    report_title: str
    report_query: str
    
    # Current section
    section_title: str
    section_description: str
    section_key_points: List[str]
    
    # Outline (pour contexte global)
    full_outline: List[str]
    current_section_idx: int
    
    # Citations disponibles
    available_citations: Dict[str, Dict[str, Any]]
    
    # Previous sections (résumé)
    previous_sections_summary: str
    
    # Constraints
    min_words: int
    max_words: int
    
    def to_prompt_context(self) -> str:
        """Génère le contexte à injecter dans le prompt."""
        outline_text = "\n".join(
            f"{'→ ' if i == self.current_section_idx else '  '}{i+1}. {s}"
            for i, s in enumerate(self.full_outline)
        )
        
        key_points_text = "\n".join(f"- {p}" for p in self.section_key_points)
        
        citations_text = ""
        if self.available_citations:
            citations_text = "\n".join(
                f"[{cid}] {c.get('title', 'N/A')} ({c.get('url', 'N/A')})"
                for cid, c in list(self.available_citations.items())[:10]
            )
        
        return f"""# Report Context

## Report Title
{self.report_title}

## Research Query
{self.report_query}

## Full Outline
{outline_text}

## Current Section: {self.section_title}
{self.section_description}

### Key Points to Cover
{key_points_text or "- Cover the main aspects of this topic"}

### Available Citations
{citations_text or "No specific citations provided - generate based on research."}

### Previous Sections Summary
{self.previous_sections_summary or "This is the first section."}

## Constraints
- Minimum words: {self.min_words}
- Maximum words: {self.max_words}
- Use markdown formatting
- Cite sources when making claims
- Stay focused on the section topic
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNK GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ChunkGenerator:
    """
    Générateur de chunks de contenu.
    
    Produit du contenu section par section, en respectant
    les limites de tokens et en maintenant le contexte.
    """
    
    def __init__(
        self,
        llm_caller: Callable[[str], AsyncGenerator[str, None]] = None,
        chunk_size_tokens: int = 4000,
    ):
        """
        Args:
            llm_caller: Fonction qui appelle le LLM et retourne un async generator.
                        Si None, utilise un générateur placeholder.
            chunk_size_tokens: Taille max des chunks en tokens.
        """
        self.llm_caller = llm_caller
        self.chunk_size_tokens = chunk_size_tokens
        
        # Estimation grossière: 1 token ≈ 4 caractères
        self._chars_per_token = 4
    
    async def generate_section(
        self,
        context: ChunkContext,
    ) -> AsyncGenerator[str, None]:
        """
        Génère le contenu d'une section.
        
        Args:
            context: Contexte de la section
            
        Yields:
            Chunks de contenu markdown
        """
        prompt = self._build_section_prompt(context)
        
        if self.llm_caller:
            async for chunk in self.llm_caller(prompt):
                yield chunk
        else:
            # Générateur placeholder
            async for chunk in self._placeholder_generator(context):
                yield chunk
    
    def _build_section_prompt(self, context: ChunkContext) -> str:
        """Construit le prompt pour générer une section."""
        return f"""{context.to_prompt_context()}

---

# Instructions

Generate the content for section "{context.section_title}".

Requirements:
1. Use proper markdown formatting (headers, lists, code blocks if needed)
2. Cite sources using [citation_id] format
3. Stay within {context.min_words}-{context.max_words} words
4. Be informative and well-structured
5. Connect with previous and next sections when relevant

Begin the section content now:

## {context.section_title}

"""
    
    async def _placeholder_generator(
        self,
        context: ChunkContext,
    ) -> AsyncGenerator[str, None]:
        """Générateur placeholder pour tests."""
        yield f"## {context.section_title}\n\n"
        
        yield f"{context.section_description or 'This section covers ' + context.section_title.lower()}.\n\n"
        
        if context.section_key_points:
            yield "### Key Points\n\n"
            for point in context.section_key_points:
                yield f"- {point}\n"
            yield "\n"
        
        yield "### Analysis\n\n"
        yield f"Detailed analysis of {context.section_title.lower()} would be generated here.\n\n"
        
        if context.available_citations:
            yield "### Sources\n\n"
            for cid, citation in list(context.available_citations.items())[:3]:
                yield f"- [{cid}] {citation.get('title', 'Source')}\n"
            yield "\n"
        
        yield f"\n*Section {context.current_section_idx + 1} of {len(context.full_outline)}*\n"


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT ASSEMBLER
# ═══════════════════════════════════════════════════════════════════════════════

class ReportAssembler:
    """
    Assemble un rapport complet à partir de sections.
    
    Usage:
        assembler = ReportAssembler(
            title="Research Report",
            query="Analyze AI safety approaches",
        )
        
        assembler.add_section("Introduction", description="Overview of AI safety")
        assembler.add_section("Methods", description="Research methodology")
        assembler.add_section("Results", description="Key findings")
        assembler.add_section("Conclusion", description="Summary and recommendations")
        
        async for chunk in assembler.generate():
            print(chunk, end="")
    """
    
    def __init__(
        self,
        title: str,
        query: str,
        generator: ChunkGenerator = None,
    ):
        self.title = title
        self.query = query
        self.generator = generator or ChunkGenerator()
        
        self.sections: List[SectionOutline] = []
        self.citations: Dict[str, Dict[str, Any]] = {}
        self.generated_summaries: List[str] = []
    
    def add_section(
        self,
        title: str,
        description: str = "",
        key_points: List[str] = None,
        min_words: int = 100,
        max_words: int = 2000,
    ):
        """Ajoute une section au rapport."""
        self.sections.append(SectionOutline(
            title=title,
            description=description,
            key_points=key_points or [],
            min_words=min_words,
            max_words=max_words,
        ))
    
    def add_citation(self, citation_id: str, citation_data: Dict[str, Any]):
        """Ajoute une citation disponible."""
        self.citations[citation_id] = citation_data
    
    async def generate(self) -> AsyncGenerator[str, None]:
        """
        Génère le rapport complet.
        
        Yields:
            Chunks de contenu markdown
        """
        # Header
        yield f"# {self.title}\n\n"
        yield f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        yield "---\n\n"
        
        # Table of contents
        yield "## Table of Contents\n\n"
        for i, section in enumerate(self.sections, 1):
            yield f"{i}. [{section.title}](#{section.title.lower().replace(' ', '-')})\n"
        yield "\n---\n\n"
        
        # Generate each section
        outline_titles = [s.title for s in self.sections]
        
        for idx, section in enumerate(self.sections):
            # Build context
            context = ChunkContext(
                report_title=self.title,
                report_query=self.query,
                section_title=section.title,
                section_description=section.description,
                section_key_points=section.key_points,
                full_outline=outline_titles,
                current_section_idx=idx,
                available_citations=self.citations,
                previous_sections_summary=self._get_previous_summary(),
                min_words=section.min_words,
                max_words=section.max_words,
            )
            
            # Generate section
            section_content = []
            async for chunk in self.generator.generate_section(context):
                section_content.append(chunk)
                yield chunk
            
            # Store summary for next section context
            full_content = "".join(section_content)
            self.generated_summaries.append(
                f"{section.title}: {full_content[:200]}..."
            )
            
            section.generated = True
            
            yield "\n\n"
        
        # Footer
        yield "---\n\n"
        yield "## Report Metadata\n\n"
        yield f"- Sections: {len(self.sections)}\n"
        yield f"- Citations: {len(self.citations)}\n"
        yield f"- Generated: {datetime.now(timezone.utc).isoformat()}\n"
    
    def _get_previous_summary(self) -> str:
        """Retourne un résumé des sections précédentes."""
        if not self.generated_summaries:
            return ""
        return "\n".join(self.generated_summaries[-3:])  # 3 dernières sections


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "SectionOutline",
    "ChunkContext",
    "ChunkGenerator",
    "ReportAssembler",
]
