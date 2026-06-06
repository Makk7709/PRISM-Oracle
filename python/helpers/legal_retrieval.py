"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         LEGAL RETRIEVAL — EVIDENCE                           ║
║                                                                              ║
║  Retrieval juridique en deux temps:                                          ║
║  1. Lookup exact si origin_id/numéro d'arrêt/identifiant article présent     ║
║  2. Sinon search lexical + rerank + top 3-5 max                              ║
║                                                                              ║
║  Filtrage strict: FR-only sauf demande explicite, abrogé/vigueur signalé     ║
║                                                                              ║
║  P5: Temporal filtering via as_of_date                                       ║
║  - Only return versions valid at as_of_date                                  ║
║  - Detect version ambiguity                                                  ║
║                                                                              ║
║  Version: 1.1.0 (P5 Versioning)                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("legal_retrieval")


# ═══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RetrievalResult:
    """
    Résultat de retrieval avec provenance complète.
    """
    chunk_id: str
    doc_id: str
    source: str
    
    # Citation formatée
    citation: str
    pinpoint: str
    
    # Contenu
    text: str
    text_snippet: str
    
    # Provenance
    provenance: Dict[str, Any] = field(default_factory=dict)
    
    # Matching info
    match_type: str = "search"  # "exact" ou "search"
    score: float = 0.0
    
    # Status
    is_abrogated: bool = False
    abrogation_date: Optional[str] = None
    
    # P5: Version info
    version_id: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    as_of_date_resolved: Optional[date] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "source": self.source,
            "citation": self.citation,
            "pinpoint": self.pinpoint,
            "text": self.text,
            "text_snippet": self.text_snippet,
            "provenance": self.provenance,
            "match_type": self.match_type,
            "score": self.score,
            "is_abrogated": self.is_abrogated,
            "abrogation_date": self.abrogation_date,
            # P5
            "version_id": self.version_id,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "as_of_date_resolved": self.as_of_date_resolved.isoformat() if self.as_of_date_resolved else None,
        }
    
    @property
    def has_resolved_version(self) -> bool:
        """P5: Check if this result has a resolved version."""
        return self.version_id is not None and self.as_of_date_resolved is not None


@dataclass
class RetrievalContext:
    """
    Contexte enrichi après retrieval.
    """
    results: List[RetrievalResult] = field(default_factory=list)
    
    # Stats
    exact_matches: int = 0
    search_matches: int = 0
    
    # Warnings
    has_abrogated: bool = False
    abrogated_citations: List[str] = field(default_factory=list)
    
    # Filters applied
    jurisdiction_filter: Optional[str] = None
    source_filter: Optional[str] = None
    
    # P5: Temporal filtering
    as_of_date: Optional[date] = None
    version_ambiguities: List[str] = field(default_factory=list)  # chunk_ids with >1 valid version
    version_not_found: List[str] = field(default_factory=list)  # chunk_ids with 0 valid versions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "exact_matches": self.exact_matches,
            "search_matches": self.search_matches,
            "has_abrogated": self.has_abrogated,
            "abrogated_citations": self.abrogated_citations,
            "jurisdiction_filter": self.jurisdiction_filter,
            "source_filter": self.source_filter,
            # P5
            "as_of_date": self.as_of_date.isoformat() if self.as_of_date else None,
            "version_ambiguities": self.version_ambiguities,
            "version_not_found": self.version_not_found,
        }
    
    @property
    def has_version_issues(self) -> bool:
        """P5: Check if there are any version resolution issues."""
        return bool(self.version_ambiguities) or bool(self.version_not_found)
    
    @property
    def all_versions_resolved(self) -> bool:
        """P5: Check if all results have resolved versions."""
        if not self.as_of_date:
            return False
        return all(r.has_resolved_version for r in self.results)


# ═══════════════════════════════════════════════════════════════════════════════
# IDENTIFIER EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern pour LEGIARTI (identifiant Légifrance)
LEGIARTI_PATTERN = re.compile(r"LEGIARTI\d{12}", re.IGNORECASE)

# Pattern pour numéro de pourvoi Cassation (ex: 19-25.123, 2019-12345)
POURVOI_PATTERN = re.compile(r"\b(\d{2}[-–]\d{2}\.\d{3}|\d{4}[-–]\d{5})\b")

# Pattern pour ECLI
ECLI_PATTERN = re.compile(r"ECLI:FR:\w+:\d{4}:\w+", re.IGNORECASE)

# Pattern pour article avec code
ARTICLE_CODE_PATTERN = re.compile(
    r"(?:art(?:icle)?\.?\s*)?([Ll]?\d{1,4}(?:[-–]\d{1,4})?(?:[-–]\d+)?)"
    r"(?:\s+(?:du\s+)?(?:code|c\.)\s+"
    r"(civil|pénal|travail|commerce|consommation|monétaire))?",
    re.IGNORECASE
)


def extract_legal_identifiers(text: str) -> Dict[str, List[str]]:
    """
    Extrait les identifiants juridiques d'un texte.
    
    Returns:
        Dict avec:
        - "legiarti": Liste d'identifiants LEGIARTI
        - "pourvoi": Liste de numéros de pourvoi
        - "ecli": Liste d'ECLI
        - "articles": Liste de tuples (article, code)
    """
    identifiers = {
        "legiarti": [],
        "pourvoi": [],
        "ecli": [],
        "articles": [],
    }
    
    # LEGIARTI
    for match in LEGIARTI_PATTERN.findall(text):
        identifiers["legiarti"].append(match.upper())
    
    # Pourvoi
    for match in POURVOI_PATTERN.findall(text):
        # Normaliser le format
        normalized = match.replace("–", "-")
        identifiers["pourvoi"].append(normalized)
    
    # ECLI
    for match in ECLI_PATTERN.findall(text):
        identifiers["ecli"].append(match.upper())
    
    # Articles
    for match in ARTICLE_CODE_PATTERN.findall(text):
        article = match[0]
        code = match[1].lower() if match[1] else None
        identifiers["articles"].append((article, code))
    
    # Deduplicate
    identifiers["legiarti"] = list(set(identifiers["legiarti"]))
    identifiers["pourvoi"] = list(set(identifiers["pourvoi"]))
    identifiers["ecli"] = list(set(identifiers["ecli"]))
    identifiers["articles"] = list(set(identifiers["articles"]))
    
    return identifiers


# ═══════════════════════════════════════════════════════════════════════════════
# LEGAL RETRIEVER
# ═══════════════════════════════════════════════════════════════════════════════

class LegalRetriever:
    """
    Retriever juridique en deux temps.
    
    1. Lookup exact d'abord si identifiants présents
    2. Sinon search lexical + rerank + top 3-5 max
    
    Filtrage:
    - FR-only sauf demande explicite
    - abrogé/vigueur signalé
    """
    
    MAX_CHUNKS = 5  # P0: max 5 chunks
    
    def __init__(self, index_dir: Optional[Path] = None):
        """
        Args:
            index_dir: Répertoire de l'index. Si None, utilise le défaut.
        """
        self.index_dir = index_dir
        self._index = None
    
    def _get_index(self):
        """Lazy loading de l'index."""
        if self._index is None:
            try:
                from python.legal_sources.indexing import LegalIndex
                
                if self.index_dir:
                    self._index = LegalIndex(self.index_dir)
                else:
                    # Default path
                    default_path = Path("data/legal/index")
                    self._index = LegalIndex(default_path)
                    
            except ImportError:
                logger.warning("legal_sources module not available")
                return None
            except Exception as e:
                logger.error(f"Failed to load legal index: {e}")
                return None
        
        return self._index
    
    def retrieve(
        self,
        query: str,
        jurisdiction: Optional[str] = "fr",
        source: Optional[str] = None,
        max_results: int = 5,
        as_of_date: Optional[date] = None,
    ) -> RetrievalContext:
        """
        Retrieve en deux temps.
        
        Args:
            query: Requête utilisateur
            jurisdiction: Filtre juridiction (fr, eu, None pour tous)
            source: Filtre source (legi, cass, etc.)
            max_results: Nombre max de résultats (défaut 5)
            as_of_date: P5 - Date for temporal filtering (return only valid versions)
            
        Returns:
            RetrievalContext avec résultats enrichis
        """
        max_results = min(max_results, self.MAX_CHUNKS)
        
        context = RetrievalContext(
            jurisdiction_filter=jurisdiction,
            source_filter=source,
            as_of_date=as_of_date,
        )
        
        index = self._get_index()
        if not index:
            logger.warning("No index available, returning empty context")
            return context
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 1: Extract identifiers for exact lookup
        # ─────────────────────────────────────────────────────────────────────
        
        identifiers = extract_legal_identifiers(query)
        
        exact_results: List[RetrievalResult] = []
        
        # Lookup LEGIARTI
        for legiarti in identifiers["legiarti"][:3]:  # Max 3
            result = self._lookup_by_origin_id(index, legiarti)
            if result:
                exact_results.extend(result)
        
        # Lookup ECLI
        for ecli in identifiers["ecli"][:2]:  # Max 2
            result = self._lookup_by_ecli(index, ecli)
            if result:
                exact_results.extend(result)
        
        # Lookup articles
        for article, code in identifiers["articles"][:3]:  # Max 3
            result = self._lookup_article(index, article, code)
            if result:
                exact_results.extend(result)
        
        context.exact_matches = len(exact_results)
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 2: Search if not enough exact results
        # ─────────────────────────────────────────────────────────────────────
        
        remaining_slots = max_results - len(exact_results)
        
        if remaining_slots > 0:
            search_results = self._search(
                index=index,
                query=query,
                source=source,
                limit=remaining_slots + 5,  # Over-fetch for rerank
            )
            
            # Rerank: prefer results with provenance
            search_results = self._rerank(search_results)
            
            # Take top N
            search_results = search_results[:remaining_slots]
            
            context.search_matches = len(search_results)
            
            # Merge results
            all_results = exact_results + search_results
        else:
            all_results = exact_results[:max_results]
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 3: Filter by jurisdiction
        # ─────────────────────────────────────────────────────────────────────
        
        if jurisdiction:
            all_results = self._filter_by_jurisdiction(all_results, jurisdiction)
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 4: Check for abrogated texts
        # ─────────────────────────────────────────────────────────────────────
        
        for result in all_results:
            if result.is_abrogated:
                context.has_abrogated = True
                context.abrogated_citations.append(result.citation)
        
        context.results = all_results[:max_results]
        
        return context
    
    def _lookup_by_origin_id(self, index, origin_id: str) -> List[RetrievalResult]:
        """Lookup exact par origin_id."""
        try:
            data = index.lookup_by_origin_id(origin_id)
            if not data:
                return []
            
            results = []
            for chunk in data.get("chunks", []):
                results.append(RetrievalResult(
                    chunk_id=chunk["chunk_id"],
                    doc_id=chunk["doc_id"],
                    source=chunk["source"],
                    citation=chunk.get("citation", ""),
                    pinpoint=chunk.get("pinpoint", ""),
                    text=chunk.get("text", ""),
                    text_snippet=chunk.get("text", "")[:200],
                    provenance=chunk.get("provenance", {}),
                    match_type="exact",
                    score=1.0,
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Lookup failed for {origin_id}: {e}")
            return []
    
    def _lookup_by_ecli(self, index, ecli: str) -> List[RetrievalResult]:
        """Lookup par ECLI (via search sur citation)."""
        # ECLI n'est pas directement indexé, on fait un search
        try:
            search_results = index.search(ecli, limit=3)
            
            results = []
            for sr in search_results:
                if ecli.lower() in sr.citation.lower():
                    results.append(RetrievalResult(
                        chunk_id=sr.chunk_id,
                        doc_id=sr.doc_id,
                        source=sr.source,
                        citation=sr.citation,
                        pinpoint=sr.pinpoint,
                        text=sr.text_snippet,
                        text_snippet=sr.text_snippet,
                        provenance=sr.provenance,
                        match_type="exact",
                        score=sr.score,
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"ECLI lookup failed for {ecli}: {e}")
            return []
    
    def _lookup_article(
        self,
        index,
        article: str,
        code: Optional[str],
    ) -> List[RetrievalResult]:
        """Lookup article avec code optionnel."""
        try:
            # Build search query
            if code:
                query = f"{article} code {code}"
            else:
                query = article
            
            search_results = index.search(query, limit=5)
            
            results = []
            for sr in search_results:
                # Verify article appears in citation or text
                if article.lower() in sr.citation.lower() or article.lower() in sr.text_snippet.lower():
                    results.append(RetrievalResult(
                        chunk_id=sr.chunk_id,
                        doc_id=sr.doc_id,
                        source=sr.source,
                        citation=sr.citation,
                        pinpoint=sr.pinpoint,
                        text=sr.text_snippet,
                        text_snippet=sr.text_snippet,
                        provenance=sr.provenance,
                        match_type="exact",
                        score=sr.score,
                    ))
            
            return results[:2]  # Max 2 per article
            
        except Exception as e:
            logger.error(f"Article lookup failed for {article}: {e}")
            return []
    
    def _search(
        self,
        index,
        query: str,
        source: Optional[str],
        limit: int,
    ) -> List[RetrievalResult]:
        """Search lexical."""
        try:
            search_results = index.search(query, source=source, limit=limit)
            
            results = []
            for sr in search_results:
                results.append(RetrievalResult(
                    chunk_id=sr.chunk_id,
                    doc_id=sr.doc_id,
                    source=sr.source,
                    citation=sr.citation,
                    pinpoint=sr.pinpoint,
                    text=sr.text_snippet,
                    text_snippet=sr.text_snippet,
                    provenance=sr.provenance,
                    match_type="search",
                    score=sr.score,
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []
    
    def _rerank(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Rerank results.
        
        Priority:
        1. Has complete provenance (license_name, license_url)
        2. Higher BM25 score
        """
        def rank_key(r: RetrievalResult) -> Tuple[int, float]:
            # Provenance completeness
            prov = r.provenance
            has_license = bool(prov.get("license_name")) and bool(prov.get("license_url"))
            prov_score = 1 if has_license else 0
            
            return (prov_score, r.score)
        
        return sorted(results, key=rank_key, reverse=True)
    
    def _filter_by_jurisdiction(
        self,
        results: List[RetrievalResult],
        jurisdiction: str,
    ) -> List[RetrievalResult]:
        """
        Filtre par juridiction.
        
        FR-only sauf demande explicite.
        """
        if jurisdiction.lower() == "fr":
            # Keep only French sources
            fr_sources = {"legi", "cass", "jade", "constit", "jorf"}
            return [r for r in results if r.source.lower() in fr_sources]
        
        elif jurisdiction.lower() == "eu":
            # EU sources (not yet implemented)
            logger.warning("EU jurisdiction filter not yet implemented")
            return results
        
        else:
            # No filter
            return results


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def format_citation_from_result(result: RetrievalResult) -> str:
    """Formate une citation à partir d'un résultat."""
    if result.citation:
        if result.pinpoint:
            return f"{result.citation}, {result.pinpoint}"
        return result.citation
    
    # Fallback
    return f"[{result.source.upper()}] {result.chunk_id[:8]}"


def build_enriched_context(
    retrieval_context: RetrievalContext,
) -> Dict[str, Any]:
    """
    Construit un contexte enrichi pour le prompt de l'agent.
    
    Returns:
        Dict avec:
        - sources: Liste de sources formatées
        - warnings: Warnings (abrogation, etc.)
        - citations: Liste de citations
    """
    sources = []
    citations = []
    warnings = []
    
    for result in retrieval_context.results:
        source_entry = {
            "citation": format_citation_from_result(result),
            "text": result.text_snippet,
            "provenance": {
                "source": result.source,
                "license": result.provenance.get("license_name", ""),
            },
        }
        sources.append(source_entry)
        citations.append(format_citation_from_result(result))
        
        if result.is_abrogated:
            warnings.append(f"⚠️ Texte abrogé: {result.citation}")
    
    if retrieval_context.has_abrogated:
        warnings.append(
            "⚠️ Certains textes cités peuvent être abrogés. "
            "Vérifiez le statut actuel sur les sites officiels."
        )
    
    return {
        "sources": sources,
        "citations": citations,
        "warnings": warnings,
        "total_results": len(retrieval_context.results),
        "exact_matches": retrieval_context.exact_matches,
        "search_matches": retrieval_context.search_matches,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# P5: TEMPORAL VERSION RESOLUTION
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_legal_version(
    text_id: str,
    as_of_date: date,
    versions: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    P5: Resolve the valid version(s) for a legal text at a given date.
    
    Args:
        text_id: The text identifier (e.g., LEGIARTI...)
        as_of_date: The date to resolve for
        versions: Optional list of version dicts. If None, fetch from index.
        
    Returns:
        (resolved_version, all_valid_versions)
        - If exactly 1 valid version: (version_dict, [version_dict])
        - If 0 valid versions: (None, [])
        - If >1 valid versions (ambiguous): (None, [v1, v2, ...])
    """
    if versions is None:
        # In production, would fetch from index
        # For now, return empty as fallback
        logger.warning(f"No versions provided for {text_id}")
        return (None, [])
    
    def parse_date_str(d: Any) -> Optional[date]:
        if d is None:
            return None
        if isinstance(d, date):
            return d
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, str):
            try:
                return datetime.strptime(d[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
        return None
    
    valid_versions = []
    
    for v in versions:
        effective_from = parse_date_str(v.get("effective_from"))
        effective_to = parse_date_str(v.get("effective_to"))
        
        if effective_from is None:
            continue
        
        # Check if valid at as_of_date
        if as_of_date < effective_from:
            continue
        if effective_to is not None and as_of_date > effective_to:
            continue
        
        valid_versions.append(v)
    
    if len(valid_versions) == 1:
        resolved = valid_versions[0]
        resolved["as_of_date_resolved"] = as_of_date.isoformat()
        return (resolved, valid_versions)
    
    return (None, valid_versions)


def filter_results_by_as_of_date(
    results: List[RetrievalResult],
    as_of_date: date,
) -> Tuple[List[RetrievalResult], List[str], List[str]]:
    """
    P5: Filter retrieval results by as_of_date.
    
    Args:
        results: List of retrieval results
        as_of_date: Date for temporal filtering
        
    Returns:
        (filtered_results, ambiguous_chunk_ids, not_found_chunk_ids)
    """
    filtered = []
    ambiguous = []
    not_found = []
    
    for r in results:
        # If result has version info, check validity
        if r.effective_from:
            if as_of_date < r.effective_from:
                not_found.append(r.chunk_id)
                continue
            if r.effective_to and as_of_date > r.effective_to:
                not_found.append(r.chunk_id)
                continue
        
        # Check abrogation
        if r.is_abrogated and r.abrogation_date:
            try:
                abr_date = datetime.strptime(r.abrogation_date[:10], "%Y-%m-%d").date()
                if as_of_date > abr_date:
                    not_found.append(r.chunk_id)
                    continue
            except ValueError:
                pass
        
        # Mark as resolved
        r.as_of_date_resolved = as_of_date
        filtered.append(r)
    
    return (filtered, ambiguous, not_found)


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "RetrievalResult",
    "RetrievalContext",
    "LegalRetriever",
    "extract_legal_identifiers",
    "format_citation_from_result",
    "build_enriched_context",
    # P5
    "resolve_legal_version",
    "filter_results_by_as_of_date",
]
