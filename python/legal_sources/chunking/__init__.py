"""
Legal Sources — Chunking

Découpage robuste des documents juridiques pour indexation.
"""

from .chunker import LegalChunker, ChunkingStrategy, ChunkerConfig

__all__ = ["LegalChunker", "ChunkingStrategy", "ChunkerConfig"]
