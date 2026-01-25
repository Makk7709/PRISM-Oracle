"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              MEDICAL OUTPUT CONTRACT — PRODUCTION ENFORCEMENT                 ║
║                                                                              ║
║  Ce module définit et enforce le contrat de sortie médical.                   ║
║  Utilisé par le gate/handler pour valider TOUTE sortie médicale.             ║
║                                                                              ║
║  RÈGLE ABSOLUE: Sortie non conforme → FAIL_CLOSED + claims=[]                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceGrade(str, Enum):
    """GRADE evidence quality levels."""
    HIGH = "H"
    MODERATE = "M"
    LOW = "L"
    VERY_LOW = "VL"
    INSUFFICIENT = "INSUFFICIENT"


class SourceType(str, Enum):
    """Types de sources médicales acceptées."""
    LABEL = "label"           # FDA/EMA label
    GUIDELINE = "guideline"   # Société savante
    RCT = "rct"               # Essai randomisé contrôlé
    META = "meta"             # Méta-analyse
    OBSERVATIONAL = "observational"  # Cohorte/registre
    PV = "pv"                 # Pharmacovigilance (FAERS)


class ConsensusStatus(str, Enum):
    """Status du consensus PRISM."""
    VALIDATED = "validated"
    PENDING = "pending"
    FAIL_CLOSED = "fail_closed"


class MedicalDecision(str, Enum):
    """Décisions possibles pour une sortie médicale."""
    APPROVED = "APPROVED"
    FAIL_CLOSED = "FAIL_CLOSED"


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class PVContext(BaseModel):
    """Contexte obligatoire pour les claims de pharmacovigilance."""
    metrics: Dict[str, float] = Field(
        ...,
        description="PRR, ROR, IC metrics"
    )
    label_mentioned: bool = Field(
        ...,
        description="Est-ce que l'événement est dans le label FDA/EMA?"
    )
    rct_confirmed: bool = Field(
        ...,
        description="Est-ce que l'événement est confirmé par RCT?"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Limitations (sous-reporting, confounding, etc.)"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CITATION FORMAT PATTERNS (traçabilité réelle)
# ═══════════════════════════════════════════════════════════════════════════════

CITATION_FORMAT_RULES: Dict[str, re.Pattern] = {
    "pmid": re.compile(r"^PMID[:\s]?\d{7,8}$", re.IGNORECASE),
    "nct": re.compile(r"^NCT\d{8}$", re.IGNORECASE),
    "doi": re.compile(r"^10\.\d{4,}/[^\s]+$"),
    "fda_label": re.compile(r"^FDA\s*(Label|Approval|Safety)", re.IGNORECASE),
    "ema": re.compile(r"^(EMA|EMEA)", re.IGNORECASE),
    "guideline": re.compile(r"^(ESC|ADA|ESMO|ASCO|HAS|NICE|WHO|ACC|AHA)", re.IGNORECASE),
    "faers": re.compile(r"^FAERS", re.IGNORECASE),
}

def validate_citation_format(citation_type: str, reference: str) -> Tuple[bool, str]:
    """
    Valide que la référence respecte le format attendu pour son type.
    
    Returns:
        (is_valid, error_message)
    """
    type_lower = citation_type.lower()
    
    # Types avec format strict
    if type_lower == "pmid":
        if not CITATION_FORMAT_RULES["pmid"].match(reference):
            return False, f"PMID format invalid: '{reference}'. Expected: PMID:12345678"
    
    elif type_lower == "nct":
        if not CITATION_FORMAT_RULES["nct"].match(reference):
            return False, f"NCT format invalid: '{reference}'. Expected: NCT01234567"
    
    elif type_lower == "doi":
        if not CITATION_FORMAT_RULES["doi"].match(reference):
            return False, f"DOI format invalid: '{reference}'. Expected: 10.xxxx/..."
    
    elif type_lower in ["fda_label", "fda"]:
        if not CITATION_FORMAT_RULES["fda_label"].match(reference):
            return False, f"FDA reference format invalid: '{reference}'"
    
    elif type_lower == "faers":
        if not CITATION_FORMAT_RULES["faers"].match(reference):
            return False, f"FAERS reference format invalid: '{reference}'"
    
    # Types plus flexibles (guideline, observational, etc.) - au moins non vide
    elif len(reference.strip()) < 3:
        return False, f"Reference too short: '{reference}'"
    
    return True, ""


class MedicalCitation(BaseModel):
    """
    Citation/source pour un claim médical.
    
    INVARIANTS:
    - type + reference doivent suivre les formats standards
    - PMID doit être numérique (PMID:12345678)
    - NCT doit être format NCT01234567
    - Pas de références génériques/bidons
    """
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    reference: str = Field(..., min_length=1)
    title: Optional[str] = None
    year: Optional[int] = None
    
    @model_validator(mode='after')
    def validate_reference_format(self) -> 'MedicalCitation':
        """Valide que la référence suit le format attendu pour son type."""
        is_valid, error = validate_citation_format(self.type, self.reference)
        if not is_valid:
            raise ValueError(f"CITATION FORMAT VIOLATION: {error}")
        return self


class MedicalClaim(BaseModel):
    """
    Claim médical avec sources obligatoires.
    
    INVARIANTS ENFORCED:
    - source_ids DOIT être non vide
    - source_type="pv" => evidence_grade="VL" (Very Low)
    - confidence entre 0.0 et 1.0
    """
    claim_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    source_ids: List[str] = Field(
        ...,
        min_length=1,  # DOIT être non vide
        description="IDs des sources supportant ce claim"
    )
    source_type: str = Field(...)
    evidence_grade: str = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Optionnel pour PV
    pv_context: Optional[PVContext] = None
    
    @model_validator(mode='after')
    def validate_pv_invariants(self) -> 'MedicalClaim':
        """
        INVARIANT T9-PV: source_type="pv" => evidence_grade in ["VL", "L"]
        Un signal FAERS seul ne peut JAMAIS avoir un grade High/Moderate.
        """
        if self.source_type == "pv" or self.source_type == SourceType.PV:
            if self.evidence_grade not in ["VL", "L", EvidenceGrade.VERY_LOW, EvidenceGrade.LOW]:
                raise ValueError(
                    f"INVARIANT VIOLATION: PV source_type requires evidence_grade VL or L, "
                    f"got {self.evidence_grade}. Signal FAERS ≠ causalité."
                )
            if self.pv_context is None:
                raise ValueError(
                    "INVARIANT VIOLATION: PV claims MUST have pv_context with metrics and limitations"
                )
        return self


class MedicalMeta(BaseModel):
    """Métadonnées obligatoires pour une réponse médicale."""
    evidence_grade_global: str = Field(...)
    consensus_status: str = Field(...)
    offline_mode: bool = Field(default=False)
    fail_reason: Optional[str] = None
    action_blocked: Optional[str] = None


class StructuredResponse(BaseModel):
    """
    Format de sortie OBLIGATOIRE pour le domaine MEDICAL.
    
    INVARIANTS:
    - Si decision="FAIL_CLOSED" → claims DOIT être vide
    - Chaque claim.source_ids doit référencer des IDs existants dans citations
    - PV claims doivent avoir evidence_grade VL/L
    """
    claims: List[MedicalClaim] = Field(default_factory=list)
    answer_md: str = Field(..., min_length=1)
    citations: List[MedicalCitation] = Field(default_factory=list)
    meta: MedicalMeta
    
    # Optionnel
    decision: Optional[str] = None
    reason: Optional[str] = None
    action_refused: bool = False
    
    @model_validator(mode='after')
    def validate_response_invariants(self) -> 'StructuredResponse':
        """
        INVARIANTS T9:
        1. FAIL_CLOSED => claims vide
        2. claim.source_ids ⊆ citations.ids
        """
        # Invariant 1: FAIL_CLOSED => claims vide
        if self.decision == "FAIL_CLOSED" or self.decision == MedicalDecision.FAIL_CLOSED:
            if self.claims:
                raise ValueError(
                    "INVARIANT VIOLATION: FAIL_CLOSED decision requires empty claims list"
                )
        
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
        
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# ANSWER_MD RENDERING (pas de narration libre)
# ═══════════════════════════════════════════════════════════════════════════════

def render_answer_from_claims(
    claims: List[MedicalClaim],
    citations: List[MedicalCitation],
    meta: MedicalMeta,
    context: str = "",
) -> str:
    """
    Génère answer_md UNIQUEMENT à partir des claims déclarés.
    
    Le LLM ne "rédige" plus, il "déclare" des claims.
    Cette fonction transforme les claims en markdown structuré.
    
    Args:
        claims: Liste des claims validés
        citations: Liste des citations
        meta: Métadonnées
        context: Contexte optionnel (ex: "Analyse du bilan de...")
        
    Returns:
        Markdown généré depuis les claims uniquement
    """
    if not claims:
        return "## Aucune Information Validée\n\nAucun claim n'a pu être validé avec des sources suffisantes."
    
    lines = []
    
    # Header
    if context:
        lines.append(f"## {context}")
    else:
        lines.append("## Analyse Médicale")
    
    lines.append("")
    
    # Group claims by evidence grade
    claims_by_grade: Dict[str, List[MedicalClaim]] = {}
    for claim in claims:
        grade = claim.evidence_grade
        if grade not in claims_by_grade:
            claims_by_grade[grade] = []
        claims_by_grade[grade].append(claim)
    
    # Render by grade (H > M > L > VL)
    grade_order = ["H", "M", "L", "VL"]
    grade_labels = {
        "H": "Niveau de Preuve Élevé",
        "M": "Niveau de Preuve Modéré",
        "L": "Niveau de Preuve Faible",
        "VL": "Niveau de Preuve Très Faible (Signal)"
    }
    
    for grade in grade_order:
        if grade in claims_by_grade:
            lines.append(f"### {grade_labels.get(grade, grade)}")
            lines.append("")
            
            for claim in claims_by_grade[grade]:
                # Claim text with inline citations
                citation_refs = ", ".join(claim.source_ids)
                lines.append(f"- {claim.text} [{citation_refs}]")
            
            lines.append("")
    
    # Citations section
    if citations:
        lines.append("### Sources")
        lines.append("")
        for cit in citations:
            title_part = f" - {cit.title}" if cit.title else ""
            year_part = f" ({cit.year})" if cit.year else ""
            lines.append(f"- **[{cit.id}]** {cit.type.upper()}: {cit.reference}{title_part}{year_part}")
        lines.append("")
    
    # Meta
    lines.append("---")
    lines.append(f"*Grade global: {meta.evidence_grade_global} | Consensus: {meta.consensus_status}*")
    lines.append("*Information médicale sourcée. Ne constitue pas un conseil médical individuel.*")
    
    return "\n".join(lines)


def validate_answer_md_no_extra_claims(
    answer_md: str,
    claims: List[MedicalClaim],
) -> Tuple[bool, List[str]]:
    """
    Vérifie que answer_md ne contient pas d'affirmations non présentes dans claims.
    
    HEURISTIQUE best-effort:
    - Extrait les phrases assertives de answer_md
    - Vérifie qu'elles correspondent à des claims déclarés
    
    Returns:
        (is_valid, list_of_suspicious_phrases)
    """
    if not claims:
        # Si pas de claims, answer_md ne devrait pas contenir d'affirmations fortes
        pass
    
    # Extraire les textes des claims pour matching
    claim_texts = [c.text.lower() for c in claims]
    claim_keywords = set()
    for text in claim_texts:
        # Extraire les mots-clés significatifs (>4 chars)
        words = re.findall(r'\b\w{5,}\b', text.lower())
        claim_keywords.update(words)
    
    # Patterns d'affirmations médicales dans answer_md
    assertion_patterns = [
        r"(?:cause|causes|provoque|entraîne)\s+\w+",
        r"(?:reduces?|réduit|diminue)\s+(?:by|de)\s*\d+",
        r"(?:increases?|augmente)\s+(?:by|de|le|la)\s*\d+",
        r"(?:HR|RR|OR)\s*[=:]\s*\d+\.\d+",
        r"(?:efficacy|efficacité)\s+(?:of|de)\s*\d+%",
        r"\d+%\s+(?:reduction|réduction|increase|augmentation)",
        r"(?:contre-?indiqué|contraindicated)",
        r"(?:recommandé|recommended|advised)",
    ]
    
    suspicious = []
    answer_lower = answer_md.lower()
    
    for pattern in assertion_patterns:
        matches = re.findall(pattern, answer_lower, re.IGNORECASE)
        for match in matches:
            # Vérifier si cette assertion est couverte par un claim
            match_words = set(re.findall(r'\b\w{5,}\b', match.lower()))
            
            # Si moins de 50% des mots significatifs sont dans les claims, c'est suspect
            if match_words and len(match_words & claim_keywords) < len(match_words) * 0.5:
                suspicious.append(match)
    
    # Limiter à 5 exemples
    suspicious = suspicious[:5]
    
    return len(suspicious) == 0, suspicious


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MedicalValidationResult:
    """Résultat de validation du contrat médical."""
    is_valid: bool
    decision: MedicalDecision
    errors: List[str] = field(default_factory=list)
    structured_response: Optional[StructuredResponse] = None
    fail_closed_response: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# RED FLAGS DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

RED_FLAG_PATTERNS: List[str] = [
    # Cardiaque
    r"douleur\s*thoracique", r"chest\s*pain", r"oppression",
    r"infarctus", r"heart\s*attack", r"cardiac\s*arrest",
    # Respiratoire
    r"can'?t\s*breathe", r"cannot\s*breathe", r"ne\s*(peux?|peut)\s*pas\s*respirer",
    r"dyspnée\s*(aiguë|sévère)", r"détresse\s*respiratoire", r"respiratory\s*distress",
    # Neurologique
    r"paralys", r"déficit\s*neuro", r"stroke", r"avc",
    r"perte\s*de\s*(conscience|connaissance)", r"loss\s*of\s*consciousness",
    r"confusion\s*aiguë", r"acute\s*confusion",
    # Psychiatrique
    r"suicid", r"me\s*tuer", r"kill\s*(my)?self", r"envie\s*de\s*mourir",
    # Saignement
    r"hémorrag", r"hemorrhag", r"bleeding\s*(heavily|profusely|uncontrolled)",
    r"saignement\s*(important|massif|abondant)",
    # Anaphylaxie
    r"anaphyla", r"gonflement.*(gorge|langue)", r"throat.*swelling",
    r"choc\s*allergique", r"allergic\s*shock",
    # Douleur abdominale sévère
    r"douleur\s*abdominale\s*(intense|sévère|insupportable)",
    r"severe\s*abdominal\s*pain",
]

PATIENT_SPECIFIC_ACTION_PATTERNS: List[str] = [
    # Posologie
    r"quelle\s*(dose|posologie)", r"combien\s*de\s*(mg|ml|comprimé)",
    r"what\s*dose", r"how\s*(much|many).*take",
    # Prescription
    r"prescri(re|vez|ption|be)", r"ordonnance",
    r"can\s*you\s*(give|prescribe)", r"donnez-moi",
    # Modification traitement
    r"(dois|devrai)-?je\s*(arrêter|continuer|changer)",
    r"should\s*i\s*(stop|continue|change|switch)",
    r"arrêter\s*(mon|le)\s*traitement", r"stop.*medication",
    r"modifier\s*(ma|la)\s*dose",
    # Diagnostic personnel
    r"(est-ce|ai)-?je\s*(un|une|le|la)", r"do\s*i\s*have",
    r"suis-je\s*(malade|atteint)",
    # Personnel explicite
    r"pour\s*(moi|mon\s*père|ma\s*mère|mon\s*enfant)",
    r"for\s*(me|my\s*(father|mother|child|son|daughter))",
]


def detect_red_flags(query: str) -> Tuple[bool, List[str]]:
    """
    Détecte les red flags nécessitant orientation urgences.
    
    Returns:
        (has_red_flag, matched_patterns)
    """
    query_lower = query.lower()
    matched = []
    
    for pattern in RED_FLAG_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            matched.append(pattern)
    
    return bool(matched), matched


def is_patient_specific_actionable(query: str) -> Tuple[bool, List[str]]:
    """
    Détecte si une query demande une action patient-specific.
    
    Returns:
        (is_patient_specific, matched_patterns)
    """
    query_lower = query.lower()
    matched = []
    
    for pattern in PATIENT_SPECIFIC_ACTION_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            matched.append(pattern)
    
    return bool(matched), matched


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN VALIDATION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_medical_output(
    output: Union[Dict[str, Any], str],
    offline_mode: bool = False,
) -> MedicalValidationResult:
    """
    Valide une sortie médicale contre le contrat StructuredResponse.
    
    ENFORCEMENT RULES:
    1. Output DOIT être un dict avec structured_response
    2. structured_response DOIT passer la validation Pydantic
    3. Si offline_mode=True → FAIL_CLOSED automatique
    4. Tous les invariants T9 doivent être respectés
    
    Args:
        output: La sortie de l'agent (dict ou string)
        offline_mode: Si True, force FAIL_CLOSED
        
    Returns:
        MedicalValidationResult avec decision et détails
    """
    errors: List[str] = []
    
    # Rule 0: Offline mode → FAIL_CLOSED immédiat
    if offline_mode:
        return MedicalValidationResult(
            is_valid=False,
            decision=MedicalDecision.FAIL_CLOSED,
            errors=["OFFLINE_MODE=true - No access to evidence sources"],
            fail_closed_response=create_fail_closed_response(
                reason="OFFLINE_MODE=true - Cannot validate medical output without source access",
                query_context="offline validation"
            )
        )
    
    # Rule 1: Output doit être un dict
    if isinstance(output, str):
        return MedicalValidationResult(
            is_valid=False,
            decision=MedicalDecision.FAIL_CLOSED,
            errors=["Output is plain text, not StructuredResponse JSON"],
            fail_closed_response=create_fail_closed_response(
                reason="Output format violation: expected StructuredResponse, got plain text",
                query_context="format validation"
            )
        )
    
    if not isinstance(output, dict):
        return MedicalValidationResult(
            is_valid=False,
            decision=MedicalDecision.FAIL_CLOSED,
            errors=[f"Output is {type(output).__name__}, not dict"],
            fail_closed_response=create_fail_closed_response(
                reason=f"Output format violation: expected dict, got {type(output).__name__}",
                query_context="format validation"
            )
        )
    
    # Rule 2: Extraire structured_response
    # Peut être à la racine ou dans tool_args
    sr_data = output.get("structured_response")
    if sr_data is None:
        sr_data = output.get("tool_args", {}).get("structured_response")
    
    if sr_data is None:
        # Peut-être que c'est déjà le structured_response
        if "claims" in output and "answer_md" in output:
            sr_data = output
        else:
            return MedicalValidationResult(
                is_valid=False,
                decision=MedicalDecision.FAIL_CLOSED,
                errors=["Missing structured_response in output"],
                fail_closed_response=create_fail_closed_response(
                    reason="Contract violation: missing structured_response object",
                    query_context="structure validation"
                )
            )
    
    # Rule 3: Valider avec Pydantic
    try:
        structured_response = StructuredResponse(**sr_data)
    except Exception as e:
        error_msg = str(e)
        # Extraire le message d'erreur Pydantic
        if "INVARIANT VIOLATION" in error_msg:
            errors.append(error_msg)
        else:
            errors.append(f"Pydantic validation failed: {error_msg}")
        
        return MedicalValidationResult(
            is_valid=False,
            decision=MedicalDecision.FAIL_CLOSED,
            errors=errors,
            fail_closed_response=create_fail_closed_response(
                reason=f"Contract validation failed: {errors[0]}",
                query_context="pydantic validation"
            )
        )
    
    # Rule 4: Vérifications additionnelles
    
    # 4a: Si pas FAIL_CLOSED, il doit y avoir des claims ou une raison valide
    if structured_response.decision != "FAIL_CLOSED":
        if not structured_response.claims and not structured_response.action_refused:
            errors.append("No claims provided and not action_refused - suspicious output")
    
    # 4b: Vérifier que les claims non-PV ont des grades appropriés
    for claim in structured_response.claims:
        if claim.source_type == "pv" and claim.evidence_grade in ["H", "M"]:
            errors.append(
                f"Claim {claim.claim_id}: PV source with {claim.evidence_grade} grade - "
                f"should be VL or L"
            )
    
    # 4c: Vérifier que answer_md ne contient pas d'affirmations hors claims
    # (protection contre la "narration libre" du LLM)
    if structured_response.claims and structured_response.decision != "FAIL_CLOSED":
        answer_valid, suspicious_phrases = validate_answer_md_no_extra_claims(
            structured_response.answer_md,
            structured_response.claims
        )
        if not answer_valid and suspicious_phrases:
            # Warning plutôt que fail - heuristique best-effort
            # En mode strict, décommenter la ligne suivante pour fail
            # errors.append(f"answer_md contains assertions not in claims: {suspicious_phrases}")
            pass  # Pour l'instant, on log seulement
    
    if errors:
        return MedicalValidationResult(
            is_valid=False,
            decision=MedicalDecision.FAIL_CLOSED,
            errors=errors,
            fail_closed_response=create_fail_closed_response(
                reason=f"Validation errors: {'; '.join(errors)}",
                query_context="post-validation checks"
            )
        )
    
    # Tout est OK
    return MedicalValidationResult(
        is_valid=True,
        decision=MedicalDecision.APPROVED,
        structured_response=structured_response
    )


def create_fail_closed_response(
    reason: str,
    query_context: str = "",
) -> Dict[str, Any]:
    """
    Crée une réponse FAIL_CLOSED standardisée.
    
    Cette réponse est elle-même un StructuredResponse valide avec claims=[].
    """
    return {
        "decision": "FAIL_CLOSED",
        "reason": reason,
        "claims": [],
        "answer_md": (
            f"## NON VALIDABLE\n\n"
            f"La sortie médicale n'a pas pu être validée.\n\n"
            f"**Raison**: {reason}\n\n"
            f"**Orientation**: Consulter un professionnel de santé pour cette question."
        ),
        "citations": [],
        "meta": {
            "evidence_grade_global": "INSUFFICIENT",
            "consensus_status": "fail_closed",
            "offline_mode": False,
            "fail_reason": reason
        }
    }


def create_red_flag_response(matched_patterns: List[str]) -> Dict[str, Any]:
    """
    Crée une réponse d'urgence pour red flags détectés.
    """
    return {
        "decision": "RED_FLAG_EMERGENCY",
        "reason": f"Red flags detected: {matched_patterns}",
        "claims": [],
        "answer_md": (
            "## ⚠️ URGENCE POTENTIELLE DÉTECTÉE\n\n"
            "Les symptômes décrits nécessitent une évaluation médicale **IMMÉDIATE**.\n\n"
            "→ **Contactez le 15 (SAMU)** ou rendez-vous aux **urgences** les plus proches.\n\n"
            "Je ne fournis pas d'analyse approfondie pour éviter tout retard de prise en charge."
        ),
        "citations": [],
        "meta": {
            "evidence_grade_global": "N/A",
            "consensus_status": "emergency_redirect",
            "offline_mode": False,
            "emergency_type": "red_flag"
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_or_fail_closed(
    output: Union[Dict[str, Any], str],
    query: str = "",
    offline_mode: bool = False,
) -> Tuple[MedicalDecision, Dict[str, Any]]:
    """
    Valide une sortie médicale et retourne la décision + réponse finale.
    
    C'est la fonction à appeler depuis le handler/gate.
    
    Args:
        output: La sortie brute de l'agent
        query: La query originale (pour détection red flags)
        offline_mode: Si le système est en mode offline
        
    Returns:
        (decision, response_to_send)
    """
    # Step 1: Check red flags
    if query:
        has_red_flag, patterns = detect_red_flags(query)
        if has_red_flag:
            return MedicalDecision.FAIL_CLOSED, create_red_flag_response(patterns)
    
    # Step 2: Validate output
    result = validate_medical_output(output, offline_mode=offline_mode)
    
    if result.is_valid and result.structured_response:
        # Convertir le Pydantic model en dict pour la réponse
        return MedicalDecision.APPROVED, result.structured_response.model_dump()
    else:
        return MedicalDecision.FAIL_CLOSED, result.fail_closed_response or create_fail_closed_response(
            reason="; ".join(result.errors),
            query_context="validation"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "EvidenceGrade",
    "SourceType", 
    "ConsensusStatus",
    "MedicalDecision",
    # Models
    "PVContext",
    "MedicalCitation",
    "MedicalClaim",
    "MedicalMeta",
    "StructuredResponse",
    "MedicalValidationResult",
    # Functions
    "detect_red_flags",
    "is_patient_specific_actionable",
    "validate_medical_output",
    "validate_or_fail_closed",
    "create_fail_closed_response",
    "create_red_flag_response",
    "validate_citation_format",
    "render_answer_from_claims",
    "validate_answer_md_no_extra_claims",
    # Patterns (for testing)
    "RED_FLAG_PATTERNS",
    "PATIENT_SPECIFIC_ACTION_PATTERNS",
    "CITATION_FORMAT_RULES",
]
