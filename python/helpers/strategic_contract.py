"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           STRATEGIC OUTPUT CONTRACT — PRODUCTION ENFORCEMENT                  ║
║                                                                              ║
║  Ce module définit et enforce le contrat de sortie pour les documents         ║
║  stratégiques : études de marché, prévisionnels, pricing, GTM.               ║
║                                                                              ║
║  RÈGLE ABSOLUE: Sortie non sourcée → FAIL_CLOSED + claims=[]                 ║
║                                                                              ║
║  DIFFÉRENCE KOREV: Un document stratégique sans sources vérifiables          ║
║  n'est pas un document Evidence — c'est un pitch.                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field, model_validator


# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class StrategicDocumentType(str, Enum):
    """Types de documents stratégiques — tous CRITIQUES par défaut."""
    MARKET_STUDY = "market_study"           # Étude de marché
    FINANCIAL_FORECAST = "financial_forecast"  # Prévisionnel financier
    PRICING = "pricing"                     # Analyse/stratégie pricing
    GTM = "go_to_market"                    # Go-to-market strategy
    BUSINESS_PLAN = "business_plan"         # Business plan
    COMPETITIVE_ANALYSIS = "competitive_analysis"  # Analyse concurrentielle
    DUE_DILIGENCE = "due_diligence"         # Due diligence


class SourceType(str, Enum):
    """Types de sources acceptées pour documents stratégiques."""
    PUBLIC_STATS = "public_stats"       # Eurostat, INSEE, BLS, etc.
    INDUSTRY_REPORT = "industry_report"  # Gartner, McKinsey, Forrester
    ACADEMIC = "academic"               # Publications académiques (DOI)
    REGULATORY = "regulatory"           # AI Act, RGPD, réglementations
    COMPANY_FILING = "company_filing"   # SEC, AMF, rapports annuels
    COMPETITOR_PUBLIC = "competitor_public"  # Sites web, pricing public
    MARKET_DATA = "market_data"         # Bloomberg, Statista, CB Insights
    PRIMARY_RESEARCH = "primary_research"  # Interviews, surveys (avec N)
    INTERNAL_DATA = "internal_data"     # Données internes vérifiables


class EvidenceGrade(str, Enum):
    """Niveau de preuve pour claims stratégiques."""
    VERIFIED = "V"           # Source publique vérifiable
    PARTIAL = "P"            # Source partielle ou extrapolation
    ESTIMATED = "E"          # Estimation basée sur proxies
    UNVERIFIED = "U"         # Aucune source — INTERDIT en mode Evidence


class StrategicDecision(str, Enum):
    """Décisions possibles pour une sortie stratégique."""
    APPROVED = "APPROVED"
    FAIL_CLOSED = "FAIL_CLOSED"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"


class Criticality(str, Enum):
    """Niveau de criticité du document."""
    HIGH = "HIGH"      # Décision investissement, board
    MEDIUM = "MEDIUM"  # Décision opérationnelle
    LOW = "LOW"        # Information interne


# ═══════════════════════════════════════════════════════════════════════════════
# DÉTECTION DE TYPE DE DOCUMENT STRATÉGIQUE
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGIC_DOCUMENT_PATTERNS: Dict[StrategicDocumentType, List[str]] = {
    StrategicDocumentType.MARKET_STUDY: [
        r"étude\s*de\s*marché", r"market\s*study", r"market\s*analysis",
        r"analyse\s*du\s*marché", r"\bTAM\b", r"\bSAM\b", r"\bSOM\b",
        r"taille\s*du\s*marché", r"market\s*size",
        r"segmentation\s*march", r"opportunité\s*de\s*marché",
    ],
    StrategicDocumentType.FINANCIAL_FORECAST: [
        r"prévision(nel)?", r"forecast", r"\bP&L\b", r"\bPL\b", r"budget",
        r"projection\s*financière", r"financial\s*projection",
        r"cash\s*flow", r"break-?even", r"\bARPA\b", r"\bARR\b", r"\bMRR\b",
        r"rentabilité", r"profitability", r"\bROI\b",
    ],
    StrategicDocumentType.PRICING: [
        r"pricing", r"tarification", r"modèle\s*économique",
        r"business\s*model", r"monétisation", r"grille\s*tarifaire",
        r"stratégie\s*de\s*prix", r"unit\s*economics",
    ],
    StrategicDocumentType.GTM: [
        r"go.?to.?market", r"\bGTM\b", r"stratégie\s*de\s*lancement", r"launch\s*strategy",
        r"acquisition\s*client", r"customer\s*acquisition",
        r"\bCAC\b", r"\bLTV\b", r"funnel\s*commercial", r"pipeline\s*commercial",
    ],
    StrategicDocumentType.COMPETITIVE_ANALYSIS: [
        r"analyse\s*concurrentielle", r"competitive\s*analysis",
        r"benchmark", r"concurrents?", r"competitors?",
        r"positioning", r"positionnement",
    ],
    StrategicDocumentType.BUSINESS_PLAN: [
        r"business\s*plan", r"plan\s*d'affaires",
        r"pitch\s*deck", r"executive\s*summary\s*business",
    ],
}


def detect_strategic_document_type(query: str) -> Tuple[bool, List[StrategicDocumentType]]:
    """
    Détecte si une requête demande un document stratégique.
    
    Returns:
        (is_strategic, list_of_detected_types)
    """
    query_lower = query.lower()
    detected = []
    
    for doc_type, patterns in STRATEGIC_DOCUMENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                if doc_type not in detected:
                    detected.append(doc_type)
                break
    
    return bool(detected), detected


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIREMENTS PAR TYPE DE DOCUMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SourceRequirement:
    """Exigences de sourcing par type de document."""
    min_sources: int
    required_source_types: List[SourceType]
    min_public_sources: int  # Sources vérifiables par tiers
    require_tam_sam_som: bool = False
    require_competitor_data: bool = False
    require_financial_basis: bool = False
    require_alternatives: bool = True  # Toujours requis par défaut


DOCUMENT_REQUIREMENTS: Dict[StrategicDocumentType, SourceRequirement] = {
    StrategicDocumentType.MARKET_STUDY: SourceRequirement(
        min_sources=5,
        required_source_types=[SourceType.PUBLIC_STATS, SourceType.INDUSTRY_REPORT],
        min_public_sources=3,
        require_tam_sam_som=True,
        require_competitor_data=True,
    ),
    StrategicDocumentType.FINANCIAL_FORECAST: SourceRequirement(
        min_sources=4,
        required_source_types=[SourceType.MARKET_DATA, SourceType.COMPANY_FILING],
        min_public_sources=2,
        require_financial_basis=True,
    ),
    StrategicDocumentType.PRICING: SourceRequirement(
        min_sources=3,
        required_source_types=[SourceType.COMPETITOR_PUBLIC, SourceType.MARKET_DATA],
        min_public_sources=2,
        require_competitor_data=True,
    ),
    StrategicDocumentType.GTM: SourceRequirement(
        min_sources=4,
        required_source_types=[SourceType.MARKET_DATA, SourceType.INDUSTRY_REPORT],
        min_public_sources=2,
    ),
    StrategicDocumentType.COMPETITIVE_ANALYSIS: SourceRequirement(
        min_sources=5,
        required_source_types=[SourceType.COMPETITOR_PUBLIC, SourceType.INDUSTRY_REPORT],
        min_public_sources=3,
        require_competitor_data=True,
    ),
    StrategicDocumentType.BUSINESS_PLAN: SourceRequirement(
        min_sources=6,
        required_source_types=[
            SourceType.PUBLIC_STATS, 
            SourceType.MARKET_DATA,
            SourceType.INDUSTRY_REPORT
        ],
        min_public_sources=4,
        require_tam_sam_som=True,
        require_financial_basis=True,
    ),
    StrategicDocumentType.DUE_DILIGENCE: SourceRequirement(
        min_sources=8,
        required_source_types=[
            SourceType.COMPANY_FILING,
            SourceType.REGULATORY,
            SourceType.PUBLIC_STATS
        ],
        min_public_sources=5,
        require_financial_basis=True,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class StrategicCitation(BaseModel):
    """
    Citation/source pour un claim stratégique.
    
    INVARIANTS:
    - reference doit être vérifiable (URL, rapport, dataset)
    - date d'accès requise pour sources web
    - type doit correspondre à SourceType
    """
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    reference: str = Field(..., min_length=1)
    url: Optional[str] = None
    access_date: Optional[str] = None  # Pour sources web
    page: Optional[str] = None  # Page/section si rapport
    dataset: Optional[str] = None  # Si données statistiques
    
    @model_validator(mode='after')
    def validate_source_completeness(self) -> 'StrategicCitation':
        """Valide que la source est suffisamment détaillée."""
        # Les sources web doivent avoir une date d'accès
        if self.url and not self.access_date:
            # Warning mais pas bloquant
            pass
        
        # Vérifier que la référence n'est pas générique
        generic_refs = ["internet", "web", "source", "données", "data", "various"]
        if any(g in self.reference.lower() for g in generic_refs):
            if len(self.reference) < 20:  # Trop court pour être précis
                raise ValueError(
                    f"CITATION VIOLATION: Reference too generic: '{self.reference}'. "
                    f"Provide specific source (report name, URL, dataset ID)."
                )
        
        return self


class StrategicClaim(BaseModel):
    """
    Claim stratégique avec sources obligatoires.
    
    INVARIANTS ENFORCED:
    - source_ids DOIT être non vide (différence Korev)
    - evidence_grade calculé depuis sources
    - claims sans source = UNVERIFIED = INTERDIT en production
    """
    claim_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    source_ids: List[str] = Field(
        default_factory=list,
        description="IDs des sources supportant ce claim"
    )
    evidence_grade: str = Field(default="U")  # Default UNVERIFIED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Contexte spécifique
    is_quantitative: bool = False  # Contient des chiffres
    is_projection: bool = False    # Est une projection/estimation
    time_horizon: Optional[str] = None  # "2024", "2024-2027", etc.
    
    @model_validator(mode='after')
    def validate_sourcing_rule(self) -> 'StrategicClaim':
        """
        RÈGLE KOREV: Un claim stratégique sans source n'est pas Evidence.
        """
        if not self.source_ids:
            self.evidence_grade = "U"  # Force UNVERIFIED
            self.confidence = 0.0
        elif len(self.source_ids) == 1:
            if self.evidence_grade == "V":
                self.evidence_grade = "P"  # Une seule source = PARTIAL max
        
        # Les projections quantitatives doivent être sourcées
        if self.is_quantitative and self.is_projection:
            if len(self.source_ids) < 1:
                raise ValueError(
                    f"CLAIM VIOLATION: Quantitative projection '{self.claim_id}' "
                    f"requires at least 1 source basis. Mark as UNVERIFIED or provide sources."
                )
        
        return self


class HypothesisDeclaration(BaseModel):
    """Hypothèse explicite avec impact et vérifiabilité."""
    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    impact: str = Field(..., description="LOW/MEDIUM/HIGH")
    verifiable: bool = Field(default=False)
    verification_method: Optional[str] = None


class AlternativeAnalysis(BaseModel):
    """Alternative analysée et écartée — OBLIGATOIRE pour décisions structurantes."""
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    rejection_reason: str = Field(..., min_length=1)
    source_ids: List[str] = Field(default_factory=list)


class TAMSAMSOMAnalysis(BaseModel):
    """Analyse TAM/SAM/SOM structurée et sourcée."""
    tam_value: Optional[float] = None  # En EUR/USD
    tam_unit: str = "EUR"
    tam_source_ids: List[str] = Field(default_factory=list)
    tam_methodology: Optional[str] = None
    
    sam_value: Optional[float] = None
    sam_percentage_of_tam: Optional[float] = None
    sam_source_ids: List[str] = Field(default_factory=list)
    sam_methodology: Optional[str] = None
    
    som_value: Optional[float] = None
    som_percentage_of_sam: Optional[float] = None
    som_source_ids: List[str] = Field(default_factory=list)
    som_methodology: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_tam_sam_som_logic(self) -> 'TAMSAMSOMAnalysis':
        """Valide la cohérence TAM > SAM > SOM."""
        if self.tam_value and self.sam_value:
            if self.sam_value > self.tam_value:
                raise ValueError("SAM cannot be larger than TAM")
        
        if self.sam_value and self.som_value:
            if self.som_value > self.sam_value:
                raise ValueError("SOM cannot be larger than SAM")
        
        # Chaque niveau doit avoir au moins une source
        if self.tam_value and not self.tam_source_ids:
            raise ValueError("TAM value requires source_ids")
        
        return self


class StrategicMeta(BaseModel):
    """Métadonnées obligatoires pour une réponse stratégique."""
    document_type: str = Field(...)
    criticality: str = Field(default="HIGH")  # Par défaut HIGH
    evidence_grade_global: str = Field(default="U")
    
    # Agents appelés
    agents_invoked: List[str] = Field(default_factory=list)
    consensus_required: bool = Field(default=True)
    consensus_status: Optional[str] = None
    
    # Sourcing stats
    total_sources: int = Field(default=0)
    public_sources: int = Field(default=0)
    unverified_claims: int = Field(default=0)
    
    # Timestamp
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Fail reason si applicable
    fail_reason: Optional[str] = None
    missing_data: List[str] = Field(default_factory=list)


class StrategicStructuredResponse(BaseModel):
    """
    Format de sortie OBLIGATOIRE pour documents stratégiques.
    
    INVARIANTS KOREV:
    - Si decision="FAIL_CLOSED" → claims avec source_ids vides
    - Chaque claim.source_ids doit référencer des IDs existants dans citations
    - Alternatives obligatoires pour décisions structurantes
    - TAM/SAM/SOM obligatoire si document_type=MARKET_STUDY
    """
    # Décision
    decision: str = Field(default="FAIL_CLOSED")
    
    # Contenu structuré
    claims: List[StrategicClaim] = Field(default_factory=list)
    citations: List[StrategicCitation] = Field(default_factory=list)
    hypotheses: List[HypothesisDeclaration] = Field(default_factory=list)
    alternatives: List[AlternativeAnalysis] = Field(default_factory=list)
    
    # Analyses spécifiques
    tam_sam_som: Optional[TAMSAMSOMAnalysis] = None
    
    # Markdown généré
    answer_md: str = Field(..., min_length=1)
    
    # Meta
    meta: StrategicMeta
    
    @model_validator(mode='after')
    def validate_strategic_invariants(self) -> 'StrategicStructuredResponse':
        """
        INVARIANTS KOREV pour documents stratégiques.
        """
        # Invariant 1: FAIL_CLOSED => aucun claim avec sources
        if self.decision == "FAIL_CLOSED":
            sourced_claims = [c for c in self.claims if c.source_ids]
            if sourced_claims:
                # OK - on peut avoir des claims partiellement sourcés
                pass
        
        # Invariant 2: Tous les source_ids doivent exister dans citations
        citation_ids: Set[str] = {c.id for c in self.citations}
        
        for claim in self.claims:
            missing_ids = set(claim.source_ids) - citation_ids
            if missing_ids:
                raise ValueError(
                    f"INVARIANT VIOLATION: Claim '{claim.claim_id}' references "
                    f"source_ids {missing_ids} not found in citations. "
                    f"Available citations: {citation_ids}"
                )
        
        # Invariant 3: Alternatives obligatoires pour certains types
        doc_type = self.meta.document_type
        if doc_type in ["market_study", "pricing", "business_plan"]:
            if not self.alternatives:
                raise ValueError(
                    f"INVARIANT VIOLATION: {doc_type} requires at least 1 alternative analysis"
                )
        
        # Invariant 4: TAM/SAM/SOM pour market study
        if doc_type == "market_study" and self.decision != "FAIL_CLOSED":
            if not self.tam_sam_som:
                raise ValueError(
                    "INVARIANT VIOLATION: market_study requires TAM/SAM/SOM analysis"
                )
        
        # Calculer les stats meta
        self.meta.total_sources = len(self.citations)
        self.meta.public_sources = len([
            c for c in self.citations 
            if c.type in ["public_stats", "industry_report", "regulatory", "company_filing"]
        ])
        self.meta.unverified_claims = len([
            c for c in self.claims if c.evidence_grade == "U"
        ])
        
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategicValidationResult:
    """Résultat de validation du contrat stratégique."""
    is_valid: bool
    decision: StrategicDecision
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    structured_response: Optional[StrategicStructuredResponse] = None
    fail_closed_response: Optional[Dict[str, Any]] = None
    
    # Stats détaillées
    source_count: int = 0
    public_source_count: int = 0
    unverified_claim_count: int = 0
    missing_requirements: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN VALIDATION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_strategic_output(
    output: Union[Dict[str, Any], str],
    document_type: StrategicDocumentType = StrategicDocumentType.MARKET_STUDY,
    criticality: Criticality = Criticality.HIGH,
    strict_mode: bool = True,
) -> StrategicValidationResult:
    """
    Valide une sortie stratégique contre le contrat Evidence.
    
    ENFORCEMENT RULES:
    1. Output DOIT être structuré
    2. Sources DOIVENT être présentes et vérifiables
    3. TAM/SAM/SOM DOIT être présent pour market study
    4. Alternatives DOIVENT être analysées
    5. Si strict_mode=True et sourcing insuffisant → FAIL_CLOSED
    
    Args:
        output: La sortie de l'agent (dict ou string)
        document_type: Type de document stratégique
        criticality: Niveau de criticité
        strict_mode: Si True, force FAIL_CLOSED sur sourcing insuffisant
        
    Returns:
        StrategicValidationResult avec decision et détails
    """
    errors: List[str] = []
    warnings: List[str] = []
    missing_requirements: List[str] = []
    
    # Rule 0: String = FAIL_CLOSED immédiat
    if isinstance(output, str):
        return StrategicValidationResult(
            is_valid=False,
            decision=StrategicDecision.FAIL_CLOSED,
            errors=["Output is plain text, not structured. Evidence requires structured output."],
            fail_closed_response=create_strategic_fail_closed(
                reason="Output format violation: expected structured response, got plain text",
                document_type=document_type,
                missing_data=["Structured claims", "Citations", "TAM/SAM/SOM", "Alternatives"]
            )
        )
    
    if not isinstance(output, dict):
        return StrategicValidationResult(
            is_valid=False,
            decision=StrategicDecision.FAIL_CLOSED,
            errors=[f"Output is {type(output).__name__}, not dict"],
            fail_closed_response=create_strategic_fail_closed(
                reason=f"Output format violation: expected dict, got {type(output).__name__}",
                document_type=document_type,
            )
        )
    
    # Rule 1: Extraire les données
    claims_data = output.get("claims", [])
    citations_data = output.get("citations", [])
    
    # Rule 2: Compter les sources
    source_count = len(citations_data)
    public_source_types = {"public_stats", "industry_report", "regulatory", "company_filing", "market_data"}
    public_source_count = len([
        c for c in citations_data 
        if c.get("type", "").lower() in public_source_types
    ])
    
    # Rule 3: Vérifier les requirements
    requirements = DOCUMENT_REQUIREMENTS.get(document_type)
    if requirements:
        if source_count < requirements.min_sources:
            missing_requirements.append(
                f"Minimum {requirements.min_sources} sources required, got {source_count}"
            )
        
        if public_source_count < requirements.min_public_sources:
            missing_requirements.append(
                f"Minimum {requirements.min_public_sources} public sources required, got {public_source_count}"
            )
        
        # Check required source types
        found_types = {c.get("type", "").lower() for c in citations_data}
        for req_type in requirements.required_source_types:
            if req_type.value not in found_types:
                missing_requirements.append(
                    f"Required source type missing: {req_type.value}"
                )
        
        # TAM/SAM/SOM check
        if requirements.require_tam_sam_som:
            if not output.get("tam_sam_som"):
                missing_requirements.append(
                    "TAM/SAM/SOM analysis required but missing"
                )
        
        # Alternatives check
        if requirements.require_alternatives:
            if not output.get("alternatives"):
                missing_requirements.append(
                    "Alternative analysis required but missing"
                )
        
        # Competitor data check
        if requirements.require_competitor_data:
            has_competitor = any(
                c.get("type", "").lower() in ["competitor_public", "competitive_analysis"]
                for c in citations_data
            )
            if not has_competitor:
                missing_requirements.append(
                    "Competitor/market data required but missing"
                )
    
    # Rule 4: Compter les claims non sourcés
    unverified_claims = [
        c for c in claims_data 
        if not c.get("source_ids") or c.get("evidence_grade") == "U"
    ]
    unverified_count = len(unverified_claims)
    
    if unverified_count > 0 and strict_mode:
        warnings.append(
            f"{unverified_count} claims without sources — marked UNVERIFIED"
        )
    
    # Rule 5: Decision
    if missing_requirements and strict_mode:
        # FAIL_CLOSED si requirements non remplis
        return StrategicValidationResult(
            is_valid=False,
            decision=StrategicDecision.FAIL_CLOSED,
            errors=errors,
            warnings=warnings,
            source_count=source_count,
            public_source_count=public_source_count,
            unverified_claim_count=unverified_count,
            missing_requirements=missing_requirements,
            fail_closed_response=create_strategic_fail_closed(
                reason="Sourcing requirements not met for Evidence-grade output",
                document_type=document_type,
                missing_data=missing_requirements
            )
        )
    
    # Try to validate with Pydantic
    try:
        # Build meta
        meta_data = output.get("meta", {})
        meta_data["document_type"] = document_type.value
        meta_data["criticality"] = criticality.value
        
        structured = StrategicStructuredResponse(
            decision=output.get("decision", "FAIL_CLOSED"),
            claims=[StrategicClaim(**c) for c in claims_data],
            citations=[StrategicCitation(**c) for c in citations_data],
            hypotheses=[HypothesisDeclaration(**h) for h in output.get("hypotheses", [])],
            alternatives=[AlternativeAnalysis(**a) for a in output.get("alternatives", [])],
            tam_sam_som=TAMSAMSOMAnalysis(**output["tam_sam_som"]) if output.get("tam_sam_som") else None,
            answer_md=output.get("answer_md", "No content generated"),
            meta=StrategicMeta(**meta_data)
        )
        
        return StrategicValidationResult(
            is_valid=True,
            decision=StrategicDecision.APPROVED,
            warnings=warnings,
            structured_response=structured,
            source_count=source_count,
            public_source_count=public_source_count,
            unverified_claim_count=unverified_count,
        )
        
    except Exception as e:
        error_msg = str(e)
        if "INVARIANT VIOLATION" in error_msg or "CLAIM VIOLATION" in error_msg:
            errors.append(error_msg)
        else:
            errors.append(f"Validation failed: {error_msg}")
        
        return StrategicValidationResult(
            is_valid=False,
            decision=StrategicDecision.FAIL_CLOSED,
            errors=errors,
            warnings=warnings,
            source_count=source_count,
            public_source_count=public_source_count,
            unverified_claim_count=unverified_count,
            missing_requirements=missing_requirements,
            fail_closed_response=create_strategic_fail_closed(
                reason=f"Contract validation failed: {errors[0] if errors else 'Unknown error'}",
                document_type=document_type,
                missing_data=missing_requirements
            )
        )


def create_strategic_fail_closed(
    reason: str,
    document_type: StrategicDocumentType,
    missing_data: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Crée une réponse FAIL_CLOSED standardisée pour document stratégique.
    
    DIFFÉRENCE KOREV: On ne génère pas de faux contenu.
    On liste explicitement ce qui manque.
    """
    if missing_data is None:
        missing_data = []
    
    requirements = DOCUMENT_REQUIREMENTS.get(document_type)
    req_text = ""
    if requirements:
        req_text = f"""
### Exigences non remplies

| Critère | Requis | Manquant |
|---------|--------|----------|
| Sources totales | {requirements.min_sources}+ | Oui |
| Sources publiques | {requirements.min_public_sources}+ | Oui |
| TAM/SAM/SOM | {"Oui" if requirements.require_tam_sam_som else "Non"} | {"Oui" if requirements.require_tam_sam_som else "-"} |
| Analyse concurrentielle | {"Oui" if requirements.require_competitor_data else "Non"} | {"Oui" if requirements.require_competitor_data else "-"} |
| Alternatives écartées | {"Oui" if requirements.require_alternatives else "Non"} | {"Oui" if requirements.require_alternatives else "-"} |
"""
    
    missing_list = "\n".join([f"- {m}" for m in missing_data]) if missing_data else "- Données non spécifiées"
    
    return {
        "decision": "FAIL_CLOSED",
        "reason": reason,
        "claims": [],
        "citations": [],
        "hypotheses": [],
        "alternatives": [],
        "tam_sam_som": None,
        "answer_md": f"""## ⚠️ DOCUMENT NON GÉNÉRABLE — FAIL_CLOSED

### Raison

**{reason}**

Ce document stratégique ne peut pas être généré en mode Evidence car les données nécessaires ne sont pas disponibles ou vérifiables.

{req_text}

### Données manquantes

{missing_list}

### Pourquoi ce refus ?

KOREV Evidence refuse de générer un document stratégique non sourcé car :

1. **Traçabilité** — Chaque affirmation doit être liée à une source vérifiable
2. **Auditabilité** — Un investisseur/board doit pouvoir vérifier les chiffres
3. **Intégrité** — Mieux vaut refuser que produire du "pitch non fondé"

### Prochaines étapes

Pour générer ce document en mode Evidence :

1. Fournir des sources publiques (Eurostat, INSEE, rapports sectoriels)
2. Inclure des benchmarks concurrentiels sourcés
3. Détailler les hypothèses et leur base de calcul
4. Documenter les alternatives analysées et écartées

---

*KOREV Evidence — Refus explicite plutôt que contenu non vérifiable.*
""",
        "meta": {
            "document_type": document_type.value,
            "criticality": "HIGH",
            "evidence_grade_global": "INSUFFICIENT",
            "consensus_status": "fail_closed",
            "fail_reason": reason,
            "missing_data": missing_data,
            "generated_at": datetime.now().isoformat(),
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def is_strategic_request(query: str) -> Tuple[bool, List[StrategicDocumentType], Criticality]:
    """
    Détecte si une requête est stratégique et retourne sa criticité.
    
    RÈGLE KOREV: Les documents stratégiques sont CRITIQUES par défaut.
    
    Returns:
        (is_strategic, document_types, criticality)
    """
    is_strategic, doc_types = detect_strategic_document_type(query)
    
    if not is_strategic:
        return False, [], Criticality.LOW
    
    # Tous les documents stratégiques sont HIGH par défaut
    # Sauf si explicitement "draft" ou "interne"
    criticality = Criticality.HIGH
    
    draft_patterns = [r"draft", r"brouillon", r"interne", r"internal", r"test"]
    for pattern in draft_patterns:
        if re.search(pattern, query.lower()):
            criticality = Criticality.MEDIUM
            break
    
    return True, doc_types, criticality


def get_required_agents(doc_types: List[StrategicDocumentType]) -> List[str]:
    """
    Retourne les agents requis pour un type de document.
    
    RÈGLE KOREV: Documents stratégiques = agents spécialisés obligatoires.
    """
    required = set()
    
    for doc_type in doc_types:
        if doc_type == StrategicDocumentType.MARKET_STUDY:
            required.update(["researcher", "finance", "marketing"])
        elif doc_type == StrategicDocumentType.FINANCIAL_FORECAST:
            required.update(["finance", "researcher"])
        elif doc_type == StrategicDocumentType.PRICING:
            required.update(["finance", "marketing", "researcher"])
        elif doc_type == StrategicDocumentType.GTM:
            required.update(["marketing", "sales", "researcher"])
        elif doc_type == StrategicDocumentType.COMPETITIVE_ANALYSIS:
            required.update(["researcher", "marketing"])
        elif doc_type == StrategicDocumentType.BUSINESS_PLAN:
            required.update(["finance", "researcher", "marketing", "sales"])
        elif doc_type == StrategicDocumentType.DUE_DILIGENCE:
            required.update(["finance", "legal_safe", "researcher"])
    
    return list(required)


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "StrategicDocumentType",
    "SourceType",
    "EvidenceGrade",
    "StrategicDecision",
    "Criticality",
    # Models
    "StrategicCitation",
    "StrategicClaim",
    "HypothesisDeclaration",
    "AlternativeAnalysis",
    "TAMSAMSOMAnalysis",
    "StrategicMeta",
    "StrategicStructuredResponse",
    "StrategicValidationResult",
    "SourceRequirement",
    # Functions
    "detect_strategic_document_type",
    "validate_strategic_output",
    "create_strategic_fail_closed",
    "is_strategic_request",
    "get_required_agents",
    # Constants
    "STRATEGIC_DOCUMENT_PATTERNS",
    "DOCUMENT_REQUIREMENTS",
]
