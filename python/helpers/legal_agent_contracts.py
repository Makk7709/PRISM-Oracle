"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    P4.1 + P5: LEGAL INTER-AGENT CONTRACTS                    ║
║                                                                              ║
║  Strict data models for agent collaboration.                                ║
║  Sub-agents produce ONLY these artifacts, NEVER final answers.              ║
║                                                                              ║
║  Artifacts:                                                                  ║
║  - FactExtraction: extracted facts from user query                          ║
║  - SourceNote: reference to an official source (with version)               ║
║  - ClaimProposal: a claim with citation or hypothesis basis                ║
║  - Critique: issues, missing info, contradictions                           ║
║  - LegalTextVersion: versioned legal text for temporal opposability (P5)    ║
║                                                                              ║
║  INVARIANTS:                                                                 ║
║  - No artifact may contain a "final_answer" field                           ║
║  - SourceNote must reference whitelisted publisher                          ║
║  - CITED claims must have valid SourceNote with excerpt_hash                ║
║  - P5: SourceNote must have LegalTextVersion for temporal opposability      ║
║                                                                              ║
║  Version: 1.1.0 (P5 Versioning)                                             ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

# Constantes (déduplication littéraux — python:S1192)
_ERR_MUST_NOT_BE_EMPTY = "Must not be empty"


# CONSTANTS & WHITELIST
# ═══════════════════════════════════════════════════════════════════════════════

class Publisher(str, Enum):
    """Whitelisted publishers for official sources."""
    # France
    LEGIFRANCE = "legifrance"
    LEGI = "legi"  # Alias for legifrance
    CASS = "cour_de_cassation"
    CONSEIL_ETAT = "conseil_etat"
    CONSEIL_CONSTITUTIONNEL = "conseil_constitutionnel"
    # European Union
    EURLEX = "eur_lex"
    CJUE = "cjue"
    CEDH = "cedh"
    
    @classmethod
    def is_whitelisted(cls, publisher: str) -> bool:
        """Check if a publisher is in the whitelist."""
        if not publisher:
            return False
        # Normalize: lowercase, replace hyphens and spaces with underscores
        normalized = publisher.lower().replace("-", "_").replace(" ", "_")
        
        # Check direct match with enum values
        for p in cls:
            if p.value == normalized:
                return True
        
        # Check common aliases
        aliases = {
            "legifrance": True,
            "legi": True,
            "eur_lex": True,
            "eurlex": True,
            "cass": True,
            "cour_de_cassation": True,
        }
        return aliases.get(normalized, False)
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all whitelisted publishers."""
        return [p.value for p in cls]


class Jurisdiction(str, Enum):
    """Supported jurisdictions."""
    FR = "fr"
    EU = "eu"
    ECHR = "echr"  # European Court of Human Rights
    
    @classmethod
    def is_valid(cls, jurisdiction: str) -> bool:
        return any(j.value == jurisdiction.lower() for j in cls)


class ClaimType(str, Enum):
    """Claim types for ClaimProposal."""
    CITED = "cited"       # Must have SourceNote with excerpt_hash
    HYPOTHESIS = "hypothesis"  # Must have basis


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

class ContractValidationError(Exception):
    """Raised when an inter-agent contract is invalid."""
    def __init__(self, artifact_type: str, field: str, reason: str):
        self.artifact_type = artifact_type
        self.field = field
        self.reason = reason
        super().__init__(f"{artifact_type}.{field}: {reason}")


class FinalAnswerDetectedError(Exception):
    """Raised when a sub-agent tries to produce a final answer."""
    def __init__(self, artifact_type: str, detected_text: str):
        self.artifact_type = artifact_type
        self.detected_text = detected_text[:100]  # Truncate
        super().__init__(f"Sub-agent attempted final answer in {artifact_type}")


class NonWhitelistedPublisherError(Exception):
    """Raised when a SourceNote references a non-whitelisted publisher."""
    def __init__(self, publisher: str, allowed: List[str]):
        self.publisher = publisher
        self.allowed = allowed
        super().__init__(f"Publisher '{publisher}' not in whitelist: {allowed}")


class VersionAmbiguityError(Exception):
    """P5: Raised when multiple valid versions exist for a text at as_of_date."""
    def __init__(self, text_id: str, as_of_date: date, version_count: int):
        self.text_id = text_id
        self.as_of_date = as_of_date
        self.version_count = version_count
        super().__init__(
            f"Version ambiguity for text '{text_id}' at {as_of_date}: "
            f"{version_count} valid versions found"
        )


class VersionNotFoundError(Exception):
    """P5: Raised when no valid version exists for a text at as_of_date."""
    def __init__(self, text_id: str, as_of_date: date, reason: str = ""):
        self.text_id = text_id
        self.as_of_date = as_of_date
        self.reason = reason
        super().__init__(
            f"No valid version for text '{text_id}' at {as_of_date}"
            + (f": {reason}" if reason else "")
        )


class MissingAsOfDateError(Exception):
    """P5: Raised when as_of_date is required but not provided."""
    def __init__(self, risk_tier: str, scope: str):
        self.risk_tier = risk_tier
        self.scope = scope
        super().__init__(
            f"as_of_date required for risk_tier={risk_tier}, scope={scope}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# P5: LEGAL TEXT VERSION
# ═══════════════════════════════════════════════════════════════════════════════

def is_version_enforcement_enabled() -> bool:
    """P5: Check if version enforcement is enabled."""
    return os.environ.get("LEGAL_VERSION_ENFORCEMENT", "1") == "1"


def parse_date(value: Union[str, date, None]) -> Optional[date]:
    """Parse a date from string or return as-is if already date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Handle ISO format: YYYY-MM-DD
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


@dataclass
class LegalTextVersion:
    """
    P5: Versioned legal text for temporal opposability.
    
    Every legal text (article, arrêt, etc.) can have multiple versions
    over time. This class represents one specific version.
    
    INVARIANTS:
    - effective_from must be set
    - effective_to can be None (still in force)
    - as_of_date_resolved tracks when this version was resolved
    """
    text_id: str
    version_id: str
    effective_from: date
    effective_to: Optional[date] = None
    is_current: bool = True
    as_of_date_resolved: Optional[date] = None
    
    # Extended metadata
    title: Optional[str] = None
    modification_reason: Optional[str] = None
    previous_version_id: Optional[str] = None
    
    def __post_init__(self):
        # Parse dates if strings
        if isinstance(self.effective_from, str):
            self.effective_from = parse_date(self.effective_from)
        if isinstance(self.effective_to, str):
            self.effective_to = parse_date(self.effective_to)
        if isinstance(self.as_of_date_resolved, str):
            self.as_of_date_resolved = parse_date(self.as_of_date_resolved)
        
        self.validate()
    
    def validate(self):
        """Validate the version."""
        if not self.text_id:
            raise ContractValidationError(
                "LegalTextVersion", "text_id", _ERR_MUST_NOT_BE_EMPTY
            )
        
        if not self.version_id:
            raise ContractValidationError(
                "LegalTextVersion", "version_id", _ERR_MUST_NOT_BE_EMPTY
            )
        
        if self.effective_from is None:
            raise ContractValidationError(
                "LegalTextVersion", "effective_from", "Must be set"
            )
        
        # effective_to must be after effective_from if set
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ContractValidationError(
                "LegalTextVersion", "effective_to",
                f"Must be after effective_from ({self.effective_from})"
            )
    
    def is_valid_at(self, as_of_date: date) -> bool:
        """Check if this version is valid at the given date."""
        if as_of_date < self.effective_from:
            return False
        if self.effective_to is not None and as_of_date > self.effective_to:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text_id": self.text_id,
            "version_id": self.version_id,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "is_current": self.is_current,
            "as_of_date_resolved": self.as_of_date_resolved.isoformat() if self.as_of_date_resolved else None,
            "title": self.title,
            "modification_reason": self.modification_reason,
            "previous_version_id": self.previous_version_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalTextVersion":
        return cls(**data)


def resolve_version(
    versions: List[LegalTextVersion],
    as_of_date: date,
) -> Tuple[Optional[LegalTextVersion], List[LegalTextVersion]]:
    """
    P5: Resolve the valid version(s) for a text at a given date.
    
    Args:
        versions: List of all versions for a text
        as_of_date: The date to resolve for
        
    Returns:
        (resolved_version, all_valid_versions)
        - If exactly 1 valid version: (version, [version])
        - If 0 valid versions: (None, [])
        - If >1 valid versions (ambiguous): (None, [v1, v2, ...])
    """
    valid_versions = [v for v in versions if v.is_valid_at(as_of_date)]
    
    if len(valid_versions) == 1:
        resolved = valid_versions[0]
        # Update as_of_date_resolved
        resolved.as_of_date_resolved = as_of_date
        return (resolved, valid_versions)
    
    return (None, valid_versions)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_excerpt_hash(excerpt: str) -> str:
    """Compute SHA256 hash of an excerpt for integrity verification."""
    return hashlib.sha256(excerpt.encode("utf-8")).hexdigest()[:16]


def detect_final_answer(text: str) -> bool:
    """
    Detect if text contains patterns indicating a final answer.
    
    Sub-agents must NOT produce final answers.
    """
    patterns = [
        r"\b(en conclusion|pour conclure|en résumé)\b",
        r"\b(ma réponse est|la réponse est|voici la réponse)\b",
        r"\b(je conclus que|je réponds)\b",
        r"^(réponse|answer|conclusion)\s*:",
        r"\b(final answer|réponse finale)\b",
    ]
    
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    return False


def validate_no_final_answer(artifact_type: str, data: Dict[str, Any]):
    """
    Validate that no field contains a final answer.
    
    Raises:
        FinalAnswerDetectedError: If final answer detected
    """
    def check_value(value: Any, path: str):
        if isinstance(value, str):
            if detect_final_answer(value):
                raise FinalAnswerDetectedError(artifact_type, value)
        elif isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                check_value(item, f"{path}[{i}]")
    
    check_value(data, artifact_type)


# ═══════════════════════════════════════════════════════════════════════════════
# P4.1: FACT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FactExtraction:
    """
    Extracted facts from user query.
    
    Produced by: Extraction Agent
    Consumed by: Legal Orchestrator
    
    INVARIANTS:
    - Must have at least one fact
    - No final answer allowed in any field
    """
    facts: List[str]
    ambiguities: List[str] = field(default_factory=list)
    parties: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    context_hints: Dict[str, str] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        self.validate()
    
    def validate(self):
        """Validate the artifact."""
        if not self.facts:
            raise ContractValidationError("FactExtraction", "facts", "Must have at least one fact")
        
        # Check no final answer
        validate_no_final_answer("FactExtraction", asdict(self))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactExtraction":
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# P4.1: SOURCE NOTE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SourceNote:
    """
    Reference to an official source.
    
    Produced by: Retrieval Agent, Research Agent
    Consumed by: Draft Builder, Judge
    
    INVARIANTS:
    - publisher must be whitelisted
    - excerpt_hash must match excerpt content
    - origin_url must be valid URL
    - P5: legal_version must be set if version enforcement enabled
    """
    origin_url: str
    publisher: str
    jurisdiction: str
    excerpt: str
    excerpt_hash: str
    chunk_id: str
    confidence: float = 0.8
    # Extended provenance (P4.3)
    document_id: Optional[str] = None
    retrieved_at: Optional[str] = None
    content_hash: Optional[str] = None
    license_tag: Optional[str] = None
    version_date: Optional[str] = None
    title: Optional[str] = None
    correlation_id: Optional[str] = None
    # P5: Legal text version
    legal_version: Optional[LegalTextVersion] = None
    # SESSION 4: Source taxonomy (retrocompatible — defaults None)
    source_type_fr: Optional[str] = None
    source_origin: Optional[str] = None
    reliability_percent: Optional[int] = None
    agent_attribution: Optional[str] = None
    
    def __post_init__(self):
        # Convert dict to LegalTextVersion if needed
        if isinstance(self.legal_version, dict):
            self.legal_version = LegalTextVersion.from_dict(self.legal_version)
        
        self.validate()
    
    def validate(self):
        """Validate the artifact."""
        # Publisher must be whitelisted
        if not Publisher.is_whitelisted(self.publisher):
            raise NonWhitelistedPublisherError(
                self.publisher, 
                Publisher.get_all()
            )
        
        # Jurisdiction must be valid
        if not Jurisdiction.is_valid(self.jurisdiction):
            raise ContractValidationError(
                "SourceNote", "jurisdiction", 
                f"Invalid jurisdiction: {self.jurisdiction}"
            )
        
        # Origin URL must look valid
        if not self.origin_url.startswith(("http://", "https://")):
            raise ContractValidationError(
                "SourceNote", "origin_url",
                "Must be a valid URL (http:// or https://)"
            )
        
        # Excerpt hash must match
        computed_hash = compute_excerpt_hash(self.excerpt)
        if self.excerpt_hash != computed_hash:
            raise ContractValidationError(
                "SourceNote", "excerpt_hash",
                f"Hash mismatch: expected {computed_hash}, got {self.excerpt_hash}"
            )
        
        # Confidence in range
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractValidationError(
                "SourceNote", "confidence",
                f"Must be in [0, 1], got {self.confidence}"
            )
        
        # P5: Legal version required if enforcement enabled
        if is_version_enforcement_enabled() and self.legal_version is None:
            raise ContractValidationError(
                "SourceNote", "legal_version",
                "P5: legal_version required for temporal opposability"
            )
        
        # No final answer (exclude legal_version from check)
        data = asdict(self)
        data.pop("legal_version", None)
        validate_no_final_answer("SourceNote", data)
    
    @property
    def has_resolved_version(self) -> bool:
        """P5: Check if this SourceNote has a resolved version."""
        return (
            self.legal_version is not None 
            and self.legal_version.as_of_date_resolved is not None
        )
    
    @property
    def version_id(self) -> Optional[str]:
        """P5: Get the version ID if available."""
        return self.legal_version.version_id if self.legal_version else None
    
    @property
    def effective_from(self) -> Optional[date]:
        """P5: Get the effective_from date if available."""
        return self.legal_version.effective_from if self.legal_version else None
    
    @property
    def effective_to(self) -> Optional[date]:
        """P5: Get the effective_to date if available."""
        return self.legal_version.effective_to if self.legal_version else None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "origin_url": self.origin_url,
            "publisher": self.publisher,
            "jurisdiction": self.jurisdiction,
            "excerpt": self.excerpt,
            "excerpt_hash": self.excerpt_hash,
            "chunk_id": self.chunk_id,
            "confidence": self.confidence,
            "document_id": self.document_id,
            "retrieved_at": self.retrieved_at,
            "content_hash": self.content_hash,
            "license_tag": self.license_tag,
            "version_date": self.version_date,
            "title": self.title,
            "correlation_id": self.correlation_id,
        }
        if self.legal_version:
            result["legal_version"] = self.legal_version.to_dict()
        if self.source_type_fr is not None:
            result["source_type_fr"] = self.source_type_fr
        if self.source_origin is not None:
            result["source_origin"] = self.source_origin
        if self.reliability_percent is not None:
            result["reliability_percent"] = self.reliability_percent
        if self.agent_attribution is not None:
            result["agent_attribution"] = self.agent_attribution
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceNote":
        return cls(**data)
    
    @classmethod
    def create(
        cls,
        origin_url: str,
        publisher: str,
        jurisdiction: str,
        excerpt: str,
        chunk_id: str,
        legal_version: Optional[LegalTextVersion] = None,
        **kwargs,
    ) -> "SourceNote":
        """Factory method that computes excerpt_hash automatically."""
        return cls(
            origin_url=origin_url,
            publisher=publisher,
            jurisdiction=jurisdiction,
            excerpt=excerpt,
            excerpt_hash=compute_excerpt_hash(excerpt),
            chunk_id=chunk_id,
            legal_version=legal_version,
            **kwargs,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# P4.1: CLAIM PROPOSAL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClaimProposal:
    """
    A proposed claim with citation or hypothesis basis.
    
    Produced by: Draft Builder Agent
    Consumed by: Judge, Consensus
    
    INVARIANTS:
    - CITED claims must have source_note with whitelisted publisher
    - HYPOTHESIS claims must have basis
    - No final answer allowed
    """
    claim_text: str
    claim_type: ClaimType
    citation: Optional[str] = None
    source_note: Optional[SourceNote] = None
    source_chunk_id: Optional[str] = None
    basis_if_hypothesis: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        # Convert string to enum if needed
        if isinstance(self.claim_type, str):
            self.claim_type = ClaimType(self.claim_type.lower())
        
        # Convert dict to SourceNote if needed
        if isinstance(self.source_note, dict):
            self.source_note = SourceNote.from_dict(self.source_note)
        
        self.validate()
    
    def validate(self):
        """Validate the artifact."""
        if not self.claim_text:
            raise ContractValidationError(
                "ClaimProposal", "claim_text", _ERR_MUST_NOT_BE_EMPTY
            )
        
        if self.claim_type == ClaimType.CITED:
            # CITED must have SourceNote
            if self.source_note is None:
                raise ContractValidationError(
                    "ClaimProposal", "source_note",
                    "CITED claim must have a SourceNote"
                )
            
            # Citation should be present
            if not self.citation:
                raise ContractValidationError(
                    "ClaimProposal", "citation",
                    "CITED claim must have a citation"
                )
        
        elif self.claim_type == ClaimType.HYPOTHESIS:
            # HYPOTHESIS must have basis
            if not self.basis_if_hypothesis:
                raise ContractValidationError(
                    "ClaimProposal", "basis_if_hypothesis",
                    "HYPOTHESIS claim must have a basis"
                )
        
        # No final answer
        data = asdict(self)
        # Remove source_note from check (already validated)
        data.pop("source_note", None)
        validate_no_final_answer("ClaimProposal", data)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "citation": self.citation,
            "source_chunk_id": self.source_chunk_id,
            "basis_if_hypothesis": self.basis_if_hypothesis,
            "correlation_id": self.correlation_id,
        }
        if self.source_note:
            result["source_note"] = self.source_note.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaimProposal":
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# P4.1: CRITIQUE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Critique:
    """
    Issues, missing info, and contradictions found in a draft.
    
    Produced by: Judge Agent, Review Agent
    Consumed by: Orchestrator
    
    INVARIANTS:
    - Must have at least one issue, missing_info, or contradiction
    - No final answer allowed
    """
    issues: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    recommendation: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        self.validate()
    
    def validate(self):
        """Validate the artifact."""
        # Must have at least one finding
        if not (self.issues or self.missing_info or self.contradictions):
            raise ContractValidationError(
                "Critique", "issues/missing_info/contradictions",
                "Must have at least one finding"
            )
        
        # No final answer
        validate_no_final_answer("Critique", asdict(self))
    
    @property
    def is_blocking(self) -> bool:
        """Check if critique should block output."""
        return self.severity in ("high", "critical")
    
    @property
    def total_findings(self) -> int:
        return len(self.issues) + len(self.missing_info) + len(self.contradictions)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Critique":
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# ARTIFACT TYPE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

ARTIFACT_TYPES = {
    "FactExtraction": FactExtraction,
    "SourceNote": SourceNote,
    "ClaimProposal": ClaimProposal,
    "Critique": Critique,
    "LegalTextVersion": LegalTextVersion,
}


def parse_artifact(artifact_type: str, data: Dict[str, Any]) -> Union[FactExtraction, SourceNote, ClaimProposal, Critique]:
    """
    Parse and validate an artifact from dict.
    
    Raises:
        ContractValidationError: If validation fails
        FinalAnswerDetectedError: If final answer detected
        NonWhitelistedPublisherError: If publisher not whitelisted
    """
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"Unknown artifact type: {artifact_type}")
    
    return ARTIFACT_TYPES[artifact_type].from_dict(data)


def validate_artifact_batch(artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate a batch of artifacts.
    
    Returns:
        List of validation results with status and errors
    """
    results = []
    
    for i, artifact_data in enumerate(artifacts):
        artifact_type = artifact_data.get("_type")
        if not artifact_type:
            results.append({
                "index": i,
                "status": "error",
                "error": "Missing _type field",
            })
            continue
        
        try:
            parse_artifact(artifact_type, {k: v for k, v in artifact_data.items() if k != "_type"})
            results.append({
                "index": i,
                "status": "valid",
                "artifact_type": artifact_type,
            })
        except Exception as e:
            results.append({
                "index": i,
                "status": "error",
                "artifact_type": artifact_type,
                "error": str(e),
            })
    
    return results


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "Publisher",
    "Jurisdiction",
    "ClaimType",
    # P5: Versioning
    "LegalTextVersion",
    # Artifacts
    "FactExtraction",
    "SourceNote",
    "ClaimProposal",
    "Critique",
    # Errors
    "ContractValidationError",
    "FinalAnswerDetectedError",
    "NonWhitelistedPublisherError",
    # P5: Version Errors
    "VersionAmbiguityError",
    "VersionNotFoundError",
    "MissingAsOfDateError",
    # Functions
    "compute_excerpt_hash",
    "detect_final_answer",
    "validate_no_final_answer",
    "parse_artifact",
    "validate_artifact_batch",
    # P5: Version functions
    "is_version_enforcement_enabled",
    "parse_date",
    "resolve_version",
    # Registry
    "ARTIFACT_TYPES",
]
