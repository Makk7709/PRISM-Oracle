"""
ComplianceGrid — Grille de conformite AI Act / RGPD pour rapports Evidence.

Evalue honnetement la conformite de chaque session par rapport aux articles
applicables du Reglement AI Act (2024/1689) et du RGPD.

PRINCIPE FONDAMENTAL : pas de "compliance washing".
- CONFORME = toutes les exigences de l'article sont satisfaites, preuves a l'appui.
- PARTIEL = certaines exigences sont couvertes, d'autres manquent. Detail explicite.
- NON_CONFORME = aucune exigence couverte.
- NON_APPLICABLE = l'article ne s'applique pas a cette session (ex: pas de risque eleve).

Chaque ComplianceCheck porte :
- article : reference normative
- exigence : ce que l'article exige (en clair)
- status : statut honnete
- evidence : preuve technique factuelle (ce qui EXISTE dans le code)
- gaps : ce qui MANQUE pour etre pleinement conforme
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.session_envelope import SessionEnvelope
    from python.helpers.pipeline_tracker import PipelineTracker
    from python.helpers.router.routing_contract import RouteDecision

logger = logging.getLogger("compliance_grid")


class ComplianceStatus(str, Enum):
    """Statut de conformite — honnete, pas binaire."""
    CONFORME = "conforme"
    PARTIEL = "partiel"
    NON_CONFORME = "non_conforme"
    NON_APPLICABLE = "non_applicable"


@dataclass
class ComplianceCheck:
    """Resultat d'evaluation d'un article reglementaire."""
    article: str
    exigence: str
    status: ComplianceStatus
    evidence: str
    gaps: str = ""

    def to_dict(self) -> dict:
        result = {
            "article": self.article,
            "exigence": self.exigence,
            "status": self.status.value,
            "evidence": self.evidence,
        }
        if self.gaps:
            result["gaps"] = self.gaps
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATEURS PAR ARTICLE
# ═══════════════════════════════════════════════════════════════════════════════

def _evaluate_art13_transparency(
    envelope: Optional["SessionEnvelope"],
    tracker: Optional["PipelineTracker"],
    has_narrative: bool = False,
) -> ComplianceCheck:
    """
    Art. 13 AI Act — Transparence.
    Exige que les utilisateurs puissent comprendre le fonctionnement du systeme.

    CE QUI EXISTE : TraceStep structure (reasoning_engine), sanitized actions/outcomes,
    session_id traçable, pipeline_tracker avec agents actives et durees.
    SESSION 14 : section « Transparence du raisonnement » avec narratif non-technique.
    """
    evidence_parts = []
    has_session_id = envelope is not None and envelope.session_id is not None
    has_tracker = tracker is not None and len(tracker.get_activated()) > 0
    has_integrity = envelope is not None and envelope.integrity_hash is not None

    if has_session_id:
        evidence_parts.append(f"Session tracable (ID: {envelope.session_id})")
    if has_tracker:
        activated = tracker.get_activated()
        evidence_parts.append(
            f"Pipeline trace : {len(activated)} agent(s) actives avec durees"
        )
    if has_integrity:
        evidence_parts.append("Hash d'integrite session calcule (SHA-256)")

    evidence_parts.append(
        "TraceStep structure dans reasoning_engine "
        "(action/outcome sanitises, CoT non expose)"
    )

    if has_narrative:
        evidence_parts.append(
            "Section 'Transparence du raisonnement' presente dans le rapport : "
            "narratif en langage non technique (agents consultes, durees, "
            "validation, confiance) sans exposition de CoT ni de prompts internes"
        )

    gaps_parts = []
    if not has_narrative:
        gaps_parts.append(
            "Export utilisateur non-technique incomplet : to_safe_dict() "
            "n'expose que le nombre d'etapes, pas le contenu des traces. "
            "Art. 13 exige que les utilisateurs puissent COMPRENDRE le fonctionnement."
        )

    gaps = " ".join(gaps_parts)

    if has_session_id and has_tracker and has_narrative:
        return ComplianceCheck(
            article="Art. 13 AI Act (2024/1689)",
            exigence="Transparence : les utilisateurs doivent pouvoir comprendre "
                     "le fonctionnement du systeme IA",
            status=ComplianceStatus.CONFORME,
            evidence="; ".join(evidence_parts),
            gaps=gaps,
        )

    if has_session_id and has_tracker:
        return ComplianceCheck(
            article="Art. 13 AI Act (2024/1689)",
            exigence="Transparence : les utilisateurs doivent pouvoir comprendre "
                     "le fonctionnement du systeme IA",
            status=ComplianceStatus.PARTIEL,
            evidence="; ".join(evidence_parts),
            gaps=gaps if gaps else (
                "Export utilisateur non-technique incomplet : "
                "Art. 13 exige que les utilisateurs puissent COMPRENDRE le fonctionnement."
            ),
        )

    return ComplianceCheck(
        article="Art. 13 AI Act (2024/1689)",
        exigence="Transparence : les utilisateurs doivent pouvoir comprendre "
                 "le fonctionnement du systeme IA",
        status=ComplianceStatus.NON_CONFORME,
        evidence="Aucune trace de session disponible" if not evidence_parts
                 else "; ".join(evidence_parts),
        gaps=gaps if gaps else (
            "Export utilisateur non-technique incomplet : "
            "Art. 13 exige que les utilisateurs puissent COMPRENDRE le fonctionnement."
        ),
    )


def _evaluate_art14_human_supervision(
    envelope: Optional["SessionEnvelope"],
    has_human_review_flag: bool = False,
    human_reviewer: Optional[str] = None,
) -> ComplianceCheck:
    """
    Art. 14 AI Act — Supervision humaine.
    Exige que le systeme puisse etre supervise par des humains.

    CE QUI EXISTE : requires_human_review flag dans legal_safe_mode,
    escalation EscalationType.HUMAN_REVIEW dans reasoning_engine,
    human_review_threshold dans metacognition.
    CE QUI MANQUE : registre de supervision (identite du superviseur,
    horodatage de la decision, signature).
    """
    evidence_parts = [
        "Mecanisme d'escalation vers revue humaine (requires_human_review, "
        "EscalationType.HUMAN_REVIEW, metacognition threshold)"
    ]

    if has_human_review_flag:
        evidence_parts.append("Revue humaine DECLENCHEE pour cette session")
        if human_reviewer:
            evidence_parts.append(f"Superviseur : {human_reviewer}")

        return ComplianceCheck(
            article="Art. 14 AI Act (2024/1689)",
            exigence="Supervision humaine : le systeme doit pouvoir etre "
                     "effectivement supervise par des personnes physiques",
            status=ComplianceStatus.PARTIEL,
            evidence="; ".join(evidence_parts),
            gaps="Pas de registre formel de supervision (identite verificable, "
                 "horodatage de decision, signature electronique)",
        )

    return ComplianceCheck(
        article="Art. 14 AI Act (2024/1689)",
        exigence="Supervision humaine : le systeme doit pouvoir etre "
                 "effectivement supervise par des personnes physiques",
        status=ComplianceStatus.PARTIEL,
        evidence="; ".join(evidence_parts),
        gaps="Revue humaine non declenchee pour cette session. "
             "Mecanisme existe mais pas active. "
             "Registre formel de supervision absent.",
    )


def _evaluate_art17_quality_system(
    envelope: Optional["SessionEnvelope"],
    tracker: Optional["PipelineTracker"],
    has_consensus: bool = False,
    has_risk_register: bool = False,
    has_processing_register: bool = False,
) -> ComplianceCheck:
    """
    Art. 17 AI Act — Systeme de gestion de la qualite.
    Exige un QMS complet : versionning, logs, monitoring post-deploiement,
    gestion des donnees, procedures de correction.

    SESSION 15: enrichi avec les metriques de monitoring S10 et les registres.
    """
    evidence_parts = []

    if envelope and envelope.integrity_hash:
        evidence_parts.append("Hash d'integrite session (SHA-256)")

    if envelope and envelope.evidence_version and envelope.evidence_version != "unknown":
        evidence_parts.append(f"Version logicielle tracee ({envelope.evidence_version})")

    if tracker and len(tracker.get_activated()) > 0:
        evidence_parts.append("Pipeline d'agents trace avec durees")

    if has_consensus:
        evidence_parts.append("Consensus PRISM multi-LLM active")

    evidence_parts.append("Logs structures (LegalPipelineLog, audit_retention_days=90)")

    evidence_parts.append(
        "Monitoring post-deploiement : compteurs d'observabilite "
        "(audit_reports_generated_total, audit_report_generation_ms_total, "
        "audit_report_size_bytes_total, audit_report_errors_total)"
    )

    if has_risk_register:
        evidence_parts.append(
            "Registre des risques (Art. 9) integre — gestion documentee "
            "des risques par domaine avec mesures d'attenuation"
        )
    if has_processing_register:
        evidence_parts.append(
            "Registre des traitements (Art. 30 RGPD) integre — "
            "gestion documentee des activites de traitement"
        )

    gaps_list = []

    if not (envelope and envelope.evidence_version and envelope.evidence_version != "unknown"):
        gaps_list.append("Version logicielle non resolue")

    gaps_list.append("Gestion formelle des donnees d'entrainement non implementee")
    gaps_list.append(
        "Procedures de correction documentees partielles "
        "(FAIL_CLOSED existe, pas de workflow formel de correction)"
    )

    all_quality_components = [
        envelope and envelope.integrity_hash,
        envelope and envelope.evidence_version and envelope.evidence_version != "unknown",
        True,  # logs structures
        True,  # monitoring S10
        has_risk_register,
        has_processing_register,
    ]
    covered = sum(1 for c in all_quality_components if c)

    if covered >= 5 and not gaps_list:
        status = ComplianceStatus.CONFORME
    else:
        status = ComplianceStatus.PARTIEL

    return ComplianceCheck(
        article="Art. 17 AI Act (2024/1689)",
        exigence="Systeme de gestion de la qualite : versionning, logs, "
                 "monitoring, gestion des donnees, procedures de correction",
        status=status,
        evidence="; ".join(evidence_parts),
        gaps="; ".join(gaps_list) if gaps_list else "",
    )


def _evaluate_art9_risk_management(
    envelope: Optional["SessionEnvelope"],
    route_decision: Optional["RouteDecision"] = None,
    confidence_score: Optional[float] = None,
    has_risk_register: bool = False,
) -> ComplianceCheck:
    """
    Art. 9 AI Act — Systeme de gestion des risques.
    Exige : identification, estimation, evaluation des risques,
    mesures d'attenuation, monitoring continu.

    SESSION 15: enrichi avec le registre formel des risques (RiskRegister).
    """
    evidence_parts = []

    if confidence_score is not None:
        evidence_parts.append(f"Score de confiance calcule ({confidence_score:.2f})")

    if route_decision is not None:
        if route_decision.ai_act_category:
            evidence_parts.append(
                f"Categorie AI Act evaluee ({route_decision.ai_act_category.value})"
            )
        if route_decision.data_sensitivity:
            evidence_parts.append(
                f"Sensibilite des donnees classifiee ({route_decision.data_sensitivity.value})"
            )

    evidence_parts.append(
        "CriticalityRouter : evaluation automatique du risque par domaine/profil"
    )
    evidence_parts.append(
        "Consensus PRISM obligatoire pour profils critiques "
        "(legal_safe, researcher, medical)"
    )

    if has_risk_register:
        evidence_parts.append(
            "Registre formel des risques present : 7 risques identifies par domaine, "
            "impact estime, mesures d'attenuation documentees, monitoring reference"
        )

    gaps_parts = []
    if not has_risk_register:
        gaps_parts.append("Registre formel des risques absent")
        gaps_parts.append("Mesures d'attenuation non documentees formellement")

    gaps_parts.append("Cycle d'evaluation periodique non implemente (revue manuelle)")

    has_identification = has_risk_register
    has_estimation = confidence_score is not None or (
        route_decision is not None and route_decision.ai_act_category is not None
    )
    has_mitigation = has_risk_register
    has_monitoring = True  # CriticalityRouter + confidence scores

    all_components = [has_identification, has_estimation, has_mitigation, has_monitoring]
    covered = sum(1 for c in all_components if c)

    if covered >= 4 and has_risk_register and len(gaps_parts) <= 1:
        status = ComplianceStatus.CONFORME
    elif covered >= 2:
        status = ComplianceStatus.PARTIEL
    else:
        status = ComplianceStatus.PARTIEL

    return ComplianceCheck(
        article="Art. 9 AI Act (2024/1689)",
        exigence="Systeme de gestion des risques : identification, estimation, "
                 "evaluation, attenuation, monitoring continu",
        status=status,
        evidence="; ".join(evidence_parts),
        gaps="; ".join(gaps_parts),
    )


def _evaluate_rgpd_art30(
    envelope: Optional["SessionEnvelope"],
    has_processing_register: bool = False,
) -> ComplianceCheck:
    """
    RGPD Art. 30 — Registre des activites de traitement.
    Exige : finalites, categories de personnes, destinataires,
    transferts, delais d'effacement, mesures de securite.

    SESSION 15: enrichi avec le ProcessingRegister formel.
    """
    evidence_parts = []

    if envelope:
        if envelope.username:
            evidence_parts.append(f"Utilisateur identifie ({envelope.username})")
        if envelope.organization:
            evidence_parts.append(f"Organisation identifiee ({envelope.organization})")
        if envelope.started_at:
            evidence_parts.append("Horodatage de traitement enregistre")
        if envelope.integrity_hash:
            evidence_parts.append("Hash d'integrite session")

    evidence_parts.append("Retention audit configurable (audit_retention_days=90)")

    if has_processing_register:
        evidence_parts.append(
            "Registre formel Art. 30 present : finalites, base legale, "
            "categories de donnees et personnes, destinataires, "
            "transferts (aucun hors UE), delais de retention, "
            "mesures de securite, DPO designe"
        )

    has_some_metadata = envelope is not None and (
        envelope.username or envelope.organization or envelope.started_at
    )

    if has_processing_register and has_some_metadata:
        return ComplianceCheck(
            article="RGPD Art. 30 (2016/679)",
            exigence="Registre des activites de traitement : finalites, categories, "
                     "destinataires, transferts, delais, mesures de securite",
            status=ComplianceStatus.CONFORME,
            evidence="; ".join(evidence_parts),
            gaps="",
        )

    gaps_parts = []
    if not has_processing_register:
        gaps_parts.append(
            "Registre formel Art. 30 absent : finalites du traitement, "
            "categories de personnes concernees, destinataires des donnees, "
            "transferts hors UE, delais d'effacement prevus, mesures de securite "
            "techniques et organisationnelles, DPO non designe"
        )

    return ComplianceCheck(
        article="RGPD Art. 30 (2016/679)",
        exigence="Registre des activites de traitement : finalites, categories, "
                 "destinataires, transferts, delais, mesures de securite",
        status=ComplianceStatus.PARTIEL if has_some_metadata
               else ComplianceStatus.NON_CONFORME,
        evidence="; ".join(evidence_parts) if evidence_parts
                 else "Aucune metadonnee de traitement enregistree",
        gaps="; ".join(gaps_parts) if gaps_parts else "",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GRILLE COMPLETE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ComplianceGrid:
    """
    Grille de conformite aggregee pour une session Evidence.

    Usage :
        grid = ComplianceGrid.evaluate(
            envelope=session_envelope,
            tracker=pipeline_tracker,
            route_decision=route_decision,
        )
        print(grid.to_report_table())
    """
    checks: List[ComplianceCheck] = field(default_factory=list)

    @classmethod
    def evaluate(
        cls,
        envelope: Optional["SessionEnvelope"] = None,
        tracker: Optional["PipelineTracker"] = None,
        route_decision: Optional["RouteDecision"] = None,
        confidence_score: Optional[float] = None,
        has_human_review: bool = False,
        human_reviewer: Optional[str] = None,
        has_consensus: bool = False,
        has_narrative: bool = False,
        has_risk_register: bool = False,
        has_processing_register: bool = False,
    ) -> "ComplianceGrid":
        """Evalue tous les articles applicables et retourne la grille."""
        checks = [
            _evaluate_art13_transparency(envelope, tracker, has_narrative=has_narrative),
            _evaluate_art14_human_supervision(envelope, has_human_review, human_reviewer),
            _evaluate_art17_quality_system(
                envelope, tracker, has_consensus,
                has_risk_register=has_risk_register,
                has_processing_register=has_processing_register,
            ),
            _evaluate_art9_risk_management(
                envelope, route_decision, confidence_score,
                has_risk_register=has_risk_register,
            ),
            _evaluate_rgpd_art30(
                envelope,
                has_processing_register=has_processing_register,
            ),
        ]
        return cls(checks=checks)

    @property
    def summary(self) -> Dict[str, int]:
        """Compteurs par statut."""
        counts: Dict[str, int] = {}
        for check in self.checks:
            key = check.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def overall_status(self) -> ComplianceStatus:
        """
        Statut global derive des checks individuels.
        - Si un NON_CONFORME → NON_CONFORME
        - Si tous CONFORME → CONFORME
        - Sinon → PARTIEL
        """
        statuses = {c.status for c in self.checks}
        statuses.discard(ComplianceStatus.NON_APPLICABLE)
        if not statuses:
            return ComplianceStatus.NON_APPLICABLE
        if ComplianceStatus.NON_CONFORME in statuses:
            return ComplianceStatus.NON_CONFORME
        if statuses == {ComplianceStatus.CONFORME}:
            return ComplianceStatus.CONFORME
        return ComplianceStatus.PARTIEL

    def to_report_table(self) -> str:
        """Rendu markdown pour le bloc 'Grille de conformite' du rapport."""
        status_icons = {
            ComplianceStatus.CONFORME: "✅ Conforme",
            ComplianceStatus.PARTIEL: "⚠️ Partiel",
            ComplianceStatus.NON_CONFORME: "❌ Non conforme",
            ComplianceStatus.NON_APPLICABLE: "— N/A",
        }

        lines = [
            "### Grille de conformite reglementaire",
            "",
            "| Article | Exigence | Statut | Evidence | Ecarts |",
            "|---|---|:---:|---|---|",
        ]

        for check in self.checks:
            icon = status_icons.get(check.status, "—")
            evidence_short = check.evidence[:120] + "..." if len(check.evidence) > 120 else check.evidence
            gaps_short = check.gaps[:100] + "..." if len(check.gaps) > 100 else check.gaps
            lines.append(
                f"| {check.article} | {check.exigence[:80]}{'...' if len(check.exigence) > 80 else ''} "
                f"| {icon} | {evidence_short} | {gaps_short} |"
            )

        overall_icon = status_icons.get(self.overall_status, "—")
        lines.extend([
            "",
            f"**Statut global** : {overall_icon}",
            "",
            "> **Note** : les statuts sont evalues honnetement. "
            "\"Partiel\" signifie que des elements existent mais que "
            "la conformite complete necessite des actions supplementaires.",
        ])

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "summary": self.summary,
            "overall_status": self.overall_status.value,
        }
