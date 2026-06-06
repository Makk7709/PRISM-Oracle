"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CONTRACT DRAFTING GUARDED — DATA MODELS                           ║
║                                                                              ║
║  Dataclasses et enums pour le pipeline de rédaction contractuelle.           ║
║                                                                              ║
║  FindingSeverity : P0 (bloquant) / P1 (avertissement) / P2 (info)          ║
║  GateVerdictEnum : APPROVE / REJECT                                         ║
║  ContractSection  : CP, CG, ANNEXE_1..ANNEXE_6                             ║
║  LeakFinding     : Résultat d'un scan du Act Leak Guard                    ║
║  ContractDraft   : Le brouillon complet (sections + variables + metadata)   ║
║  GateVerdict     : Résultat de la gate d'audit                             ║
║  DraftingOutput  : Sortie finale du pipeline                                ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class FindingSeverity(Enum):
    """Sévérité des findings du Act Leak Guard et de la Gate.
    
    P0 = BLOQUANT  — empêche la release (fail-closed)
    P1 = WARNING   — signalé mais n'empêche pas la release
    P2 = INFO      — suggestion d'amélioration
    """
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class GateVerdictEnum(Enum):
    """Verdict de la gate d'audit.
    
    APPROVE = le contrat peut être présenté (avec warnings éventuels)
    REJECT  = le contrat ne doit PAS être présenté (P0 ou disclaimer absent)
    """
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ContractSection(Enum):
    """Sections d'un contrat de licence ON-PREM.
    
    CP       = Conditions Particulières
    CG       = Conditions Générales
    ANNEXE_1 = Description du logiciel + modules + limites
    ANNEXE_2 = Support/maintenance + niveaux de service (SLA)
    ANNEXE_3 = Sécurité (accès support, journalisation)
    ANNEXE_4 = DPA RGPD (art. 28) — conditionnel
    ANNEXE_5 = Réversibilité / fin de contrat
    ANNEXE_6 = Grille tarifaire + pénalités
    """
    CP = "CP"
    CG = "CG"
    ANNEXE_1 = "ANNEXE_1"
    ANNEXE_2 = "ANNEXE_2"
    ANNEXE_3 = "ANNEXE_3"
    ANNEXE_4 = "ANNEXE_4"
    ANNEXE_5 = "ANNEXE_5"
    ANNEXE_6 = "ANNEXE_6"


# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LeakFinding:
    """Résultat d'un scan de clause dangereuse.
    
    Attributes:
        severity:       Sévérité (P0 = bloquant, P1 = warning, P2 = info)
        pattern:        Le motif détecté (ex: "remise du code")
        context:        L'extrait de texte où le motif a été trouvé
        recommendation: Recommandation de correction
        section:        La section du contrat concernée (ex: "CG", "ANNEXE_5")
        legal_ref:      Référence légale (ex: "Art. L.122-6-1 CPI") — optionnel
    """
    severity: FindingSeverity
    pattern: str
    context: str
    recommendation: str
    section: str
    legal_ref: str = ""


@dataclass
class ContractDraft:
    """Brouillon de contrat complet.
    
    Attributes:
        sections:       Dict section_name → texte (ex: {"CP": "...", "CG": "..."})
        variables:      Variables injectées dans les templates
        disclaimer:     Mention "PROJET — à valider par un juriste"
        correlation_id: Identifiant de traçabilité
    """
    sections: Dict[str, str]
    variables: Dict[str, str] = field(default_factory=dict)
    disclaimer: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class GateVerdict:
    """Résultat de la gate d'audit.
    
    INVARIANT: can_release = True ⟺ verdict = APPROVE
    INVARIANT: P0 trouvé ⟹ verdict = REJECT, can_release = False
    
    Attributes:
        verdict:     APPROVE ou REJECT
        findings:    Liste des findings (P0, P1, P2)
        can_release: Si le contrat peut être présenté à l'utilisateur
        summary:     Résumé textuel du verdict
    """
    verdict: GateVerdictEnum
    findings: List[LeakFinding] = field(default_factory=list)
    can_release: bool = False
    summary: str = ""

    def has_p0(self) -> bool:
        """Retourne True si au moins un finding P0 est présent."""
        return any(f.severity == FindingSeverity.P0 for f in self.findings)

    def has_p1(self) -> bool:
        """Retourne True si au moins un finding P1 est présent."""
        return any(f.severity == FindingSeverity.P1 for f in self.findings)

    def p0_count(self) -> int:
        """Nombre de findings P0."""
        return sum(1 for f in self.findings if f.severity == FindingSeverity.P0)

    def p1_count(self) -> int:
        """Nombre de findings P1."""
        return sum(1 for f in self.findings if f.severity == FindingSeverity.P1)

    def to_audit_report(self) -> str:
        """Génère un rapport d'audit structuré.
        
        Format:
            ══════ AUDIT CONTRACTUEL — LEGAL_SAFE GATE ══════
            Verdict: APPROVE / REJECT
            P0: N | P1: N | P2: N
            
            [P0] pattern — section
              Contexte: ...
              Recommandation: ...
              Réf. légale: ...
            ...
        
        Returns:
            str — rapport d'audit textuel
        """
        lines = [
            "══════════════════════════════════════════════════════",
            "        AUDIT CONTRACTUEL — LEGAL_SAFE GATE          ",
            "══════════════════════════════════════════════════════",
            f"Verdict: {self.verdict.value}",
            f"P0: {self.p0_count()} | P1: {self.p1_count()} | "
            f"P2: {sum(1 for f in self.findings if f.severity == FindingSeverity.P2)}",
            f"Can release: {'OUI' if self.can_release else 'NON'}",
            "",
        ]
        
        for finding in self.findings:
            lines.append(
                f"[{finding.severity.value}] {finding.pattern} — "
                f"Section: {finding.section}"
            )
            if finding.context:
                ctx = finding.context[:120]
                lines.append(f"  Contexte: {ctx}")
            lines.append(f"  Recommandation: {finding.recommendation}")
            if finding.legal_ref:
                lines.append(f"  Réf. légale: {finding.legal_ref}")
            lines.append("")
        
        if not self.findings:
            lines.append("Aucun finding détecté.")
            lines.append("")
        
        lines.append("══════════════════════════════════════════════════════")
        return "\n".join(lines)


@dataclass
class DraftingOutput:
    """Sortie finale du pipeline de rédaction contractuelle.
    
    Attributes:
        draft:             Le brouillon complet
        gate_verdict:      Le verdict de la gate
        gate_passed:       Si la gate a approuvé
        gate_summary:      Résumé de la gate
        rendered_contract: Le texte final rendu (sections concaténées)
        corrections_needed: Liste des corrections requises (si gate rejetée)
    """
    draft: ContractDraft
    gate_verdict: GateVerdict
    gate_passed: bool
    gate_summary: str
    rendered_contract: str = ""
    corrections_needed: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE VERSIONING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TemplateVersion:
    """Métadonnées de versioning d'un template contractuel.
    
    Chaque template DOIT avoir:
      - Un identifiant unique (section)
      - Un numéro de version sémantique
      - Une date de dernière revue juridique
      - Le nom du relecteur juridique
      - Un changelog des modifications
    
    RÈGLE: Un template sans revue juridique datant de > 12 mois
    est considéré STALE et déclenche un P1 à la gate.
    """
    section: str
    version: str
    last_review_date: date
    reviewer: str
    changelog: List[str] = field(default_factory=list)
    legal_basis: str = ""
    stale_threshold_days: int = 365

    def is_stale(self) -> bool:
        """Retourne True si le template n'a pas été revu depuis > stale_threshold_days."""
        delta = date.today() - self.last_review_date
        return delta.days > self.stale_threshold_days

    def days_since_review(self) -> int:
        """Nombre de jours depuis la dernière revue juridique."""
        return (date.today() - self.last_review_date).days


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VariableValidationResult:
    """Résultat de la validation des variables d'entrée.
    
    INVARIANT: is_valid = False ⟹ le pipeline DOIT refuser de générer.
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_variables: Dict[str, str] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DraftAuditEntry:
    """Entrée de journal d'audit pour chaque opération du pipeline.
    
    Traçabilité complète: qui, quoi, quand, résultat.
    """
    correlation_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    action: str = ""
    details: str = ""
    verdict: str = ""
    findings_count: int = 0
    template_versions: Dict[str, str] = field(default_factory=dict)
    variables_hash: str = ""
    success: bool = True
    error: str = ""
