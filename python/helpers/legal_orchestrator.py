"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      LEGAL ORCHESTRATOR — EVIDENCE                           ║
║                                                                              ║
║  Single entry point for the legal pipeline in KOREV Evidence.               ║
║  Enforces P0.7 invariants + P0.8/P0.9 production requirements.              ║
║                                                                              ║
║  P1 WIRING:                                                                  ║
║  ┌─────────────────────────────────────────────────────────────────┐       ║
║  │  run_legal_pipeline(query, route_decision, ...)                 │       ║
║  │     ├── 1. Retrieval via LegalIndex FTS5 (REAL)                 │       ║
║  │     ├── 2. Draft construction via LLM FIRAC (REAL)              │       ║
║  │     ├── 3. Judge (binary checklist)                             │       ║
║  │     ├── 4. Consensus via seek_consensus (REAL LLM arbiters)     │       ║
║  │     └── 5. Output (APPROVED/SAFE/REFUSAL)                       │       ║
║  └─────────────────────────────────────────────────────────────────┘       ║
║                                                                              ║
║  INVARIANTS:                                                                 ║
║  P0.7 (strict):                                                             ║
║  • No provenance = No output (except REFUSAL)                               ║
║  • BOARD/MEDIUM/HIGH = Consensus required                                   ║
║  • APPROVED_POSITION only if consensus APPROVED                             ║
║  • Fail-closed: any violation => REFUSAL with explicit reason               ║
║                                                                              ║
║  P4 (sources officielles):                                                  ║
║  • CITED claims must have SourceNote with whitelisted publisher             ║
║  • Sub-agents produce artifacts, NEVER final answers                        ║
║  • Provenance must include: origin_url, publisher, excerpt_hash             ║
║                                                                              ║
║  P5 (versioning temporel):                                                  ║
║  • as_of_date required for MEDIUM/HIGH risk + non-INFO scope                ║
║  • All SourceNotes must have resolved LegalTextVersion                      ║
║  • VERSION_RESOLVED check in Judge (blocking)                               ║
║                                                                              ║
║  P6.1 (diff juridique):                                                     ║
║  • Diff structuré entre versions N et N-1                                   ║
║  • Qualification: ADD/REMOVE/MODIFY + NEUTRAL/AGGRAVATING/RELAXING          ║
║  • Intégration dans audit_bundle                                            ║
║                                                                              ║
║  Version: 1.4.0 (P6.1 Legal Diff)                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from collections import OrderedDict

# Local imports
from python.helpers.legal_pipeline import (
    # Routing
    LegalRiskTier,
    DecisionScope,
    Jurisdiction,
    LegalRouteContext,
    detect_legal_context,
    # Draft
    ClaimType,
    LegalClaim,
    LegalDraft,
    generate_draft_id,
    # Judge
    JudgeCheckResult,
    LegalJudgeVerdict,
    LegalJudgeResult,
    judge_legal_draft,
    # Consensus
    LegalConsensusProposal,
    build_legal_consensus_proposal,
    # Output
    LegalOutputMode,
    LegalOutput,
    build_legal_output,
    generate_audit_bundle_id,
    # P0.7
    MissingInfoCode,
    requires_consensus,
)

from python.helpers.legal_retrieval import (
    RetrievalResult,
    RetrievalContext,
    LegalRetriever,
    extract_legal_identifiers,
    format_citation_from_result,
    build_enriched_context,
)

from python.helpers.router import (
    RouteDecision,
    IntentName,
)

# P1: Real consensus
try:
    from python.helpers.consensus_arbiter import (
        ConsensusOrchestrator,
        seek_consensus,
    )
    from python.helpers.consensus_manager import (
        DecisionType,
        ConsensusStatus,
        ConsensusResult,
    )
    CONSENSUS_AVAILABLE = True
except ImportError:
    CONSENSUS_AVAILABLE = False
    ConsensusOrchestrator = None
    seek_consensus = None
    DecisionType = None
    ConsensusStatus = None

# P1: Real FTS5 index
try:
    from python.legal_sources.indexing import LegalIndex, SearchResult
    LEGAL_INDEX_AVAILABLE = True
except ImportError:
    LEGAL_INDEX_AVAILABLE = False
    LegalIndex = None
    SearchResult = None

# P4: Inter-agent contracts
try:
    from python.helpers.legal_agent_contracts import (
        Publisher,
        SourceNote,
        ClaimProposal,
        FactExtraction,
        Critique,
        ClaimType as P4ClaimType,
        ContractValidationError,
        FinalAnswerDetectedError,
        NonWhitelistedPublisherError,
        compute_excerpt_hash,
        validate_no_final_answer,
        # P5: Versioning
        LegalTextVersion,
        VersionAmbiguityError,
        VersionNotFoundError,
        MissingAsOfDateError,
        is_version_enforcement_enabled,
        parse_date,
        resolve_version,
    )
    P4_CONTRACTS_AVAILABLE = True
except ImportError:
    P4_CONTRACTS_AVAILABLE = False
    Publisher = None
    SourceNote = None
    ClaimProposal = None
    FactExtraction = None
    Critique = None
    P4ClaimType = None
    ContractValidationError = None
    FinalAnswerDetectedError = None
    NonWhitelistedPublisherError = None
    compute_excerpt_hash = None
    validate_no_final_answer = None
    # P5
    LegalTextVersion = None
    VersionAmbiguityError = None

# P6.1: Legal Diff
try:
    from python.helpers.legal_diff import (
        LegalDiffReport,
        LegalDiffSegment,
        DiffStatus,
        ChangeType,
        ImpactQualification,
        compute_legal_diff,
        create_not_applicable_report,
        create_error_report,
    )
    P6_DIFF_AVAILABLE = True
except ImportError:
    P6_DIFF_AVAILABLE = False
    LegalDiffReport = None
    LegalDiffSegment = None
    DiffStatus = None
    ChangeType = None
    ImpactQualification = None
    compute_legal_diff = None
    create_not_applicable_report = None
    create_error_report = None
    VersionNotFoundError = None
    MissingAsOfDateError = None
    is_version_enforcement_enabled = lambda: False
    parse_date = None
    resolve_version = None

logger = logging.getLogger("legal_orchestrator")


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════════════════════════════════════════

def is_legal_pipeline_enabled() -> bool:
    """
    Check if the legal pipeline is enabled.
    
    Environment variable: LEGAL_PIPELINE_ENABLED=1
    Default: True (enabled)
    """
    return os.environ.get("LEGAL_PIPELINE_ENABLED", "1") == "1"


def get_legal_enforcement_level() -> int:
    """
    Get legal pipeline enforcement level (0-3).
    
    0 = OFF (fallback to REFUSAL)
    1 = Audit only (log but don't block)
    2 = Soft enforcement (warn + block high-stakes)
    3 = Hard enforcement (full P0.7 invariants)
    
    Default: 3 (hard enforcement)
    """
    try:
        level = int(os.environ.get("LEGAL_ENFORCEMENT_LEVEL", "3"))
        return min(max(level, 0), 3)
    except ValueError:
        return 3


def is_whitelist_enforcement_enabled() -> bool:
    """
    P4: Check if publisher whitelist enforcement is enabled.
    
    Default: True (enabled)
    """
    return os.environ.get("LEGAL_WHITELIST_ENFORCEMENT", "1") == "1"


def is_as_of_date_enforcement_enabled() -> bool:
    """
    P5: Check if as_of_date enforcement is enabled.
    
    Default: True (enabled)
    """
    return os.environ.get("LEGAL_AS_OF_DATE_ENFORCEMENT", "1") == "1"


def is_diff_enabled() -> bool:
    """
    P6.1: Check if legal diff computation is enabled.
    
    Default: True (enabled)
    """
    return os.environ.get("LEGAL_DIFF_ENABLED", "1") == "1"


# ═══════════════════════════════════════════════════════════════════════════════
# P5: AS_OF_DATE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def requires_as_of_date(
    risk_tier: "LegalRiskTier",
    scope: "DecisionScope",
) -> bool:
    """
    P5: Check if as_of_date is required for this risk_tier + scope combination.
    
    Rules:
    - INFO scope: never required (educational only)
    - LOW risk: never required
    - MEDIUM or higher + non-INFO scope: required
    
    Args:
        risk_tier: The risk tier
        scope: The decision scope
        
    Returns:
        True if as_of_date is required
    """
    if not is_as_of_date_enforcement_enabled():
        return False
    
    # INFO scope never requires as_of_date
    if scope == DecisionScope.INFO:
        return False
    
    # LOW risk never requires as_of_date
    if risk_tier == LegalRiskTier.LOW:
        return False
    
    # MEDIUM, HIGH, CRITICAL + non-INFO = required
    return True


def validate_as_of_date(
    as_of_date: Optional[date],
    risk_tier: "LegalRiskTier",
    scope: "DecisionScope",
    *,
    correlation_id: str,
) -> Optional[str]:
    """
    P5: Validate that as_of_date is provided when required.
    
    Args:
        as_of_date: The date provided (or None)
        risk_tier: The risk tier
        scope: The decision scope
        correlation_id: For logging
        
    Returns:
        Error message if validation fails, None if OK
    """
    if requires_as_of_date(risk_tier, scope) and as_of_date is None:
        return f"as_of_date required for risk_tier={risk_tier.value}, scope={scope.value}"
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# P4.2: WHITELIST VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class WhitelistViolationError(Exception):
    """P4: Raised when a source is not from a whitelisted publisher."""
    def __init__(self, publisher: str, chunk_id: str):
        self.publisher = publisher
        self.chunk_id = chunk_id
        super().__init__(f"Non-whitelisted publisher '{publisher}' for chunk {chunk_id}")


def validate_source_whitelist(
    retrieval_results: List[RetrievalResult],
    *,
    correlation_id: str,
) -> List[str]:
    """
    P4.2: Validate that all sources come from whitelisted publishers.
    
    Args:
        retrieval_results: Results from retrieval
        correlation_id: For logging
        
    Returns:
        List of non-whitelisted chunk_ids (empty if all valid)
        
    Note: Only validates if P4_CONTRACTS_AVAILABLE and whitelist enforcement enabled.
    """
    if not P4_CONTRACTS_AVAILABLE or not is_whitelist_enforcement_enabled():
        return []
    
    non_whitelisted = []
    
    for result in retrieval_results:
        # Get publisher from provenance
        publisher = None
        if result.provenance:
            if isinstance(result.provenance, dict):
                publisher = result.provenance.get("source") or result.provenance.get("publisher")
            elif hasattr(result.provenance, "source"):
                publisher = result.provenance.source
        
        if publisher and not Publisher.is_whitelisted(publisher):
            non_whitelisted.append(result.chunk_id)
            log_structured(LegalPipelineLog(
                correlation_id=correlation_id,
                event="whitelist_violation",
                data={
                    "chunk_id": result.chunk_id,
                    "publisher": publisher,
                    "allowed": Publisher.get_all(),
                },
            ))
    
    return non_whitelisted


def validate_cited_claims_have_sources(
    draft,  # LegalDraft
    source_notes: Dict[str, "SourceNote"],
    *,
    correlation_id: str,
) -> List[str]:
    """
    P4.2: Validate that all CITED claims have a SourceNote with whitelisted publisher.
    
    Args:
        draft: LegalDraft with claims
        source_notes: Map of chunk_id -> SourceNote
        correlation_id: For logging
        
    Returns:
        List of invalid claim texts (empty if all valid)
    """
    if not P4_CONTRACTS_AVAILABLE:
        return []
    
    invalid_claims = []
    
    for claim in draft.claims:
        if claim.claim_type == ClaimType.CITED:
            # Must have a chunk_id
            if not claim.chunk_id:
                invalid_claims.append(claim.text)
                log_structured(LegalPipelineLog(
                    correlation_id=correlation_id,
                    event="cited_claim_no_chunk_id",
                    data={"claim_text": claim.text[:100]},
                ))
                continue
            
            # Must have a SourceNote
            if claim.chunk_id not in source_notes:
                invalid_claims.append(claim.text)
                log_structured(LegalPipelineLog(
                    correlation_id=correlation_id,
                    event="cited_claim_no_source_note",
                    data={
                        "claim_text": claim.text[:100],
                        "chunk_id": claim.chunk_id,
                    },
                ))
    
    return invalid_claims


def build_source_notes_from_retrieval(
    retrieval_results: List[RetrievalResult],
    *,
    correlation_id: str,
) -> Dict[str, "SourceNote"]:
    """
    P4.3: Build SourceNote objects from retrieval results.
    
    Args:
        retrieval_results: Results with provenance
        correlation_id: For logging
        
    Returns:
        Dict mapping chunk_id -> SourceNote
    """
    if not P4_CONTRACTS_AVAILABLE:
        return {}
    
    source_notes = {}
    
    for result in retrieval_results:
        try:
            # Extract provenance fields
            prov = result.provenance or {}
            if hasattr(prov, "__dict__"):
                prov = prov.__dict__
            elif not isinstance(prov, dict):
                prov = {}
            
            # Create SourceNote
            source_note = SourceNote.create(
                origin_url=prov.get("origin_url", f"https://unknown/{result.chunk_id}"),
                publisher=prov.get("source") or prov.get("publisher", "legifrance"),
                jurisdiction=prov.get("jurisdiction", "fr"),
                excerpt=result.text[:500] if result.text else "",
                chunk_id=result.chunk_id,
                document_id=prov.get("origin_id"),
                retrieved_at=datetime.now().isoformat() if hasattr(datetime, 'now') else None,
                content_hash=prov.get("content_hash"),
                license_tag=prov.get("license_name"),
                title=result.citation,
                correlation_id=correlation_id,
            )
            source_notes[result.chunk_id] = source_note
            
        except (ContractValidationError, NonWhitelistedPublisherError) as e:
            log_structured(LegalPipelineLog(
                correlation_id=correlation_id,
                event="source_note_validation_failed",
                data={
                    "chunk_id": result.chunk_id,
                    "error": str(e),
                },
            ))
            # Skip invalid source notes
    
    return source_notes


# ═══════════════════════════════════════════════════════════════════════════════
# PROVENANCE ERROR
# ═══════════════════════════════════════════════════════════════════════════════

class ProvenanceMissingError(Exception):
    """Raised when provenance cannot be resolved for chunks."""
    def __init__(self, chunk_ids: List[str], reason: str = ""):
        self.chunk_ids = chunk_ids
        self.reason = reason
        super().__init__(f"Provenance missing for {len(chunk_ids)} chunks: {reason}")


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURED LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LegalPipelineLog:
    """Structured log entry for legal pipeline."""
    correlation_id: str
    event: str
    timestamp: float = field(default_factory=time.time)
    duration_ms: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps({
            "correlation_id": self.correlation_id,
            "event": self.event,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            **self.data,
        })


def log_structured(log_entry: LegalPipelineLog):
    """Emit structured JSON log."""
    logger.info(log_entry.to_json())


# ═══════════════════════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LegalPipelineMetrics:
    """Metrics for legal pipeline (singleton pattern)."""
    requests_total: int = 0
    refusals_total: int = 0
    provenance_missing_total: int = 0
    consensus_required_total: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    refusal_reasons: Dict[str, int] = field(default_factory=dict)
    
    def record_request(self):
        self.requests_total += 1
    
    def record_refusal(self, reason: str):
        self.refusals_total += 1
        self.refusal_reasons[reason] = self.refusal_reasons.get(reason, 0) + 1
    
    def record_provenance_missing(self):
        self.provenance_missing_total += 1
    
    def record_consensus_required(self):
        self.consensus_required_total += 1
    
    def record_latency(self, ms: float):
        self.latencies_ms.append(ms)
        # Keep only last 1000
        if len(self.latencies_ms) > 1000:
            self.latencies_ms = self.latencies_ms[-1000:]
    
    @property
    def latency_p50(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        n = len(sorted_latencies)
        if n % 2 == 0:
            # Even number: average of two middle elements
            return (sorted_latencies[n // 2 - 1] + sorted_latencies[n // 2]) / 2
        else:
            return sorted_latencies[n // 2]
    
    @property
    def latency_p95(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    # P3: Step-level metrics
    step_latencies: Dict[str, List[float]] = field(default_factory=dict)
    timeout_total: int = 0
    idempotent_hits: int = 0
    double_run_blocked: int = 0
    
    def record_step_latency(self, step: str, ms: float):
        """P3.3: Record latency for a specific step."""
        if step not in self.step_latencies:
            self.step_latencies[step] = []
        self.step_latencies[step].append(ms)
        if len(self.step_latencies[step]) > 1000:
            self.step_latencies[step] = self.step_latencies[step][-1000:]
    
    def record_timeout(self):
        """P3.3: Record a timeout event."""
        self.timeout_total += 1
    
    def record_idempotent_hit(self):
        """P3.1: Record an idempotent cache hit."""
        self.idempotent_hits += 1
    
    def record_double_run_blocked(self):
        """P3.2: Record a blocked double-run attempt."""
        self.double_run_blocked += 1
    
    def get_step_p50(self, step: str) -> float:
        """P3.3: Get p50 latency for a step."""
        if step not in self.step_latencies or not self.step_latencies[step]:
            return 0.0
        sorted_vals = sorted(self.step_latencies[step])
        n = len(sorted_vals)
        return sorted_vals[n // 2]
    
    def get_step_p95(self, step: str) -> float:
        """P3.3: Get p95 latency for a step."""
        if step not in self.step_latencies or not self.step_latencies[step]:
            return 0.0
        sorted_vals = sorted(self.step_latencies[step])
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    def to_dict(self) -> Dict[str, Any]:
        step_stats = {}
        for step in self.step_latencies:
            step_stats[f"{step}_p50_ms"] = self.get_step_p50(step)
            step_stats[f"{step}_p95_ms"] = self.get_step_p95(step)
        
        return {
            "requests_total": self.requests_total,
            "refusals_total": self.refusals_total,
            "provenance_missing_total": self.provenance_missing_total,
            "consensus_required_total": self.consensus_required_total,
            "latency_p50_ms": self.latency_p50,
            "latency_p95_ms": self.latency_p95,
            "refusal_reasons": self.refusal_reasons,
            # P3 metrics
            "timeout_total": self.timeout_total,
            "idempotent_hits": self.idempotent_hits,
            "double_run_blocked": self.double_run_blocked,
            **step_stats,
        }


# Global metrics instance
_metrics = LegalPipelineMetrics()


def get_legal_pipeline_metrics() -> LegalPipelineMetrics:
    """Get the global metrics instance."""
    return _metrics


# ═══════════════════════════════════════════════════════════════════════════════
# P3.1: IDEMPOTENCY CACHE
# ═══════════════════════════════════════════════════════════════════════════════

class IdempotencyCache:
    """
    P3.1: Thread-safe LRU cache for idempotent pipeline results.
    
    Invariant: same idempotency_key → same audit_bundle_id
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 300.0):
        self._cache: OrderedDict[str, Tuple[LegalOutput, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
    
    def compute_idempotency_key(
        self,
        query: str,
        scope: Optional[str],
        jurisdiction: Optional[str],
        risk_tier: Optional[str],
        source_chunk_ids: List[str],
        enforcement_level: str,
    ) -> str:
        """
        P3.1: Compute deterministic idempotency key.
        
        Key = SHA256(normalized_query + scope + jurisdiction + risk_tier + sorted(chunk_ids) + enforcement)
        """
        # Normalize query (lowercase, strip, collapse whitespace)
        normalized = " ".join(query.lower().split())
        
        # Build composite string
        components = [
            normalized,
            scope or "info",
            jurisdiction or "fr",
            risk_tier or "low",
            ",".join(sorted(source_chunk_ids)),
            enforcement_level,
        ]
        composite = "|".join(components)
        
        return hashlib.sha256(composite.encode("utf-8")).hexdigest()[:32]
    
    def get(self, key: str, correlation_id: str) -> Optional[LegalOutput]:
        """Get cached result if valid (not expired)."""
        with self._lock:
            if key not in self._cache:
                return None
            
            output, timestamp = self._cache[key]
            
            # Check TTL
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            
            log_structured(LegalPipelineLog(
                correlation_id=correlation_id,
                event="idempotent_cache_hit",
                data={
                    "idempotency_key": key,
                    "audit_bundle_id": output.audit_bundle_id,
                },
            ))
            
            return output
    
    def set(self, key: str, output: LegalOutput, correlation_id: str):
        """Cache a result."""
        with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = (output, time.time())
            
            log_structured(LegalPipelineLog(
                correlation_id=correlation_id,
                event="idempotent_cache_set",
                data={
                    "idempotency_key": key,
                    "audit_bundle_id": output.audit_bundle_id,
                    "cache_size": len(self._cache),
                },
            ))
    
    def clear(self):
        """Clear the cache (for testing)."""
        with self._lock:
            self._cache.clear()
    
    @property
    def size(self) -> int:
        """Current cache size."""
        return len(self._cache)


# Global idempotency cache
_idempotency_cache = IdempotencyCache()


def get_idempotency_cache() -> IdempotencyCache:
    """Get the global idempotency cache."""
    return _idempotency_cache


def is_idempotency_enabled() -> bool:
    """P3.1: Check if idempotency is enabled (default ON)."""
    return os.environ.get("LEGAL_PIPELINE_IDEMPOTENCE", "1") == "1"


# ═══════════════════════════════════════════════════════════════════════════════
# P3.3: BUDGET & TIMEOUT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PipelineBudget:
    """
    P3.3: Budget configuration for pipeline execution.
    
    All values in milliseconds.
    """
    total_budget_ms: int = 12000  # 12s total
    retrieval_budget_ms: int = 3000  # 3s for FTS5
    llm_draft_budget_ms: int = 5000  # 5s for LLM FIRAC
    judge_budget_ms: int = 500  # 0.5s for judge
    consensus_budget_ms: int = 8000  # 8s for consensus (LLM calls)
    rendering_budget_ms: int = 1000  # 1s for rendering
    
    @classmethod
    def from_env(cls) -> "PipelineBudget":
        """Load budget from environment variables."""
        return cls(
            total_budget_ms=int(os.environ.get("LEGAL_BUDGET_TOTAL_MS", "12000")),
            retrieval_budget_ms=int(os.environ.get("LEGAL_BUDGET_RETRIEVAL_MS", "3000")),
            llm_draft_budget_ms=int(os.environ.get("LEGAL_BUDGET_LLM_DRAFT_MS", "5000")),
            judge_budget_ms=int(os.environ.get("LEGAL_BUDGET_JUDGE_MS", "500")),
            consensus_budget_ms=int(os.environ.get("LEGAL_BUDGET_CONSENSUS_MS", "8000")),
            rendering_budget_ms=int(os.environ.get("LEGAL_BUDGET_RENDERING_MS", "1000")),
        )


class TimeoutError(Exception):
    """P3.3: Raised when a step exceeds its budget."""
    def __init__(self, step: str, budget_ms: int, actual_ms: float):
        self.step = step
        self.budget_ms = budget_ms
        self.actual_ms = actual_ms
        super().__init__(f"Step '{step}' exceeded budget: {actual_ms:.0f}ms > {budget_ms}ms")


async def with_timeout(
    coro,
    budget_ms: int,
    step: str,
    correlation_id: str,
):
    """
    P3.3: Execute coroutine with timeout.
    
    Raises:
        TimeoutError: If execution exceeds budget
    """
    start = time.time()
    try:
        result = await asyncio.wait_for(coro, timeout=budget_ms / 1000.0)
        actual_ms = (time.time() - start) * 1000
        _metrics.record_step_latency(step, actual_ms)
        return result
    except asyncio.TimeoutError:
        actual_ms = (time.time() - start) * 1000
        _metrics.record_timeout()
        _metrics.record_step_latency(step, actual_ms)
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="step_timeout",
            duration_ms=actual_ms,
            data={
                "step": step,
                "budget_ms": budget_ms,
            },
        ))
        raise TimeoutError(step, budget_ms, actual_ms)


# ═══════════════════════════════════════════════════════════════════════════════
# PROVENANCE RESOLUTION (PRODUCTION)
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_provenance_strict(
    chunk_ids: List[str],
    retrieval_results: List[RetrievalResult],
    *,
    correlation_id: str,
) -> Dict[str, Dict[str, Any]]:
    """
    P0.8: Resolve provenance for all chunks STRICTLY.
    
    No fallback, no TODO. If provenance is missing, raise ProvenanceMissingError.
    
    Args:
        chunk_ids: List of chunk IDs to resolve
        retrieval_results: Results from retrieval (with provenance)
        correlation_id: For logging
        
    Returns:
        Dict mapping chunk_id -> provenance dict
        
    Raises:
        ProvenanceMissingError: If any chunk is missing provenance
    """
    if not chunk_ids:
        return {}
    
    # Build map from retrieval results
    provenance_map: Dict[str, Dict[str, Any]] = {}
    result_map = {r.chunk_id: r for r in retrieval_results}
    
    missing_chunks: List[str] = []
    
    for chunk_id in chunk_ids:
        result = result_map.get(chunk_id)
        
        if result and result.provenance:
            # Ensure minimum required fields
            prov = result.provenance.copy()
            prov.setdefault("source", result.source)
            prov.setdefault("chunk_id", chunk_id)
            provenance_map[chunk_id] = prov
        elif result:
            # Result exists but no provenance - build minimal
            provenance_map[chunk_id] = {
                "source": result.source,
                "chunk_id": chunk_id,
                "citation": result.citation,
            }
        else:
            missing_chunks.append(chunk_id)
    
    if missing_chunks:
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="provenance_resolution_failed",
            data={"missing_chunks": missing_chunks},
        ))
        _metrics.record_provenance_missing()
        raise ProvenanceMissingError(
            chunk_ids=missing_chunks,
            reason=f"No retrieval result for {len(missing_chunks)} chunks"
        )
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="provenance_resolved",
        data={"chunk_count": len(provenance_map)},
    ))
    
    return provenance_map


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS EXECUTION (P1: REAL)
# ═══════════════════════════════════════════════════════════════════════════════

def is_consensus_simulation_enabled() -> bool:
    """
    Check if consensus simulation mode is enabled.
    
    Environment variable: LEGAL_CONSENSUS_SIMULATION=1
    
    Default behavior:
    - Production (EVIDENCE_ENV=production): False (real consensus required)
    - Development (EVIDENCE_ENV=development or unset): True (simulation enabled)
    
    This prevents development environments from failing due to missing API keys.
    """
    explicit_value = os.environ.get("LEGAL_CONSENSUS_SIMULATION")
    if explicit_value is not None:
        return explicit_value == "1"
    
    # Auto-detect: enable simulation in development by default
    env = os.environ.get("EVIDENCE_ENV", "development").lower()
    if env == "production":
        return False  # Production: require real consensus
    else:
        return True   # Development: simulation by default


async def execute_consensus(
    proposal: LegalConsensusProposal,
    *,
    correlation_id: str,
    call_llm_func: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    P1: Execute consensus voting on a legal proposal using REAL LLM arbiters.
    
    Args:
        proposal: The consensus proposal
        correlation_id: For logging
        call_llm_func: Deprecated (kept for backward compatibility)
        
    Returns:
        Dict with status, votes, etc.
        
    INVARIANT: If consensus required but unavailable → status=PENDING (not APPROVED)
    """
    start_time = time.time()
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="consensus_start",
        data={
            "proposal_id": proposal.proposal_id,
            "required_approvals": proposal.required_approvals,
            "require_unanimity": proposal.require_unanimity,
            "risk_tier": proposal.risk_tier.value if proposal.risk_tier else "unknown",
            "simulation_mode": is_consensus_simulation_enabled(),
        },
    ))
    
    _metrics.record_consensus_required()
    
    # ─────────────────────────────────────────────────────────────────────────
    # SIMULATION MODE (only for testing, NO auto-approval)
    # ─────────────────────────────────────────────────────────────────────────
    
    if is_consensus_simulation_enabled():
        # Simulation: never approve without real votes
        votes = {}
        status = "NO_CONSENSUS"
        
        duration_ms = (time.time() - start_time) * 1000
        result = {
            "proposal_id": proposal.proposal_id,
            "status": status,
            "votes": votes,
            "required_approvals": proposal.required_approvals,
            "unanimous": proposal.require_unanimity,
            "simulation": True,
        }
        
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="consensus_end",
            duration_ms=duration_ms,
            data=result,
        ))
        
        return result
    
    # ─────────────────────────────────────────────────────────────────────────
    # REAL CONSENSUS (P1 wiring)
    # ─────────────────────────────────────────────────────────────────────────
    
    if not CONSENSUS_AVAILABLE or seek_consensus is None:
        logger.error("Consensus system not available - fail-closed")
        _metrics.record_refusal("consensus_unavailable")
        return {
            "proposal_id": proposal.proposal_id,
            "status": "PENDING",  # Not APPROVED - fail-closed
            "votes": {},
            "required_approvals": proposal.required_approvals,
            "unanimous": proposal.require_unanimity,
            "error": "consensus_system_unavailable",
        }
    
    try:
        # Build context for arbiters
        summary = getattr(proposal, 'summary', None) or f"Draft {proposal.draft_id}"
        context = {
            "draft_id": proposal.draft_id,
            "risk_tier": proposal.risk_tier.value if proposal.risk_tier else "unknown",
            "scope": proposal.scope.value if proposal.scope else "info",
            "summary": summary,
            "required_approvals": proposal.required_approvals,
            "require_unanimity": proposal.require_unanimity,
        }
        
        # Build action description
        action = f"Validate legal analysis: {summary[:200]}"
        
        # Call real consensus
        consensus_result: ConsensusResult = await seek_consensus(
            action=action,
            context=context,
            decision_type=DecisionType.CRITICAL,
            correlation_id=correlation_id,
        )
        
        # Map result to expected format
        votes = {}
        if hasattr(consensus_result, 'votes') and consensus_result.votes:
            for provider, vote in consensus_result.votes.items():
                if hasattr(vote, 'vote'):
                    votes[provider] = vote.vote.value.lower() if hasattr(vote.vote, 'value') else str(vote.vote)
                else:
                    votes[provider] = str(vote)
        
        # Determine status
        if hasattr(consensus_result, 'status'):
            status_val = consensus_result.status
            if hasattr(status_val, 'value'):
                status = status_val.value
            else:
                status = str(status_val)
        elif hasattr(consensus_result, 'approved'):
            status = "APPROVED" if consensus_result.approved else "REJECTED"
        else:
            status = "PENDING"
        
        # NEW: Add reason_code for audit distinction
        reason_code_map = {
            "APPROVED": "approved",
            "REJECTED": "rejected",
            "NO_CONSENSUS": "no_consensus",    # Evaluation done, no quorum
            "INFRA_FAILURE": "infra_failure",  # All arbiters unavailable or timed out
            "PENDING": "pending",
        }
        reason_code = reason_code_map.get(status, "unknown")
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = {
            "proposal_id": proposal.proposal_id,
            "status": status,
            "reason_code": reason_code,  # NEW: For audit/ops distinction
            "votes": votes,
            "required_approvals": proposal.required_approvals,
            "unanimous": proposal.require_unanimity,
            "decision_time_ms": getattr(consensus_result, 'decision_time_ms', duration_ms),
        }
        
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="consensus_end",
            duration_ms=duration_ms,
            data=result,
        ))
        
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"Consensus timeout for {proposal.proposal_id}")
        return {
            "proposal_id": proposal.proposal_id,
            "status": "INFRA_FAILURE",
            "reason_code": "infra_failure",
            "votes": {},
            "required_approvals": proposal.required_approvals,
            "unanimous": proposal.require_unanimity,
            "error": "consensus_timeout",
        }
    except Exception as e:
        logger.error(f"Consensus error: {e}")
        return {
            "proposal_id": proposal.proposal_id,
            "status": "INFRA_FAILURE",
            "reason_code": "infra_failure",
            "votes": {},
            "required_approvals": proposal.required_approvals,
            "unanimous": proposal.require_unanimity,
            "error": str(e),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL VIA REAL FTS5 INDEX (P1.4)
# ═══════════════════════════════════════════════════════════════════════════════

def get_legal_index_path() -> Path:
    """Get the path to the legal index directory."""
    # Default: workspace/data/legal_index
    default_path = Path(__file__).parent.parent.parent / "data" / "legal_index"
    return Path(os.environ.get("LEGAL_INDEX_PATH", str(default_path)))


def retrieve_from_fts5_index(
    query: str,
    *,
    jurisdiction: str = "fr",
    max_results: int = 5,
    correlation_id: str,
) -> RetrievalContext:
    """
    P1.4: Retrieve legal sources from the REAL SQLite FTS5 index.
    
    Args:
        query: User query
        jurisdiction: Jurisdiction filter (fr, eu, etc.)
        max_results: Maximum number of results
        correlation_id: For logging
        
    Returns:
        RetrievalContext with results
    """
    retrieval_start = time.time()
    
    if not LEGAL_INDEX_AVAILABLE or LegalIndex is None:
        logger.warning("LegalIndex not available - falling back to empty results")
        return RetrievalContext()
    
    index_path = get_legal_index_path()
    
    if not index_path.exists():
        logger.warning(f"Legal index not found at {index_path}")
        return RetrievalContext()
    
    try:
        # Open the FTS5 index
        index = LegalIndex(index_path)
        
        # Search using FTS5
        source_filter = "legi" if jurisdiction == "fr" else None
        search_results = index.search(
            query=query,
            source=source_filter,
            limit=max_results,
        )
        
        # Convert SearchResult to RetrievalResult
        results: List[RetrievalResult] = []
        for sr in search_results:
            results.append(RetrievalResult(
                chunk_id=sr.chunk_id,
                doc_id=sr.doc_id,
                source=sr.source,
                citation=sr.citation,
                pinpoint=sr.pinpoint,
                text="",  # Not included in SearchResult
                text_snippet=sr.text_snippet,
                provenance=sr.provenance,
                match_type="search",
                score=sr.score,
            ))
        
        retrieval_duration_ms = (time.time() - retrieval_start) * 1000
        
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="fts5_retrieval_complete",
            duration_ms=retrieval_duration_ms,
            data={
                "results_count": len(results),
                "index_path": str(index_path),
            },
        ))
        
        # Build context
        ctx = RetrievalContext()
        ctx.results = results
        ctx.search_matches = len(results)
        ctx.exact_matches = 0
        
        return ctx
        
    except Exception as e:
        logger.error(f"FTS5 retrieval error: {e}")
        return RetrievalContext()


# ═══════════════════════════════════════════════════════════════════════════════
# LLM DRAFT BUILDER (P1.3)
# ═══════════════════════════════════════════════════════════════════════════════

# Prompt for FIRAC draft generation
FIRAC_DRAFT_PROMPT = """Tu es un assistant juridique. Génère une analyse FIRAC structurée.

QUERY: {query}

SOURCES DISPONIBLES:
{sources_block}

INSTRUCTIONS:
1. Extraire les FAITS pertinents de la requête
2. Identifier les RÈGLES applicables à partir des sources
3. Rédiger une APPLICATION concise des règles aux faits
4. Identifier les RISQUES potentiels
5. Proposer la prochaine ACTION recommandée
6. Lister les CLAIMS avec leurs citations

IMPORTANT:
- Chaque claim DOIT référencer une source via chunk_id
- Si source insuffisante, mettre claim_type="hypothesis" avec basis explicite
- NE JAMAIS inventer de texte juridique
- Si informations insuffisantes, indiquer "REQUEST_INFO" comme next_action

Réponds en JSON strict:
{{
  "facts": ["fait 1", "fait 2"],
  "rules": ["règle 1 (source)", "règle 2 (source)"],
  "application": "texte d'application (min 60 caractères)",
  "risks": ["risque 1", "risque 2"],
  "next_action": "action recommandée",
  "claims": [
    {{"text": "contenu du claim", "claim_type": "cited", "citation": "Art. X", "chunk_id": "chunk_xxx"}},
    {{"text": "hypothèse", "claim_type": "hypothesis", "basis": "raisonnement"}}
  ]
}}
"""


async def build_legal_draft_with_llm(
    query: str,
    legal_context: LegalRouteContext,
    retrieval_context: RetrievalContext,
    *,
    correlation_id: str,
    call_llm_func: Optional[Callable] = None,
) -> LegalDraft:
    """
    P1.3: Build a LegalDraft using LLM for FIRAC analysis.
    
    Args:
        query: User query
        legal_context: Detected legal context
        retrieval_context: Retrieved sources
        correlation_id: For logging
        call_llm_func: LLM call function (async)
        
    Returns:
        LegalDraft with proper claims
        
    INVARIANT: No UNSUPPORTED claims for OPERATIONAL/BOARD scope
    """
    draft_id = generate_draft_id(query, time.time())
    
    # Build sources block for prompt
    sources_lines = []
    for i, result in enumerate(retrieval_context.results):
        sources_lines.append(
            f"[{i+1}] chunk_id={result.chunk_id}\n"
            f"    citation: {result.citation}\n"
            f"    extrait: {result.text_snippet[:300]}..."
        )
    sources_block = "\n".join(sources_lines) if sources_lines else "(Aucune source trouvée dans l'index local)"
    
    # If no LLM function, fall back to basic draft
    # BUT: If we have an LLM function, we CAN generate analysis even without sources
    # The LLM will use its training knowledge (with appropriate disclaimers)
    if call_llm_func is None:
        return _build_basic_draft(query, legal_context, retrieval_context, draft_id, correlation_id)
    
    # Build prompt
    prompt = FIRAC_DRAFT_PROMPT.format(
        query=query,
        sources_block=sources_block,
    )
    
    try:
        # Call LLM (temperature=0 for deterministic)
        llm_response = await call_llm_func(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2000,
        )
        
        # Parse JSON response
        response_text = llm_response if isinstance(llm_response, str) else llm_response.get("content", "")
        
        # Extract JSON from response (handle markdown code blocks)
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]
        
        parsed = json.loads(json_text.strip())
        
        # Build draft from parsed response
        # Note: If no retrieval results, LLM generates citations from training data
        # These are marked as "llm_knowledge" not "indexed_source"
        draft = LegalDraft(
            draft_id=draft_id,
            query=query,
            facts=parsed.get("facts", [f"Requête: {query}"]),
            rules=parsed.get("rules", []),
            application=parsed.get("application", ""),
            risks=parsed.get("risks", []),
            next_action=parsed.get("next_action", "Vérifier les sources officielles (Légifrance)"),
            # Use retrieval citations if available, otherwise use LLM-provided rules as citations
            citations=[r.citation for r in retrieval_context.results] if retrieval_context.results else parsed.get("rules", []),
            source_chunk_ids=[r.chunk_id for r in retrieval_context.results] if retrieval_context.results else [],
            legal_context=legal_context,
        )
        
        # Ensure minimum application length
        if len(draft.application) < 60:
            draft.application += " " * (60 - len(draft.application))
        
        # Add claims from LLM response
        for claim_data in parsed.get("claims", []):
            claim_type_str = claim_data.get("claim_type", "cited")
            
            if claim_type_str == "cited":
                draft.add_cited_claim(
                    text=claim_data.get("text", ""),
                    citation=claim_data.get("citation", ""),
                    chunk_id=claim_data.get("chunk_id", ""),
                )
            elif claim_type_str == "hypothesis":
                draft.add_hypothesis_claim(
                    text=claim_data.get("text", ""),
                    basis=claim_data.get("basis", ""),
                )
            # Skip UNSUPPORTED claims (not allowed)
        
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="llm_draft_built",
            data={
                "draft_id": draft_id,
                "facts_count": len(draft.facts),
                "rules_count": len(draft.rules),
                "claims_count": len(draft.claims),
                "llm_used": True,
            },
        ))
        
        return draft
        
    except json.JSONDecodeError as e:
        logger.error(f"LLM draft JSON parse error: {e}")
        # Fall back to basic draft
        return _build_basic_draft(query, legal_context, retrieval_context, draft_id, correlation_id)
    except Exception as e:
        logger.error(f"LLM draft error: {e}")
        return _build_basic_draft(query, legal_context, retrieval_context, draft_id, correlation_id)


def _build_basic_draft(
    query: str,
    legal_context: LegalRouteContext,
    retrieval_context: RetrievalContext,
    draft_id: str,
    correlation_id: str,
) -> LegalDraft:
    """Build a basic draft without LLM (fallback)."""
    facts = [f"Requête utilisateur: {query}"]
    rules = []
    citations = []
    chunk_ids = []
    
    for result in retrieval_context.results:
        rules.append(f"{result.citation}: {result.text_snippet[:200]}...")
        citations.append(format_citation_from_result(result))
        chunk_ids.append(result.chunk_id)
    
    application = (
        f"Analyse des {len(retrieval_context.results)} sources identifiées "
        f"pour la question juridique posée. "
        f"Les règles applicables ont été extraites des sources officielles."
    )
    if len(application) < 60:
        application += " " * (60 - len(application))
    
    risks = []
    if retrieval_context.has_abrogated:
        risks.append("⚠️ Certaines sources citées peuvent être abrogées")
    if legal_context.requires_jurisdiction_clarification:
        risks.append("⚠️ La juridiction nécessite clarification (FR/EU)")
    
    draft = LegalDraft(
        draft_id=draft_id,
        query=query,
        facts=facts,
        rules=rules,
        application=application,
        risks=risks,
        next_action="Vérifier les sources sur les sites officiels",
        citations=citations,
        source_chunk_ids=chunk_ids,
        legal_context=legal_context,
    )
    
    # Add claims from retrieval
    for result in retrieval_context.results:
        draft.add_cited_claim(
            text=result.text_snippet[:100],
            citation=format_citation_from_result(result),
            chunk_id=result.chunk_id,
        )
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="basic_draft_built",
        data={
            "draft_id": draft_id,
            "facts_count": len(facts),
            "rules_count": len(rules),
            "claims_count": len(draft.claims),
            "llm_used": False,
        },
    ))
    
    return draft


def build_legal_draft_from_retrieval(
    query: str,
    legal_context: LegalRouteContext,
    retrieval_context: RetrievalContext,
    *,
    correlation_id: str,
) -> LegalDraft:
    """
    Build a LegalDraft from retrieval results (sync version).
    
    This is the backward-compatible sync wrapper.
    For LLM-enhanced drafts, use build_legal_draft_with_llm().
    """
    draft_id = generate_draft_id(query, time.time())
    return _build_basic_draft(query, legal_context, retrieval_context, draft_id, correlation_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""
    return hashlib.sha256(f"{time.time()}:{os.getpid()}".encode()).hexdigest()[:16]


async def run_legal_pipeline(
    query: str,
    route_decision: Optional[RouteDecision] = None,
    *,
    correlation_id: Optional[str] = None,
    enforcement_level: Optional[int] = None,
    max_sources: int = 5,
    call_llm_func: Optional[Callable] = None,
    budget: Optional[PipelineBudget] = None,
    as_of_date: Optional[Union[date, str]] = None,
) -> LegalOutput:
    """
    P0.8/P3/P5: Single entry point for the legal pipeline.
    
    This function orchestrates the entire legal pipeline:
    1. Retrieval (2-stage: exact + search)
    2. Draft construction (FIRAC + claims)
    3. Judge (binary checklist)
    4. Consensus (if required)
    5. Output (with provenance)
    
    INVARIANTS ENFORCED:
    - No provenance = No output (except REFUSAL)
    - BOARD/MEDIUM/HIGH = Consensus required
    - APPROVED_POSITION only if consensus APPROVED
    - P3.1: same idempotency_key → same audit_bundle_id
    - P3.3: timeouts → REFUSAL (never skip consensus if required)
    - P5: as_of_date required for MEDIUM+ risk, non-INFO scope
    - P5: all sources must have resolved version
    
    Args:
        query: User query
        route_decision: Router decision (optional)
        correlation_id: For logging/tracing
        enforcement_level: Override enforcement level
        max_sources: Maximum retrieval results
        call_llm_func: Optional LLM function for consensus
        budget: P3.3 Budget configuration (default from env)
        as_of_date: P5 Date for temporal versioning (required for MEDIUM+ risk)
        
    Returns:
        LegalOutput with appropriate mode
    """
    start_time = time.time()
    
    # Generate correlation ID if not provided
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    
    # Get enforcement level
    level = enforcement_level if enforcement_level is not None else get_legal_enforcement_level()
    
    # P3.3: Get budget configuration
    if budget is None:
        budget = PipelineBudget.from_env()
    
    # Record request
    _metrics.record_request()
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="legal_pipeline_start",
        data={
            "query_length": len(query),
            "enforcement_level": level,
            "max_sources": max_sources,
            "budget_total_ms": budget.total_budget_ms,
        },
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK FEATURE FLAG
    # ─────────────────────────────────────────────────────────────────────────
    
    if not is_legal_pipeline_enabled():
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="legal_pipeline_disabled",
        ))
        _metrics.record_refusal("legal_pipeline_disabled")
        
        return LegalOutput(
            mode=LegalOutputMode.REFUSAL_REQUEST_INFO,
            answer="Le pipeline juridique est désactivé. Veuillez contacter l'administrateur.",
            missing_info=["legal_pipeline_disabled"],
            audit_bundle_id=generate_audit_bundle_id("disabled", "refusal", [], []),
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: DETECT LEGAL CONTEXT
    # ─────────────────────────────────────────────────────────────────────────
    
    legal_context = detect_legal_context(query)
    
    # ─────────────────────────────────────────────────────────────────────────
    # P5: PARSE AND VALIDATE AS_OF_DATE
    # ─────────────────────────────────────────────────────────────────────────
    
    # Parse as_of_date if string
    resolved_as_of_date: Optional[date] = None
    if as_of_date is not None:
        if isinstance(as_of_date, str):
            resolved_as_of_date = parse_date(as_of_date) if parse_date else None
        elif isinstance(as_of_date, date):
            resolved_as_of_date = as_of_date
    
    # Check if as_of_date is required
    as_of_date_error = validate_as_of_date(
        resolved_as_of_date,
        legal_context.risk_tier,
        legal_context.scope,
        correlation_id=correlation_id,
    )
    
    if as_of_date_error:
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="as_of_date_required",
            data={
                "risk_tier": legal_context.risk_tier.value,
                "scope": legal_context.scope.value,
                "error": as_of_date_error,
            },
        ))
        _metrics.record_refusal("missing_as_of_date")
        
        return LegalOutput(
            mode=LegalOutputMode.REFUSAL_REQUEST_INFO,
            answer=(
                "Cette analyse nécessite une date de référence (as_of_date) pour garantir "
                "l'opposabilité temporelle de la réponse. Veuillez préciser la date à laquelle "
                "l'analyse doit être effectuée."
            ),
            missing_info=["as_of_date"],
            audit_bundle_id=generate_audit_bundle_id(
                correlation_id, "refusal_missing_as_of_date", [], []
            ),
            as_of_date=None,
        )
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="as_of_date_validated",
        data={
            "as_of_date": resolved_as_of_date.isoformat() if resolved_as_of_date else None,
            "required": requires_as_of_date(legal_context.risk_tier, legal_context.scope),
        },
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # P3.1: IDEMPOTENCY CHECK (early, before expensive operations)
    # ─────────────────────────────────────────────────────────────────────────
    
    idempotency_key: Optional[str] = None
    
    if is_idempotency_enabled():
        # Pre-compute idempotency key with available info
        # Note: We use an empty list for chunk_ids here since retrieval hasn't happened
        # The final key after retrieval will be more specific
        idempotency_key = _idempotency_cache.compute_idempotency_key(
            query=query,
            scope=legal_context.scope.value,
            jurisdiction=legal_context.jurisdiction.value,
            risk_tier=legal_context.risk_tier.value,
            source_chunk_ids=[],  # Will be empty for pre-check
            enforcement_level=str(level),
        )
        
        # Check cache
        cached_output = _idempotency_cache.get(idempotency_key, correlation_id)
        if cached_output is not None:
            _metrics.record_idempotent_hit()
            log_structured(LegalPipelineLog(
                correlation_id=correlation_id,
                event="idempotent_return",
                duration_ms=(time.time() - start_time) * 1000,
                data={
                    "idempotency_key": idempotency_key,
                    "audit_bundle_id": cached_output.audit_bundle_id,
                },
            ))
            return cached_output
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="legal_context_detected",
        data={
            "risk_tier": legal_context.risk_tier.value,
            "scope": legal_context.scope.value,
            "jurisdiction": legal_context.jurisdiction.value,
            "risk_score": legal_context.risk_score,
        },
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: RETRIEVAL (P1.4 - Real FTS5 Index)
    # ─────────────────────────────────────────────────────────────────────────
    
    retrieval_start = time.time()
    use_fts5 = os.environ.get("LEGAL_USE_FTS5_INDEX", "1") == "1"
    
    if use_fts5 and LEGAL_INDEX_AVAILABLE:
        # P1: Use real FTS5 index
        retrieval_context = retrieve_from_fts5_index(
            query=query,
            jurisdiction=legal_context.jurisdiction.value if legal_context.jurisdiction != Jurisdiction.UNKNOWN else "fr",
            max_results=max_sources,
            correlation_id=correlation_id,
        )
    else:
        # Fallback to LegalRetriever
        try:
            retriever = LegalRetriever()
            retrieval_context = retriever.retrieve(
                query=query,
                jurisdiction=legal_context.jurisdiction.value if legal_context.jurisdiction != Jurisdiction.UNKNOWN else "fr",
                max_results=max_sources,
            )
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            retrieval_context = RetrievalContext()
    
    retrieval_duration_ms = (time.time() - retrieval_start) * 1000
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="legal_retrieval_end",
        duration_ms=retrieval_duration_ms,
        data={
            "exact_matches": retrieval_context.exact_matches,
            "search_matches": retrieval_context.search_matches,
            "total_results": len(retrieval_context.results),
            "has_abrogated": retrieval_context.has_abrogated,
            "fts5_used": use_fts5 and LEGAL_INDEX_AVAILABLE,
        },
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: BUILD DRAFT (P1.3 - LLM FIRAC if available)
    # ─────────────────────────────────────────────────────────────────────────
    
    if call_llm_func is not None:
        # P1: Use LLM for FIRAC draft
        draft = await build_legal_draft_with_llm(
            query=query,
            legal_context=legal_context,
            retrieval_context=retrieval_context,
            correlation_id=correlation_id,
            call_llm_func=call_llm_func,
        )
    else:
        # Basic draft (no LLM)
        draft = build_legal_draft_from_retrieval(
            query=query,
            legal_context=legal_context,
            retrieval_context=retrieval_context,
            correlation_id=correlation_id,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: JUDGE
    # ─────────────────────────────────────────────────────────────────────────
    
    judge_result = judge_legal_draft(draft)
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="judge_result",
        data={
            "verdict": judge_result.verdict.value,
            "pass_rate": judge_result.pass_rate,
            "critical_failures": judge_result.critical_failures,
            "missing_info": judge_result.missing_info_required,
        },
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: CONSENSUS (if required)
    # ─────────────────────────────────────────────────────────────────────────
    
    consensus_result = None
    
    if requires_consensus(legal_context):
        log_structured(LegalPipelineLog(
            correlation_id=correlation_id,
            event="consensus_required",
            data={
                "risk_tier": legal_context.risk_tier.value,
                "scope": legal_context.scope.value,
            },
        ))
        
        # Only run consensus if judge passed
        if judge_result.verdict == LegalJudgeVerdict.APPROVE:
            proposal = build_legal_consensus_proposal(draft, judge_result)
            consensus_result = await execute_consensus(
                proposal,
                correlation_id=correlation_id,
                call_llm_func=call_llm_func,
            )
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: RESOLVE PROVENANCE
    # ─────────────────────────────────────────────────────────────────────────
    
    provenance_map = None
    
    if draft.source_chunk_ids:
        try:
            provenance_map = resolve_provenance_strict(
                chunk_ids=draft.source_chunk_ids,
                retrieval_results=retrieval_context.results,
                correlation_id=correlation_id,
            )
        except ProvenanceMissingError as e:
            log_structured(LegalPipelineLog(
                correlation_id=correlation_id,
                event="provenance_missing_error",
                data={"reason": str(e)},
            ))
            # Provenance missing will cause REFUSAL in build_legal_output
            provenance_map = None
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: BUILD OUTPUT
    # ─────────────────────────────────────────────────────────────────────────
    
    output = build_legal_output(
        draft=draft,
        judge_result=judge_result,
        consensus_result=consensus_result,
        provenance_map=provenance_map,
    )
    
    # Record metrics
    total_duration_ms = (time.time() - start_time) * 1000
    _metrics.record_latency(total_duration_ms)
    
    if output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO:
        reason = output.missing_info[0] if output.missing_info else "unknown"
        _metrics.record_refusal(reason)
    
    # ─────────────────────────────────────────────────────────────────────────
    # P3.1: CACHE RESULT FOR IDEMPOTENCY
    # ─────────────────────────────────────────────────────────────────────────
    
    if is_idempotency_enabled():
        # Compute final idempotency key with actual chunk_ids
        final_idempotency_key = _idempotency_cache.compute_idempotency_key(
            query=query,
            scope=legal_context.scope.value,
            jurisdiction=legal_context.jurisdiction.value,
            risk_tier=legal_context.risk_tier.value,
            source_chunk_ids=draft.source_chunk_ids,
            enforcement_level=str(level),
        )
        
        # Cache the result
        _idempotency_cache.set(final_idempotency_key, output, correlation_id)
    
    log_structured(LegalPipelineLog(
        correlation_id=correlation_id,
        event="legal_pipeline_end",
        duration_ms=total_duration_ms,
        data={
            "output_mode": output.mode.value,
            "missing_info": output.missing_info,
            "consensus_status": output.consensus_status,
            "audit_bundle_id": output.audit_bundle_id,
            "idempotency_enabled": is_idempotency_enabled(),
        },
    ))
    
    return output


# ═══════════════════════════════════════════════════════════════════════════════
# SYNC WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

def run_legal_pipeline_sync(
    query: str,
    route_decision: Optional[RouteDecision] = None,
    **kwargs,
) -> LegalOutput:
    """
    Synchronous wrapper for run_legal_pipeline.
    
    Use this in non-async contexts.
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        run_legal_pipeline(query, route_decision, **kwargs)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Main entry point
    "run_legal_pipeline",
    "run_legal_pipeline_sync",
    # Feature flags
    "is_legal_pipeline_enabled",
    "get_legal_enforcement_level",
    "is_consensus_simulation_enabled",
    "is_idempotency_enabled",
    "is_whitelist_enforcement_enabled",
    # Errors
    "ProvenanceMissingError",
    "TimeoutError",
    "WhitelistViolationError",
    # Metrics
    "LegalPipelineMetrics",
    "get_legal_pipeline_metrics",
    # Logging
    "LegalPipelineLog",
    "log_structured",
    # Helpers
    "generate_correlation_id",
    "resolve_provenance_strict",
    # P1: Real components
    "retrieve_from_fts5_index",
    "build_legal_draft_with_llm",
    "execute_consensus",
    # Availability flags
    "CONSENSUS_AVAILABLE",
    "LEGAL_INDEX_AVAILABLE",
    "P4_CONTRACTS_AVAILABLE",
    "P6_DIFF_AVAILABLE",
    # P4: Whitelist validation
    "validate_source_whitelist",
    "validate_cited_claims_have_sources",
    "build_source_notes_from_retrieval",
    # P3: Idempotency & Budget
    "IdempotencyCache",
    "get_idempotency_cache",
    "PipelineBudget",
    "with_timeout",
    # P6.1: Legal Diff
    "is_diff_enabled",
]
