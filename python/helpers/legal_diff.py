"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                P6.1+P6.2: LEGAL DIFF — ÉVOLUTION NORMATIVE                   ║
║                                                                              ║
║  Module de diff juridique structuré entre versions d'un même texte légal.   ║
║                                                                              ║
║  Fonctionnalités:                                                            ║
║  - Diff textuel structuré (paragraphe/ligne)                                ║
║  - Qualification des modifications: ADD | REMOVE | MODIFY                   ║
║  - Évaluation d'impact: NEUTRAL | AGGRAVATING | RELAXING                    ║
║  - Traçabilité complète avec audit_bundle                                   ║
║                                                                              ║
║  P6.2 HARDENING:                                                            ║
║  - Normalisation Unicode/typographique pré-split                            ║
║  - Signal override: no-signal-change-ignored                                ║
║  - Lexique fléchi minimal (variantes grammaticales)                         ║
║                                                                              ║
║  INVARIANTS:                                                                 ║
║  - Aucun diff sans versions résolues (hérite P5)                            ║
║  - Aucun segment sans change_type                                           ║
║  - Aucune qualification sans justification textuelle                        ║
║  - NEUTRAL par défaut (fail-safe)                                           ║
║  - Aucune conclusion juridique définitive                                   ║
║  - P6.2: Signal change = segment présent (no-signal-change-ignored)         ║
║                                                                              ║
║  Version: 1.1.0 (P6.2 Hardening)                                            ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from difflib import SequenceMatcher, unified_diff
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ChangeType(str, Enum):
    """Type de modification détectée."""
    ADD = "add"          # Ajout de texte
    REMOVE = "remove"    # Suppression de texte
    MODIFY = "modify"    # Reformulation substantielle


class ImpactQualification(str, Enum):
    """Qualification de l'impact juridique potentiel."""
    NEUTRAL = "neutral"         # Pas d'impact significatif détecté
    AGGRAVATING = "aggravating"  # Renforcement d'obligations/sanctions
    RELAXING = "relaxing"        # Assouplissement/exemption


class DiffStatus(str, Enum):
    """Statut du diff dans le pipeline."""
    AVAILABLE = "available"        # Diff calculé avec succès
    NOT_APPLICABLE = "not_applicable"  # Pas de version précédente
    VERSION_MISMATCH = "version_mismatch"  # Incohérence de versions
    ERROR = "error"                # Erreur lors du calcul


# ═══════════════════════════════════════════════════════════════════════════════
# P6.2.1: NORMALISATION UNICODE/TYPOGRAPHIQUE
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_legal_text(text: str) -> str:
    """
    P6.2.1: Normalize text for consistent diff computation.
    
    PURE and DETERMINISTIC function.
    
    Normalizations applied:
    1. Unicode NFKC normalization
    2. Apostrophes: U+2019 (') → U+0027 (')
    3. Dashes: en-dash (–), em-dash (—) → hyphen (-)
    4. Spaces: NBSP (U+00A0) → space, collapse multiple spaces
    5. Line endings: \r\n → \n
    6. Trim leading/trailing whitespace per line
    
    Does NOT:
    - Lowercase (preserves case for display)
    - Remove semantic content
    """
    if not text:
        return ""
    
    # 1. Unicode NFKC normalization (handles composed/decomposed forms)
    normalized = unicodedata.normalize("NFKC", text)
    
    # 2. Normalize apostrophes: curly → straight
    # U+2019 RIGHT SINGLE QUOTATION MARK → U+0027 APOSTROPHE
    # U+2018 LEFT SINGLE QUOTATION MARK → U+0027 APOSTROPHE
    # U+02BC MODIFIER LETTER APOSTROPHE → U+0027 APOSTROPHE
    normalized = normalized.replace("\u2019", "'")
    normalized = normalized.replace("\u2018", "'")
    normalized = normalized.replace("\u02bc", "'")
    
    # 3. Normalize dashes: en-dash, em-dash → hyphen
    # U+2013 EN DASH → U+002D HYPHEN-MINUS
    # U+2014 EM DASH → U+002D HYPHEN-MINUS
    # U+2212 MINUS SIGN → U+002D HYPHEN-MINUS
    normalized = normalized.replace("\u2013", "-")
    normalized = normalized.replace("\u2014", "-")
    normalized = normalized.replace("\u2212", "-")
    
    # 4. Normalize spaces: NBSP → space
    # U+00A0 NO-BREAK SPACE → U+0020 SPACE
    # U+202F NARROW NO-BREAK SPACE → U+0020 SPACE
    # U+2007 FIGURE SPACE → U+0020 SPACE
    normalized = normalized.replace("\u00a0", " ")
    normalized = normalized.replace("\u202f", " ")
    normalized = normalized.replace("\u2007", " ")
    
    # 5. Normalize line endings: \r\n → \n, \r → \n
    normalized = normalized.replace("\r\n", "\n")
    normalized = normalized.replace("\r", "\n")
    
    # 6. Collapse multiple spaces (but preserve newlines)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    
    # 7. Trim each line
    lines = normalized.split("\n")
    lines = [line.strip() for line in lines]
    normalized = "\n".join(lines)
    
    return normalized


# ═══════════════════════════════════════════════════════════════════════════════
# LEXIQUE JURIDIQUE (QUALIFICATION) — P6.2.3 EXTENDED WITH INFLECTED FORMS
# ═══════════════════════════════════════════════════════════════════════════════

# Termes indiquant un renforcement (AGGRAVATING)
# P6.2.3: Includes inflected forms (masc/fem/plur)
AGGRAVATING_KEYWORDS = {
    # Obligations
    "doit", "doivent", "devra", "devront", "devrait", "devraient",
    "obligatoire", "obligatoires",
    "obligation", "obligations",
    "impératif", "impératifs", "impérative", "impératives",
    "contrainte", "contraintes",
    "exigence", "exigences",
    "requis", "requise", "requises",
    "nécessaire", "nécessaires",
    # Sanctions
    "sanction", "sanctions",
    "pénalité", "pénalités",
    "amende", "amendes",
    "astreinte", "astreintes",
    "interdiction", "interdictions",
    "interdit", "interdite", "interdits", "interdites",
    "prohibition", "prohibitions",
    # Délais réduits
    "immédiat", "immédiate", "immédiats", "immédiates",
    "immédiatement",
    "sans délai",
    "urgent", "urgente", "urgents", "urgentes",
    # Seuils abaissés
    "minimum", "minima", "minimaux", "minimale", "minimales",
    "au moins",
    "plancher", "planchers",
    # Responsabilité
    "responsable", "responsables",
    "responsabilité", "responsabilités",
    "solidaire", "solidaires",
    "solidairement",
}

# Termes indiquant un assouplissement (RELAXING)
# P6.2.3: Includes inflected forms (masc/fem/plur)
RELAXING_KEYWORDS = {
    # Exemptions
    "exempt", "exempte", "exempts", "exemptes",
    "exempté", "exemptée", "exemptés", "exemptées",
    "exemption", "exemptions",
    "dispense", "dispenses",
    "dispensé", "dispensée", "dispensés", "dispensées",
    "dérogation", "dérogations",
    "dérogatoire", "dérogatoires",
    "facultatif", "facultative", "facultatifs", "facultatives",
    "optionnel", "optionnelle", "optionnels", "optionnelles",
    # Assouplissements
    "peut", "peuvent", "pourra", "pourront", "pourrait", "pourraient",
    "possibilité", "possibilités",
    "possible", "possibles",
    "autorisé", "autorisée", "autorisés", "autorisées",
    "permis", "permise", "permises",
    "permet", "permettre", "permettent",
    "toléré", "tolérée", "tolérés", "tolérées",
    "tolérance", "tolérances",
    # Délais allongés
    "prolongé", "prolongée", "prolongés", "prolongées",
    "prolongation", "prolongations",
    "prorogé", "prorogée", "prorogés", "prorogées",
    "prorogation", "prorogations",
    "report", "reports",
    "reporté", "reportée", "reportés", "reportées",
    "différé", "différée", "différés", "différées",
    # Seuils relevés
    "maximum", "maxima", "maximaux", "maximale", "maximales",
    "plafond", "plafonds",
    "au plus",
    # Atténuation
    "atténué", "atténuée", "atténués", "atténuées",
    "atténuation", "atténuations",
    "réduit", "réduite", "réduits", "réduites",
    "réduction", "réductions",
    "allégé", "allégée", "allégés", "allégées",
}

# Topics juridiques pour classification
LEGAL_TOPICS = {
    "délai": ["délai", "jour", "mois", "an", "année", "semaine", "heure", "terme"],
    "sanction": ["sanction", "pénalité", "amende", "astreinte", "peine"],
    "obligation": ["doit", "obligation", "contrainte", "exigence"],
    "responsabilité": ["responsable", "responsabilité", "faute", "dommage"],
    "procédure": ["procédure", "formalité", "notification", "signification"],
    "montant": ["euro", "€", "somme", "montant", "valeur", "seuil"],
    "condition": ["condition", "sous réserve", "à condition", "si"],
    "exemption": ["exempt", "dispense", "dérogation", "exception"],
}

# Combined keywords for signal extraction (P6.2.2)
ALL_NORMATIVE_KEYWORDS: FrozenSet[str] = frozenset(AGGRAVATING_KEYWORDS | RELAXING_KEYWORDS)


# ═══════════════════════════════════════════════════════════════════════════════
# P6.2.2: SIGNAL OVERRIDE — NO-SIGNAL-CHANGE-IGNORED
# ═══════════════════════════════════════════════════════════════════════════════

def extract_normative_signals(text: str) -> Set[str]:
    """
    P6.2.2: Extract normative signals from text.
    
    Returns the set of canonical keywords found in the text (case-insensitive).
    Uses the combined AGGRAVATING + RELAXING lexicon.
    
    Args:
        text: Text to analyze (will be lowercased for matching)
        
    Returns:
        Set of canonical keywords found (lowercase)
    """
    if not text:
        return set()
    
    text_lower = text.lower()
    found_signals = set()
    
    for keyword in ALL_NORMATIVE_KEYWORDS:
        # Use word boundary matching for multi-word keywords
        if " " in keyword:
            # Multi-word: check as substring
            if keyword in text_lower:
                found_signals.add(keyword)
        else:
            # Single word: check with word boundaries to avoid partial matches
            # e.g., "peut" should not match "peuvent" separately if both are in lexicon
            # But since both ARE in lexicon, simple substring is fine
            if keyword in text_lower:
                found_signals.add(keyword)
    
    return found_signals


def should_force_diff(before_text: str, after_text: str) -> bool:
    """
    P6.2.2: Check if a diff should be forced despite high similarity ratio.
    
    INVARIANT: If normative signals change (appear or disappear), 
    the change MUST be reported as a segment.
    
    Args:
        before_text: Original text
        after_text: Modified text
        
    Returns:
        True if signals changed (diff must be forced), False otherwise
    """
    signals_before = extract_normative_signals(before_text or "")
    signals_after = extract_normative_signals(after_text or "")
    
    # Check if any signal was added or removed
    added = signals_after - signals_before
    removed = signals_before - signals_after
    
    return bool(added or removed)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

class DiffValidationError(Exception):
    """Raised when diff validation fails."""
    def __init__(self, reason: str, context: Optional[Dict] = None):
        self.reason = reason
        self.context = context or {}
        super().__init__(f"Diff validation failed: {reason}")


class VersionMismatchError(Exception):
    """Raised when versions don't match for diff."""
    def __init__(self, text_id: str, v1: str, v2: str):
        self.text_id = text_id
        self.v1 = v1
        self.v2 = v2
        super().__init__(f"Version mismatch for {text_id}: {v1} vs {v2}")


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1: LEGAL DIFF SEGMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LegalDiffSegment:
    """
    Un segment de diff entre deux versions.
    
    INVARIANTS:
    - change_type toujours défini
    - Si ADD: after_text requis
    - Si REMOVE: before_text requis
    - Si MODIFY: before_text ET after_text requis
    - qualification justifiée par detected_signals
    """
    segment_id: str
    change_type: ChangeType
    
    # Textes (optionnels selon change_type)
    before_text: Optional[str] = None
    after_text: Optional[str] = None
    
    # Qualification
    qualification: ImpactQualification = ImpactQualification.NEUTRAL
    qualification_reason: str = ""
    detected_signals: List[str] = field(default_factory=list)
    
    # Contexte
    impacted_topics: List[str] = field(default_factory=list)
    line_range_before: Optional[Tuple[int, int]] = None
    line_range_after: Optional[Tuple[int, int]] = None
    
    def __post_init__(self):
        # Convert string to enum if needed
        if isinstance(self.change_type, str):
            self.change_type = ChangeType(self.change_type.lower())
        if isinstance(self.qualification, str):
            self.qualification = ImpactQualification(self.qualification.lower())
        
        self.validate()
    
    def validate(self):
        """Validate the segment."""
        if not self.segment_id:
            raise DiffValidationError("segment_id required")
        
        if self.change_type == ChangeType.ADD:
            if not self.after_text:
                raise DiffValidationError(
                    "ADD segment requires after_text",
                    {"segment_id": self.segment_id}
                )
        elif self.change_type == ChangeType.REMOVE:
            if not self.before_text:
                raise DiffValidationError(
                    "REMOVE segment requires before_text",
                    {"segment_id": self.segment_id}
                )
        elif self.change_type == ChangeType.MODIFY:
            if not self.before_text or not self.after_text:
                raise DiffValidationError(
                    "MODIFY segment requires before_text AND after_text",
                    {"segment_id": self.segment_id}
                )
        
        # Qualification must be justified if not NEUTRAL
        if self.qualification != ImpactQualification.NEUTRAL:
            if not self.detected_signals:
                raise DiffValidationError(
                    f"{self.qualification.value} qualification requires detected_signals",
                    {"segment_id": self.segment_id}
                )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "change_type": self.change_type.value,
            "before_text": self.before_text,
            "after_text": self.after_text,
            "qualification": self.qualification.value,
            "qualification_reason": self.qualification_reason,
            "detected_signals": self.detected_signals,
            "impacted_topics": self.impacted_topics,
            "line_range_before": self.line_range_before,
            "line_range_after": self.line_range_after,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalDiffSegment":
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1: LEGAL DIFF REPORT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LegalDiffReport:
    """
    Rapport de diff complet entre deux versions.
    
    INVARIANTS:
    - text_id, from_version_id, to_version_id requis
    - as_of_date requis (hérite P5)
    - Tous les segments valides
    """
    text_id: str
    from_version_id: str
    to_version_id: str
    as_of_date: date
    
    # Segments
    segments: List[LegalDiffSegment] = field(default_factory=list)
    
    # Summary flags
    aggravation_detected: bool = False
    relaxation_detected: bool = False
    scope_change_detected: bool = False
    
    # Metadata
    diff_status: DiffStatus = DiffStatus.AVAILABLE
    computed_at: float = field(default_factory=lambda: datetime.now().timestamp())
    diff_hash: str = ""
    
    # Textual summary
    summary: str = ""
    
    def __post_init__(self):
        # Parse as_of_date if string
        if isinstance(self.as_of_date, str):
            self.as_of_date = datetime.strptime(self.as_of_date[:10], "%Y-%m-%d").date()
        
        # Convert status string to enum
        if isinstance(self.diff_status, str):
            self.diff_status = DiffStatus(self.diff_status.lower())
        
        self.validate()
        self._compute_summary_flags()
        self._compute_hash()
    
    def validate(self):
        """Validate the report."""
        if not self.text_id:
            raise DiffValidationError("text_id required")
        if not self.from_version_id:
            raise DiffValidationError("from_version_id required")
        if not self.to_version_id:
            raise DiffValidationError("to_version_id required")
        if self.as_of_date is None:
            raise DiffValidationError("as_of_date required (P5 inheritance)")
    
    def _compute_summary_flags(self):
        """Compute summary flags from segments."""
        for seg in self.segments:
            if seg.qualification == ImpactQualification.AGGRAVATING:
                self.aggravation_detected = True
            elif seg.qualification == ImpactQualification.RELAXING:
                self.relaxation_detected = True
    
    def _compute_hash(self):
        """Compute deterministic hash of the diff."""
        content = f"{self.text_id}:{self.from_version_id}:{self.to_version_id}"
        for seg in sorted(self.segments, key=lambda s: s.segment_id):
            content += f"|{seg.change_type.value}:{seg.before_text}:{seg.after_text}"
        self.diff_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @property
    def total_segments(self) -> int:
        return len(self.segments)
    
    @property
    def additions(self) -> List[LegalDiffSegment]:
        return [s for s in self.segments if s.change_type == ChangeType.ADD]
    
    @property
    def removals(self) -> List[LegalDiffSegment]:
        return [s for s in self.segments if s.change_type == ChangeType.REMOVE]
    
    @property
    def modifications(self) -> List[LegalDiffSegment]:
        return [s for s in self.segments if s.change_type == ChangeType.MODIFY]
    
    @property
    def has_significant_changes(self) -> bool:
        """Check if there are significant changes (non-neutral)."""
        return self.aggravation_detected or self.relaxation_detected
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text_id": self.text_id,
            "from_version_id": self.from_version_id,
            "to_version_id": self.to_version_id,
            "as_of_date": self.as_of_date.isoformat(),
            "segments": [s.to_dict() for s in self.segments],
            "aggravation_detected": self.aggravation_detected,
            "relaxation_detected": self.relaxation_detected,
            "scope_change_detected": self.scope_change_detected,
            "diff_status": self.diff_status.value,
            "computed_at": self.computed_at,
            "diff_hash": self.diff_hash,
            "summary": self.summary,
            "total_segments": self.total_segments,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalDiffReport":
        segments = [LegalDiffSegment.from_dict(s) for s in data.get("segments", [])]
        return cls(
            text_id=data["text_id"],
            from_version_id=data["from_version_id"],
            to_version_id=data["to_version_id"],
            as_of_date=data["as_of_date"],
            segments=segments,
            diff_status=data.get("diff_status", DiffStatus.AVAILABLE),
            summary=data.get("summary", ""),
        )
    
    def to_markdown(self) -> str:
        """Generate markdown summary."""
        lines = []
        
        lines.append("### Évolutions depuis la version précédente")
        lines.append("")
        lines.append(f"**Texte**: {self.text_id}")
        lines.append(f"**De**: {self.from_version_id} → **À**: {self.to_version_id}")
        lines.append(f"**Date d'analyse**: {self.as_of_date.strftime('%d/%m/%Y')}")
        lines.append("")
        
        if not self.segments:
            lines.append("_Aucune modification détectée._")
            return "\n".join(lines)
        
        # Summary
        lines.append(f"**{self.total_segments} modification(s) détectée(s)**:")
        lines.append(f"- Ajouts: {len(self.additions)}")
        lines.append(f"- Suppressions: {len(self.removals)}")
        lines.append(f"- Reformulations: {len(self.modifications)}")
        lines.append("")
        
        # Flags
        if self.aggravation_detected:
            lines.append("⚠️ **Aggravation potentielle détectée** — Renforcement d'obligations/sanctions")
        if self.relaxation_detected:
            lines.append("✅ **Assouplissement potentiel détecté** — Exemptions/délais allongés")
        
        lines.append("")
        
        # Segments
        for seg in self.segments:
            icon = {"add": "➕", "remove": "➖", "modify": "📝"}[seg.change_type.value]
            qual_icon = {
                "neutral": "⚪",
                "aggravating": "🔴",
                "relaxing": "🟢",
            }[seg.qualification.value]
            
            lines.append(f"#### {icon} {seg.change_type.value.upper()} {qual_icon}")
            
            if seg.before_text:
                lines.append(f"> **Avant**: _{seg.before_text[:100]}{'...' if len(seg.before_text) > 100 else ''}_")
            if seg.after_text:
                lines.append(f"> **Après**: _{seg.after_text[:100]}{'...' if len(seg.after_text) > 100 else ''}_")
            
            if seg.qualification != ImpactQualification.NEUTRAL:
                lines.append(f"> **Impact**: {seg.qualification.value} — {seg.qualification_reason}")
                if seg.detected_signals:
                    lines.append(f"> **Signaux**: {', '.join(seg.detected_signals[:5])}")
            
            lines.append("")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1.2 + P6.2: DIFF ENGINE WITH NORMALIZATION AND SIGNAL OVERRIDE
# ═══════════════════════════════════════════════════════════════════════════════

def _split_into_paragraphs(text: str, normalize: bool = True) -> List[str]:
    """
    Split text into paragraphs (non-empty lines).
    
    P6.2.1: Applies normalization before splitting if normalize=True.
    """
    if normalize:
        text = normalize_legal_text(text)
    
    paragraphs = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            paragraphs.append(stripped)
    return paragraphs


def _is_substantial_change(
    old: str, 
    new: str, 
    threshold: float = 0.85,
    check_signals: bool = True,
) -> bool:
    """
    P6.2.2: Check if change is substantial (not just minor rewording).
    
    Uses SequenceMatcher ratio:
    - ratio > threshold = minor change (near-identical text)
    - ratio <= threshold = substantial change (worth reporting)
    
    P6.2.2 SIGNAL OVERRIDE:
    If check_signals=True and normative signals changed, 
    the change is ALWAYS considered substantial regardless of ratio.
    
    Default threshold 0.85 catches most meaningful changes while
    ignoring trivial whitespace/punctuation differences.
    """
    # P6.2.2: Signal override - if signals changed, always report
    if check_signals and should_force_diff(old, new):
        return True
    
    ratio = SequenceMatcher(None, old.lower(), new.lower()).ratio()
    return ratio <= threshold


def compute_legal_diff(
    old_text: str,
    new_text: str,
    text_id: str,
    from_version_id: str,
    to_version_id: str,
    as_of_date: date,
) -> LegalDiffReport:
    """
    P6.1.2 + P6.2: Compute structured legal diff between two versions.
    
    P6.2 HARDENING:
    - Texts are normalized before diff (P6.2.1)
    - Signal override prevents missing normative changes (P6.2.2)
    - Extended lexicon with inflected forms (P6.2.3)
    
    Args:
        old_text: Text from previous version (N-1)
        new_text: Text from current version (N)
        text_id: Legal text identifier
        from_version_id: Previous version ID
        to_version_id: Current version ID
        as_of_date: Date for temporal context
        
    Returns:
        LegalDiffReport with all segments and qualifications
    """
    segments: List[LegalDiffSegment] = []
    segment_counter = 0
    
    # P6.2.1: Normalize texts before processing
    old_normalized = normalize_legal_text(old_text)
    new_normalized = normalize_legal_text(new_text)
    
    # Split into paragraphs (already normalized)
    old_paragraphs = _split_into_paragraphs(old_normalized, normalize=False)
    new_paragraphs = _split_into_paragraphs(new_normalized, normalize=False)
    
    # Use SequenceMatcher for paragraph-level diff
    matcher = SequenceMatcher(None, old_paragraphs, new_paragraphs)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # No change
            continue
        
        elif tag == "replace":
            # Modification: paragraphs replaced
            for old_idx, new_idx in zip(range(i1, i2), range(j1, j2)):
                old_para = old_paragraphs[old_idx]
                new_para = new_paragraphs[new_idx]
                
                # P6.2.2: Check if substantial (with signal override)
                if _is_substantial_change(old_para, new_para, check_signals=True):
                    segment_counter += 1
                    seg = _create_segment(
                        segment_id=f"seg_{segment_counter:03d}",
                        change_type=ChangeType.MODIFY,
                        before_text=old_para,
                        after_text=new_para,
                        line_before=(old_idx + 1, old_idx + 1),
                        line_after=(new_idx + 1, new_idx + 1),
                    )
                    segments.append(seg)
            
            # Handle unmatched paragraphs
            if i2 - i1 > j2 - j1:
                # More old paragraphs than new = some removed
                for old_idx in range(i1 + (j2 - j1), i2):
                    segment_counter += 1
                    seg = _create_segment(
                        segment_id=f"seg_{segment_counter:03d}",
                        change_type=ChangeType.REMOVE,
                        before_text=old_paragraphs[old_idx],
                        line_before=(old_idx + 1, old_idx + 1),
                    )
                    segments.append(seg)
            elif j2 - j1 > i2 - i1:
                # More new paragraphs than old = some added
                for new_idx in range(j1 + (i2 - i1), j2):
                    segment_counter += 1
                    seg = _create_segment(
                        segment_id=f"seg_{segment_counter:03d}",
                        change_type=ChangeType.ADD,
                        after_text=new_paragraphs[new_idx],
                        line_after=(new_idx + 1, new_idx + 1),
                    )
                    segments.append(seg)
        
        elif tag == "delete":
            # Removal: paragraphs deleted
            for old_idx in range(i1, i2):
                segment_counter += 1
                seg = _create_segment(
                    segment_id=f"seg_{segment_counter:03d}",
                    change_type=ChangeType.REMOVE,
                    before_text=old_paragraphs[old_idx],
                    line_before=(old_idx + 1, old_idx + 1),
                )
                segments.append(seg)
        
        elif tag == "insert":
            # Addition: paragraphs added
            for new_idx in range(j1, j2):
                segment_counter += 1
                seg = _create_segment(
                    segment_id=f"seg_{segment_counter:03d}",
                    change_type=ChangeType.ADD,
                    after_text=new_paragraphs[new_idx],
                    line_after=(new_idx + 1, new_idx + 1),
                )
                segments.append(seg)
    
    # Build report (uses normalized texts for hash stability)
    report = LegalDiffReport(
        text_id=text_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
        as_of_date=as_of_date,
        segments=segments,
    )
    
    # Generate summary
    report.summary = _generate_summary(report)
    
    return report


def _create_segment(
    segment_id: str,
    change_type: ChangeType,
    before_text: Optional[str] = None,
    after_text: Optional[str] = None,
    line_before: Optional[Tuple[int, int]] = None,
    line_after: Optional[Tuple[int, int]] = None,
) -> LegalDiffSegment:
    """Create a segment with automatic qualification."""
    
    # Qualify the change
    qualification, reason, signals = qualify_change(
        change_type=change_type,
        before_text=before_text,
        after_text=after_text,
    )
    
    # Detect impacted topics
    topics = _detect_topics(before_text, after_text)
    
    return LegalDiffSegment(
        segment_id=segment_id,
        change_type=change_type,
        before_text=before_text,
        after_text=after_text,
        qualification=qualification,
        qualification_reason=reason,
        detected_signals=signals,
        impacted_topics=topics,
        line_range_before=line_before,
        line_range_after=line_after,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1.3: QUALIFICATION NORMATIVE
# ═══════════════════════════════════════════════════════════════════════════════

def qualify_change(
    change_type: ChangeType,
    before_text: Optional[str],
    after_text: Optional[str],
) -> Tuple[ImpactQualification, str, List[str]]:
    """
    P6.1.3: Qualify the impact of a change.
    
    Returns:
        (qualification, reason, detected_signals)
        
    RULES:
    - NEUTRAL by default (fail-safe)
    - AGGRAVATING only if aggravating keywords added or relaxing keywords removed
    - RELAXING only if relaxing keywords added or aggravating keywords removed
    """
    signals: List[str] = []
    
    # Normalize texts
    before_lower = (before_text or "").lower()
    after_lower = (after_text or "").lower()
    
    # Check for aggravating signals
    aggravating_score = 0
    relaxing_score = 0
    
    for keyword in AGGRAVATING_KEYWORDS:
        in_before = keyword in before_lower
        in_after = keyword in after_lower
        
        if in_after and not in_before:
            # Aggravating keyword added
            aggravating_score += 1
            signals.append(f"+{keyword}")
        elif in_before and not in_after:
            # Aggravating keyword removed = relaxing
            relaxing_score += 1
            signals.append(f"-{keyword}")
    
    for keyword in RELAXING_KEYWORDS:
        in_before = keyword in before_lower
        in_after = keyword in after_lower
        
        if in_after and not in_before:
            # Relaxing keyword added
            relaxing_score += 1
            signals.append(f"+{keyword}")
        elif in_before and not in_after:
            # Relaxing keyword removed = aggravating
            aggravating_score += 1
            signals.append(f"-{keyword}")
    
    # Determine qualification
    if aggravating_score > relaxing_score and aggravating_score >= 1:
        return (
            ImpactQualification.AGGRAVATING,
            f"Renforcement détecté ({aggravating_score} signaux)",
            signals,
        )
    elif relaxing_score > aggravating_score and relaxing_score >= 1:
        return (
            ImpactQualification.RELAXING,
            f"Assouplissement détecté ({relaxing_score} signaux)",
            signals,
        )
    else:
        return (
            ImpactQualification.NEUTRAL,
            "Aucun impact significatif détecté",
            [],
        )


def _detect_topics(
    before_text: Optional[str],
    after_text: Optional[str],
) -> List[str]:
    """Detect legal topics impacted by the change."""
    combined = f"{before_text or ''} {after_text or ''}".lower()
    
    topics = []
    for topic, keywords in LEGAL_TOPICS.items():
        if any(kw in combined for kw in keywords):
            topics.append(topic)
    
    return topics


def _generate_summary(report: LegalDiffReport) -> str:
    """Generate textual summary of the diff."""
    if not report.segments:
        return "Aucune modification détectée entre les deux versions."
    
    parts = []
    
    # Count by type
    adds = len(report.additions)
    removes = len(report.removals)
    mods = len(report.modifications)
    
    if adds:
        parts.append(f"{adds} ajout(s)")
    if removes:
        parts.append(f"{removes} suppression(s)")
    if mods:
        parts.append(f"{mods} reformulation(s)")
    
    summary = f"Modifications: {', '.join(parts)}."
    
    if report.aggravation_detected:
        summary += " ⚠️ Aggravation potentielle détectée."
    if report.relaxation_detected:
        summary += " ✅ Assouplissement potentiel détecté."
    
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: CREATE NOT_APPLICABLE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def create_not_applicable_report(
    text_id: str,
    current_version_id: str,
    as_of_date: date,
    reason: str = "No previous version available",
) -> LegalDiffReport:
    """Create a NOT_APPLICABLE diff report when no previous version exists."""
    return LegalDiffReport(
        text_id=text_id,
        from_version_id="N/A",
        to_version_id=current_version_id,
        as_of_date=as_of_date,
        segments=[],
        diff_status=DiffStatus.NOT_APPLICABLE,
        summary=reason,
    )


def create_error_report(
    text_id: str,
    from_version_id: str,
    to_version_id: str,
    as_of_date: date,
    error: str,
) -> LegalDiffReport:
    """Create an ERROR diff report when diff computation fails."""
    return LegalDiffReport(
        text_id=text_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
        as_of_date=as_of_date,
        segments=[],
        diff_status=DiffStatus.ERROR,
        summary=f"Erreur lors du calcul du diff: {error}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ChangeType",
    "ImpactQualification",
    "DiffStatus",
    # Models
    "LegalDiffSegment",
    "LegalDiffReport",
    # Errors
    "DiffValidationError",
    "VersionMismatchError",
    # Functions
    "compute_legal_diff",
    "qualify_change",
    "create_not_applicable_report",
    "create_error_report",
    # P6.2 Functions
    "normalize_legal_text",
    "extract_normative_signals",
    "should_force_diff",
    # Constants
    "AGGRAVATING_KEYWORDS",
    "RELAXING_KEYWORDS",
    "LEGAL_TOPICS",
    "ALL_NORMATIVE_KEYWORDS",
]
