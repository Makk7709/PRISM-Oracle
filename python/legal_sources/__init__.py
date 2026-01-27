"""
Legal Sources — Open Data Juridique France

Package d'ingestion des sources juridiques françaises en open data.

Sources supportées:
- LEGI: Codes, lois, règlements consolidés
- JORF: Journal Officiel
- CASS: Arrêts Cour de cassation (via Judilibre)
- JADE: Jurisprudence administrative (P1)
- CONSTIT: Décisions Conseil constitutionnel (P1)

Usage:
    python -m legal_sources ingest --source legi --since 2025-01-01
    python -m legal_sources ingest --source cass --since 2025-01-01
    python -m legal_sources verify

Licence: Les données sont sous Licence Ouverte 2.0 (Etalab)
"""

from .models import (
    LegalSource,
    LegalDoc,
    LegalChunk,
    Provenance,
    IngestionResult,
)

from .config import LegalSourcesConfig, get_default_config

__version__ = "0.1.0"

__all__ = [
    "LegalSource",
    "LegalDoc",
    "LegalChunk",
    "Provenance",
    "IngestionResult",
    "LegalSourcesConfig",
    "get_default_config",
]
