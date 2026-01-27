"""
Legal Sources — Open Data Juridique France (Enterprise Edition)

Package d'ingestion des sources juridiques françaises en open data.
Conformité audit: licences et CGU vérifiées et sourcées.

Sources supportées:
- LEGI: Codes, lois, règlements consolidés (Licence Ouverte 2.0)
- JORF: Journal Officiel (Licence Ouverte 2.0)
- CASS: Arrêts Cour de cassation via Judilibre (Licence Ouverte 2.0 + CGU)
- JADE: Jurisprudence administrative (P1)
- CONSTIT: Décisions Conseil constitutionnel (P1)

Usage:
    python -m legal_sources ingest --source cass --since 2025-01-01
    python -m legal_sources ingest --source cass --limit 50 --smoke
    python -m legal_sources search --q "L132-8" --source legi --limit 10
    python -m legal_sources lookup --origin-id LEGIARTI000006420055
    python -m legal_sources export-audit --chunk-ids id1,id2 --out audit.json
    python -m legal_sources verify
    python -m legal_sources stats

Toutes les données sont sous Licence Ouverte 2.0 (Etalab).
CGU spécifiques selon les sources (cf. docs/legal_sources_fr.md).
"""

from .models import (
    LegalSource,
    AccessMode,
    Jurisdiction,
    DocumentType,
    LegalDoc,
    LegalChunk,
    Provenance,
    IngestionResult,
    ProvenanceValidationError,
    SOURCE_COMPLIANCE,
    create_compliant_provenance,
)

from .config import LegalSourcesConfig, get_default_config

from .indexing import LegalIndex, SearchResult

from .audit_bundle import (
    AuditBundle,
    AuditEntry,
    build_audit_bundle,
    build_audit_bundle_from_chunks,
    validate_audit_bundle,
    generate_audit_report,
)

from .resilience import (
    RetryConfig,
    CheckpointData,
    CheckpointManager,
    RateLimiter,
    ResilientSession,
    retry_with_backoff,
)

__version__ = "1.0.0"

__all__ = [
    # Models
    "LegalSource",
    "AccessMode",
    "Jurisdiction",
    "DocumentType",
    "LegalDoc",
    "LegalChunk",
    "Provenance",
    "IngestionResult",
    "ProvenanceValidationError",
    "SOURCE_COMPLIANCE",
    "create_compliant_provenance",
    
    # Config
    "LegalSourcesConfig",
    "get_default_config",
    
    # Indexing
    "LegalIndex",
    "SearchResult",
    
    # Audit
    "AuditBundle",
    "AuditEntry",
    "build_audit_bundle",
    "build_audit_bundle_from_chunks",
    "validate_audit_bundle",
    "generate_audit_report",
    
    # Resilience
    "RetryConfig",
    "CheckpointData",
    "CheckpointManager",
    "RateLimiter",
    "ResilientSession",
    "retry_with_backoff",
]
