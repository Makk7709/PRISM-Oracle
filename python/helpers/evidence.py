"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    EVIDENCE PACK — Zero Hallucination System                 ║
║                                                                              ║
║  Système de gestion des preuves pour le mode "zéro hallucination".           ║
║                                                                              ║
║  Principes:                                                                  ║
║  1. Chaque claim DOIT référencer au moins 1 source                           ║
║  2. Les domaines critiques exigent 2+ sources indépendantes                  ║
║  3. Pas de source = pas de claim (fail-closed)                               ║
║  4. Toutes les sources sont hashées et traçables                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from python.helpers.criticality_router import CriticalDomain

logger = logging.getLogger("evidence")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class SourceType(str, Enum):
    """Types de sources."""
    PRIMARY = "primary"          # Paper original, guideline officielle
    SECONDARY = "secondary"      # Revue, méta-analyse
    TERTIARY = "tertiary"        # Vulgarisation, Wikipedia
    WEB = "web"                  # Page web générale
    DATABASE = "database"        # Base de données (PubMed, etc.)
    TOOL_OUTPUT = "tool_output"  # Sortie d'outil MCP
    USER_PROVIDED = "user_provided"


class SourceReliability(str, Enum):
    """Fiabilité d'une source."""
    HIGH = "high"           # Peer-reviewed, officiel
    MEDIUM = "medium"       # Réputé mais non peer-reviewed
    LOW = "low"             # Non vérifié
    UNKNOWN = "unknown"     # À évaluer


class ClaimStatus(str, Enum):
    """Statut d'un claim."""
    SUPPORTED = "supported"       # Sources suffisantes
    PARTIAL = "partial"           # Sources insuffisantes mais existantes
    UNSUPPORTED = "unsupported"   # Aucune source
    INVALIDATED = "invalidated"   # Contredit par les sources


class EvidenceValidationResult(str, Enum):
    """Résultat de validation du pack de preuves."""
    SUFFICIENT = "sufficient"       # Prêt pour consensus
    INSUFFICIENT = "insufficient"   # Manque de preuves
    CONTRADICTORY = "contradictory" # Sources contradictoires
    MISSING = "missing"             # Pas de sources du tout


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIREMENTS BY DOMAIN
# ═══════════════════════════════════════════════════════════════════════════════

DOMAIN_EVIDENCE_REQUIREMENTS: Dict[CriticalDomain, Dict[str, Any]] = {
    CriticalDomain.LEGAL: {
        "min_sources": 2,
        "require_primary": True,  # Besoin d'au moins 1 source primaire
        "accepted_types": [SourceType.PRIMARY, SourceType.SECONDARY, SourceType.DATABASE],
        "min_reliability": SourceReliability.MEDIUM,
        "max_age_days": 365 * 2,  # Sources de moins de 2 ans
    },
    CriticalDomain.MEDICAL: {
        "min_sources": 2,
        "require_primary": True,
        "accepted_types": [SourceType.PRIMARY, SourceType.SECONDARY, SourceType.DATABASE],
        "min_reliability": SourceReliability.HIGH,
        "max_age_days": 365 * 3,  # 3 ans pour médical
    },
    CriticalDomain.SCIENTIFIC: {
        "min_sources": 2,
        "require_primary": True,
        "accepted_types": [SourceType.PRIMARY, SourceType.SECONDARY, SourceType.DATABASE],
        "min_reliability": SourceReliability.MEDIUM,
        "max_age_days": 365 * 5,  # 5 ans pour scientifique
    },
    CriticalDomain.FINANCE_HIGH_RISK: {
        "min_sources": 1,
        "require_primary": False,
        "accepted_types": [SourceType.PRIMARY, SourceType.SECONDARY, SourceType.WEB, SourceType.DATABASE],
        "min_reliability": SourceReliability.MEDIUM,
        "max_age_days": 365,  # 1 an pour finance
    },
    CriticalDomain.DEFAULT: {
        "min_sources": 1,
        "require_primary": False,
        "accepted_types": list(SourceType),
        "min_reliability": SourceReliability.LOW,
        "max_age_days": None,  # Pas de limite
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Source(BaseModel):
    """Une source de preuve."""
    
    # Identification
    source_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Localisation
    url: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    publication: Optional[str] = None  # Journal, site, etc.
    publication_date: Optional[str] = None
    
    # Contenu
    excerpt: str = ""  # Extrait pertinent
    excerpt_hash: str = ""
    full_content_hash: str = ""
    
    # Métadonnées
    source_type: SourceType = SourceType.WEB
    reliability: SourceReliability = SourceReliability.UNKNOWN
    tool_name: Optional[str] = None  # MCP qui a récupéré la source
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Validation
    is_verified: bool = False
    verification_notes: str = ""
    
    @field_validator("excerpt_hash", mode="before")
    @classmethod
    def compute_excerpt_hash(cls, v, info):
        if v:
            return v
        excerpt = info.data.get("excerpt", "")
        if excerpt:
            return hashlib.sha256(excerpt.encode()).hexdigest()[:16]
        return ""
    
    def compute_content_hash(self, content: str) -> str:
        """Calcule le hash du contenu complet."""
        self.full_content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        return self.full_content_hash
    
    def matches_requirements(
        self,
        accepted_types: List[SourceType],
        min_reliability: SourceReliability,
        max_age_days: Optional[int] = None,
    ) -> bool:
        """Vérifie si la source correspond aux exigences."""
        # Type
        if self.source_type not in accepted_types:
            return False
        
        # Fiabilité
        reliability_order = [
            SourceReliability.UNKNOWN,
            SourceReliability.LOW,
            SourceReliability.MEDIUM,
            SourceReliability.HIGH,
        ]
        if reliability_order.index(self.reliability) < reliability_order.index(min_reliability):
            return False
        
        # Âge (si applicable)
        if max_age_days and self.publication_date:
            try:
                pub_date = datetime.fromisoformat(self.publication_date.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - pub_date).days
                if age_days > max_age_days:
                    return False
            except (ValueError, TypeError):
                pass  # Ignorer si date invalide
        
        return True


class Claim(BaseModel):
    """Un claim (affirmation) avec ses sources."""
    
    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    domain: CriticalDomain = CriticalDomain.DEFAULT
    
    # Exigences
    required_sources_min: int = 1
    
    # Sources associées
    supported_by_source_ids: List[str] = Field(default_factory=list)
    contradicted_by_source_ids: List[str] = Field(default_factory=list)
    
    # Statut
    status: ClaimStatus = ClaimStatus.UNSUPPORTED
    confidence: float = 0.0  # 0.0-1.0
    
    # Notes
    validation_notes: str = ""
    
    def evaluate_status(self, sources: Dict[str, Source]) -> ClaimStatus:
        """
        Évalue le statut du claim basé sur les sources disponibles.
        Met à jour self.status et self.confidence.
        """
        # Sources contradictoires ?
        if self.contradicted_by_source_ids:
            self.status = ClaimStatus.INVALIDATED
            self.confidence = 0.0
            return self.status
        
        # Compter les sources de support valides
        valid_sources = [
            sources[sid] for sid in self.supported_by_source_ids
            if sid in sources
        ]
        
        if not valid_sources:
            self.status = ClaimStatus.UNSUPPORTED
            self.confidence = 0.0
        elif len(valid_sources) < self.required_sources_min:
            self.status = ClaimStatus.PARTIAL
            self.confidence = len(valid_sources) / self.required_sources_min * 0.5
        else:
            self.status = ClaimStatus.SUPPORTED
            # Confiance basée sur la fiabilité des sources
            reliability_scores = {
                SourceReliability.HIGH: 1.0,
                SourceReliability.MEDIUM: 0.7,
                SourceReliability.LOW: 0.4,
                SourceReliability.UNKNOWN: 0.2,
            }
            avg_reliability = sum(
                reliability_scores[s.reliability] for s in valid_sources
            ) / len(valid_sources)
            self.confidence = avg_reliability
        
        return self.status


class EvidencePack(BaseModel):
    """Pack de preuves complet pour une réponse."""
    
    pack_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Contexte
    query: str = ""
    domain: CriticalDomain = CriticalDomain.DEFAULT
    strict_mode: bool = False
    
    # Contenu
    sources: Dict[str, Source] = Field(default_factory=dict)
    claims: List[Claim] = Field(default_factory=list)
    
    # Validation
    validation_result: EvidenceValidationResult = EvidenceValidationResult.MISSING
    validation_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Draft
    draft_response: str = ""
    
    def add_source(self, source: Source) -> str:
        """Ajoute une source et retourne son ID."""
        self.sources[source.source_id] = source
        return source.source_id
    
    def add_claim(self, claim: Claim):
        """Ajoute un claim."""
        self.claims.append(claim)
    
    def link_claim_to_source(self, claim_id: str, source_id: str):
        """Lie un claim à une source."""
        for claim in self.claims:
            if claim.claim_id == claim_id:
                if source_id not in claim.supported_by_source_ids:
                    claim.supported_by_source_ids.append(source_id)
                break
    
    def validate(self) -> EvidenceValidationResult:
        """
        Valide le pack de preuves selon les exigences du domaine.
        
        Returns:
            EvidenceValidationResult
        """
        requirements = DOMAIN_EVIDENCE_REQUIREMENTS.get(
            self.domain,
            DOMAIN_EVIDENCE_REQUIREMENTS[CriticalDomain.DEFAULT]
        )
        
        details = {
            "domain": self.domain.value,
            "strict_mode": self.strict_mode,
            "requirements": requirements,
            "sources_count": len(self.sources),
            "claims_count": len(self.claims),
            "issues": [],
        }
        
        # 1. Vérifier le nombre de sources
        valid_sources = [
            s for s in self.sources.values()
            if s.matches_requirements(
                requirements["accepted_types"],
                requirements["min_reliability"],
                requirements.get("max_age_days"),
            )
        ]
        
        details["valid_sources_count"] = len(valid_sources)
        
        if len(valid_sources) < requirements["min_sources"]:
            details["issues"].append(
                f"Insufficient sources: {len(valid_sources)} < {requirements['min_sources']}"
            )
        
        # 2. Vérifier les sources primaires si requis
        if requirements.get("require_primary"):
            primary_sources = [
                s for s in valid_sources
                if s.source_type == SourceType.PRIMARY
            ]
            if not primary_sources:
                details["issues"].append("No primary source found (required)")
        
        # 3. Évaluer chaque claim
        unsupported_claims = []
        for claim in self.claims:
            claim.evaluate_status(self.sources)
            if claim.status in [ClaimStatus.UNSUPPORTED, ClaimStatus.INVALIDATED]:
                unsupported_claims.append(claim.claim_id)
        
        details["unsupported_claims"] = unsupported_claims
        
        if unsupported_claims:
            details["issues"].append(
                f"{len(unsupported_claims)} claim(s) without sufficient evidence"
            )
        
        # 4. Vérifier les contradictions
        contradicted = [c for c in self.claims if c.status == ClaimStatus.INVALIDATED]
        if contradicted:
            details["issues"].append(
                f"{len(contradicted)} claim(s) contradicted by sources"
            )
            self.validation_result = EvidenceValidationResult.CONTRADICTORY
        elif not self.sources:
            self.validation_result = EvidenceValidationResult.MISSING
        elif details["issues"]:
            self.validation_result = EvidenceValidationResult.INSUFFICIENT
        else:
            self.validation_result = EvidenceValidationResult.SUFFICIENT
        
        self.validation_details = details
        return self.validation_result
    
    def get_missing_evidence_message(self) -> str:
        """
        Génère un message expliquant ce qui manque.
        Utilisé pour le fail-closed.
        """
        if self.validation_result == EvidenceValidationResult.SUFFICIENT:
            return ""
        
        requirements = DOMAIN_EVIDENCE_REQUIREMENTS.get(
            self.domain,
            DOMAIN_EVIDENCE_REQUIREMENTS[CriticalDomain.DEFAULT]
        )
        
        lines = [
            "## ⚠️ Evidence insuffisante pour conclure",
            "",
            f"**Domaine:** {self.domain.value}",
            f"**Mode strict:** {'Oui' if self.strict_mode else 'Non'}",
            "",
            "### Ce qui manque:",
        ]
        
        for issue in self.validation_details.get("issues", []):
            lines.append(f"- {issue}")
        
        lines.extend([
            "",
            "### Exigences pour ce domaine:",
            f"- Minimum {requirements['min_sources']} source(s)",
            f"- Fiabilité minimum: {requirements['min_reliability']}",
        ])
        
        if requirements.get("require_primary"):
            lines.append("- Au moins 1 source primaire requise")
        
        lines.extend([
            "",
            "### Actions recommandées:",
            "1. Rechercher des sources additionnelles",
            "2. Vérifier les sources existantes",
            "3. Reformuler les claims non soutenus",
            "",
            "*Aucune affirmation non sourcée ne sera faite.*"
        ])
        
        return "\n".join(lines)
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Génère un dict pour l'audit log."""
        return {
            "pack_id": self.pack_id,
            "created_at": self.created_at,
            "domain": self.domain.value,
            "strict_mode": self.strict_mode,
            "sources_count": len(self.sources),
            "claims_count": len(self.claims),
            "validation_result": self.validation_result.value,
            "issues": self.validation_details.get("issues", []),
            "source_ids": list(self.sources.keys()),
            "claim_statuses": {
                c.claim_id: c.status.value for c in self.claims
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceBuilder:
    """
    Builder pour construire un EvidencePack à partir de données collectées.
    """
    
    def __init__(
        self,
        query: str,
        domain: CriticalDomain = CriticalDomain.DEFAULT,
        strict_mode: bool = False,
    ):
        self.pack = EvidencePack(
            query=query,
            domain=domain,
            strict_mode=strict_mode,
        )
    
    def add_mcp_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
    ) -> List[str]:
        """
        Ajoute les résultats d'un outil MCP comme sources.
        
        Returns:
            Liste des source_ids créés
        """
        source_ids = []
        
        # Détecter le format du résultat
        results = result.get("results", [result])
        if not isinstance(results, list):
            results = [results]
        
        for item in results:
            source = Source(
                url=item.get("url") or item.get("link"),
                title=item.get("title", "Untitled"),
                authors=item.get("authors", []),
                publication=item.get("source") or item.get("journal"),
                publication_date=item.get("date") or item.get("published"),
                excerpt=item.get("snippet") or item.get("abstract", "")[:500],
                source_type=self._infer_source_type(tool_name, item),
                reliability=self._infer_reliability(tool_name, item),
                tool_name=tool_name,
            )
            
            # Calculer hash du contenu si disponible
            content = item.get("content") or item.get("text", "")
            if content:
                source.compute_content_hash(content)
            
            sid = self.pack.add_source(source)
            source_ids.append(sid)
        
        return source_ids
    
    def add_claim(
        self,
        text: str,
        source_ids: List[str] = None,
        required_sources: int = None,
    ) -> str:
        """
        Ajoute un claim avec ses sources.
        
        Returns:
            claim_id
        """
        requirements = DOMAIN_EVIDENCE_REQUIREMENTS.get(
            self.pack.domain,
            DOMAIN_EVIDENCE_REQUIREMENTS[CriticalDomain.DEFAULT]
        )
        
        claim = Claim(
            text=text,
            domain=self.pack.domain,
            required_sources_min=required_sources or requirements["min_sources"],
            supported_by_source_ids=source_ids or [],
        )
        
        self.pack.add_claim(claim)
        return claim.claim_id
    
    def build(self) -> EvidencePack:
        """
        Finalise et valide le pack.
        
        Returns:
            EvidencePack validé
        """
        self.pack.validate()
        return self.pack
    
    def _infer_source_type(self, tool_name: str, item: Dict) -> SourceType:
        """Infère le type de source depuis le tool."""
        tool_lower = tool_name.lower()
        
        if "arxiv" in tool_lower or "pubmed" in tool_lower:
            return SourceType.PRIMARY
        elif "scholar" in tool_lower:
            return SourceType.SECONDARY
        elif "wikipedia" in tool_lower:
            return SourceType.TERTIARY
        elif "tavily" in tool_lower or "firecrawl" in tool_lower:
            return SourceType.WEB
        else:
            return SourceType.TOOL_OUTPUT
    
    def _infer_reliability(self, tool_name: str, item: Dict) -> SourceReliability:
        """Infère la fiabilité depuis le tool et le contenu."""
        tool_lower = tool_name.lower()
        
        # Sources académiques = haute fiabilité
        if any(t in tool_lower for t in ["arxiv", "pubmed", "scholar", "semantic"]):
            return SourceReliability.HIGH
        
        # Sources web générales = fiabilité moyenne
        if any(t in tool_lower for t in ["tavily", "firecrawl"]):
            # Vérifier le domaine
            url = item.get("url", "")
            if any(d in url for d in [".gov", ".edu", ".org"]):
                return SourceReliability.MEDIUM
            return SourceReliability.LOW
        
        return SourceReliability.UNKNOWN


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_evidence_for_consensus(
    evidence_pack: EvidencePack,
    strict_mode: bool = True,
) -> Tuple[bool, str]:
    """
    Valide un pack de preuves pour soumission au consensus.
    
    Args:
        evidence_pack: Pack à valider
        strict_mode: Mode strict (fail-closed)
        
    Returns:
        (is_valid, message)
    """
    result = evidence_pack.validate()
    
    if result == EvidenceValidationResult.SUFFICIENT:
        return True, "Evidence pack validated"
    
    if strict_mode:
        # En mode strict, on refuse
        message = evidence_pack.get_missing_evidence_message()
        return False, message
    
    # En mode non-strict, on autorise avec avertissement
    if result == EvidenceValidationResult.CONTRADICTORY:
        return False, "Sources contain contradictions"
    
    return True, f"Warning: Evidence is {result.value}"


def create_fail_closed_response(
    query: str,
    domain: CriticalDomain,
    evidence_pack: Optional[EvidencePack] = None,
) -> str:
    """
    Crée une réponse fail-closed quand les preuves sont insuffisantes.
    
    Returns:
        Markdown response
    """
    if evidence_pack:
        return evidence_pack.get_missing_evidence_message()
    
    requirements = DOMAIN_EVIDENCE_REQUIREMENTS.get(
        domain,
        DOMAIN_EVIDENCE_REQUIREMENTS[CriticalDomain.DEFAULT]
    )
    
    return f"""## ⚠️ Impossible de répondre avec certitude

**Domaine:** {domain.value}
**Requête:** {query[:200]}...

### Raison

Les preuves disponibles sont insuffisantes pour formuler une réponse fiable dans ce domaine critique.

### Exigences non satisfaites

- Minimum {requirements['min_sources']} source(s) de fiabilité {requirements['min_reliability']} requise(s)
- Sources primaires requises: {'Oui' if requirements.get('require_primary') else 'Non'}

### Recommandation

1. Rechercher des sources additionnelles via les outils de recherche
2. Consulter un expert du domaine
3. Reformuler la question de manière plus précise

*Ce système applique le principe "fail-closed": en cas de doute, aucune affirmation n'est faite.*
"""


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "SourceType",
    "SourceReliability",
    "ClaimStatus",
    "EvidenceValidationResult",
    # Constants
    "DOMAIN_EVIDENCE_REQUIREMENTS",
    # Models
    "Source",
    "Claim",
    "EvidencePack",
    # Builder
    "EvidenceBuilder",
    # Functions
    "validate_evidence_for_consensus",
    "create_fail_closed_response",
]
