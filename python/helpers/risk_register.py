"""
SESSION 15 — RiskRegister: Registre formel des risques (Art. 9 AI Act).

Implements the formal risk register required by Art. 9 of the AI Act
(Regulation EU 2024/1689):

  - Risk identification by domain/profile
  - Impact estimation per risk category
  - Documented mitigation measures
  - Continuous monitoring references

The register is deterministic — no LLM judgment. Risk levels and mitigations
are derived from the CriticalityRouter mappings (INTENT_TO_AI_ACT,
INTENT_TO_SENSITIVITY) and the existing safety mechanisms.

Author: Korev AI
License: Proprietary
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.router.routing_contract import RouteDecision

logger = logging.getLogger("risk_register")


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MitigationStatus(str, Enum):
    ACTIVE = "active"
    PLANNED = "planned"
    NOT_IMPLEMENTED = "not_implemented"


@dataclass
class IdentifiedRisk:
    """A single identified risk with impact and mitigation."""
    risk_id: str
    domain: str
    description: str
    level: RiskLevel
    impact: str
    mitigations: List[str] = field(default_factory=list)
    mitigation_status: MitigationStatus = MitigationStatus.ACTIVE
    monitoring: str = ""

    def to_dict(self) -> dict:
        return {
            "risk_id": self.risk_id,
            "domain": self.domain,
            "description": self.description,
            "level": self.level.value,
            "impact": self.impact,
            "mitigations": self.mitigations,
            "mitigation_status": self.mitigation_status.value,
            "monitoring": self.monitoring,
        }


_STATIC_RISKS: List[IdentifiedRisk] = [
    IdentifiedRisk(
        risk_id="RSK-001",
        domain="Juridique (legal_safe)",
        description="Production de contenu juridique incorrect ou incomplet "
                    "pouvant induire l'utilisateur en erreur",
        level=RiskLevel.HIGH,
        impact="Decision juridique fondee sur des informations erronees ; "
               "responsabilite de l'organisation",
        mitigations=[
            "Classification AI Act HIGH_RISK pour le profil legal_safe",
            "Mode legal_safe_mode avec avertissements obligatoires",
            "Consensus PRISM multi-LLM obligatoire pour les requetes juridiques",
            "FAIL_CLOSED : refus de validation si sourcing insuffisant",
            "Metacognition : escalade HUMAN_REVIEW sous seuil de confiance",
        ],
        mitigation_status=MitigationStatus.ACTIVE,
        monitoring="Score de confiance calcule par session ; "
                   "compteur d'escalades HUMAN_REVIEW dans les logs",
    ),
    IdentifiedRisk(
        risk_id="RSK-002",
        domain="Medical (medical)",
        description="Production de recommandations medicales non validees "
                    "par un professionnel de sante",
        level=RiskLevel.CRITICAL,
        impact="Risque pour la sante des personnes ; "
               "non-conformite dispositifs medicaux (Annexe I, section A)",
        mitigations=[
            "Classification AI Act HIGH_RISK pour le profil medical",
            "Sensibilite des donnees RESTRICTED",
            "Consensus PRISM multi-LLM obligatoire",
            "Avertissement systematique : 'Ce contenu ne constitue pas un avis medical'",
            "Metacognition : SAFE_REFUSE si confiance < 0.2",
        ],
        mitigation_status=MitigationStatus.ACTIVE,
        monitoring="Taux de SAFE_REFUSE pour requetes medicales ; "
                   "compteur de consensus declenches",
    ),
    IdentifiedRisk(
        risk_id="RSK-003",
        domain="Finance (finance)",
        description="Production d'analyses financieres incorrectes ou trompeuses "
                    "pouvant influencer des decisions d'investissement",
        level=RiskLevel.HIGH,
        impact="Decisions d'investissement basees sur des donnees erronees ; "
               "risque de perte financiere pour l'utilisateur",
        mitigations=[
            "Classification AI Act HIGH_RISK pour le profil finance",
            "Sensibilite des donnees CONFIDENTIAL",
            "Pipeline strategique avec 4 agents specialises + validation croisee",
            "FAIL_CLOSED : refus de validation si alternatives non analysees",
            "Tracabilite complete des sources (SourceTaxonomy)",
        ],
        mitigation_status=MitigationStatus.ACTIVE,
        monitoring="Score de confiance routing_strength ; "
                   "compteur de FAIL_CLOSED sur pipeline strategique",
    ),
    IdentifiedRisk(
        risk_id="RSK-004",
        domain="Recherche (researcher)",
        description="Biais dans la selection et l'interpretation des sources "
                    "de recherche",
        level=RiskLevel.MEDIUM,
        impact="Analyse biaisee pouvant orienter les decisions strategiques",
        mitigations=[
            "Classification AI Act LIMITED_RISK (obligations de transparence)",
            "Tracabilite des sources avec fiabilite estimee (SourceTaxonomy)",
            "Pipeline multi-agents pour diversifier les perspectives",
            "Hash d'integrite sur chaque document produit",
        ],
        mitigation_status=MitigationStatus.ACTIVE,
        monitoring="Nombre de sources par analyse ; "
                   "diversite des types de sources",
    ),
    IdentifiedRisk(
        risk_id="RSK-005",
        domain="Marketing / Sales / General",
        description="Production de contenu inexact ou trompeur "
                    "a destination commerciale",
        level=RiskLevel.LOW,
        impact="Impact repute faible (pas de decision critique), "
               "mais risque reputationnel",
        mitigations=[
            "Classification AI Act MINIMAL_RISK",
            "Sensibilite des donnees INTERNAL",
            "Metacognition avec seuil d'escalade standard",
            "Section transparence dans le rapport d'audit",
        ],
        mitigation_status=MitigationStatus.ACTIVE,
        monitoring="Monitoring standard des sessions via audit report",
    ),
    IdentifiedRisk(
        risk_id="RSK-006",
        domain="Transversal",
        description="Fuite de donnees personnelles (PII) dans les logs, "
                    "reponses ou traces de raisonnement",
        level=RiskLevel.HIGH,
        impact="Non-conformite RGPD ; atteinte a la vie privee des utilisateurs",
        mitigations=[
            "Sanitization systematique des exceptions (sanitize_exception, no-PII)",
            "TraceStep limite a 60 caracteres, CoT jamais expose",
            "to_safe_dict() et to_safe_narrative() sans contenu brut",
            "Hash d'integrite SHA-256 sur les donnees, pas sur les PII",
            "Logs structures sans contenu conversationnel",
        ],
        mitigation_status=MitigationStatus.ACTIVE,
        monitoring="Tests automatises de detection PII (test_metacognition_policy) ; "
                   "audit des payloads de logs",
    ),
    IdentifiedRisk(
        risk_id="RSK-007",
        domain="Transversal",
        description="Alteration ou falsification des rapports d'audit "
                    "apres generation",
        level=RiskLevel.HIGH,
        impact="Perte de confiance dans le systeme de tracabilite ; "
               "non-conformite Art. 13/17 AI Act",
        mitigations=[
            "Signature RSA-PSS-SHA256 (non-repudiation) sur chaque rapport",
            "Fallback HMAC-SHA256 si cle RSA indisponible",
            "Hash SHA-256 du document, de la requete et de la reponse",
            "Cle privee RSA stockee hors du depot Git (volume Docker /evidence/keys)",
        ],
        mitigation_status=MitigationStatus.ACTIVE,
        monitoring="Verification de signature a la lecture ; "
                   "alerte si methode HMAC utilisee en production",
    ),
]


@dataclass
class RiskRegister:
    """Registre formel des risques — Art. 9 AI Act."""
    risks: List[IdentifiedRisk] = field(default_factory=list)
    session_risks: List[IdentifiedRisk] = field(default_factory=list)

    @classmethod
    def from_session(
        cls,
        route_decision: Optional["RouteDecision"] = None,
        confidence_score: Optional[float] = None,
    ) -> "RiskRegister":
        """Build a risk register from session context.

        Includes all static risks plus any session-specific risk indicators.
        """
        register = cls(risks=list(_STATIC_RISKS))

        session_risks: List[IdentifiedRisk] = []

        if confidence_score is not None and confidence_score < 0.4:
            session_risks.append(IdentifiedRisk(
                risk_id="RSK-SES-001",
                domain="Session courante",
                description=f"Confiance faible detectee ({confidence_score:.0%}) "
                            "pour cette session",
                level=RiskLevel.MEDIUM,
                impact="Resultat potentiellement peu fiable",
                mitigations=[
                    "Escalade automatique vers revue humaine",
                    "Mention explicite dans le rapport d'audit",
                ],
                mitigation_status=MitigationStatus.ACTIVE,
                monitoring="Score affiche dans les metadonnees techniques",
            ))

        if route_decision is not None:
            cat = getattr(route_decision, "ai_act_category", None)
            if cat is not None:
                cat_name = getattr(cat, "name", str(cat))
                if cat_name in ("HIGH_RISK", "UNACCEPTABLE"):
                    session_risks.append(IdentifiedRisk(
                        risk_id="RSK-SES-002",
                        domain="Session courante",
                        description=f"Session classifiee {cat_name} — "
                                    "controles renforces appliques",
                        level=RiskLevel.HIGH if cat_name == "HIGH_RISK"
                              else RiskLevel.CRITICAL,
                        impact="Exigences AI Act renforcees pour cette categorie",
                        mitigations=[
                            "Consensus PRISM obligatoire",
                            "Tracabilite complete des sources",
                            "Signature RSA du rapport d'audit",
                        ],
                        mitigation_status=MitigationStatus.ACTIVE,
                        monitoring="Grille de conformite evaluee en temps reel",
                    ))

        register.session_risks = session_risks
        return register

    def to_report_section(self) -> str:
        """Render as a markdown section for the audit report."""
        lines = [
            "### Registre des risques (Art. 9 AI Act)\n",
            "> *Ce registre identifie les risques lies au systeme IA, "
            "estime leur impact, et documente les mesures d'attenuation "
            "conformement a l'Art. 9 du Reglement AI Act (UE) 2024/1689.*\n",
            "#### Risques identifies par domaine\n",
            "| ID | Domaine | Risque | Niveau | Statut attenuation |",
            "|---|---|---|:---:|:---:|",
        ]

        status_icons = {
            MitigationStatus.ACTIVE: "✅ Actif",
            MitigationStatus.PLANNED: "🔄 Planifie",
            MitigationStatus.NOT_IMPLEMENTED: "❌ Absent",
        }

        for risk in self.risks:
            level_label = {
                RiskLevel.LOW: "🟢 Faible",
                RiskLevel.MEDIUM: "🟡 Modere",
                RiskLevel.HIGH: "🟠 Eleve",
                RiskLevel.CRITICAL: "🔴 Critique",
            }.get(risk.level, risk.level.value)
            status = status_icons.get(risk.mitigation_status, "—")
            desc_short = risk.description[:80] + "..." if len(risk.description) > 80 else risk.description
            lines.append(
                f"| {risk.risk_id} | {risk.domain} | {desc_short} "
                f"| {level_label} | {status} |"
            )

        if self.session_risks:
            lines.extend([
                "",
                "#### Risques specifiques a cette session\n",
                "| ID | Description | Niveau | Mesures |",
                "|---|---|:---:|---|",
            ])
            for risk in self.session_risks:
                level_label = {
                    RiskLevel.LOW: "🟢 Faible",
                    RiskLevel.MEDIUM: "🟡 Modere",
                    RiskLevel.HIGH: "🟠 Eleve",
                    RiskLevel.CRITICAL: "🔴 Critique",
                }.get(risk.level, risk.level.value)
                mitigations_short = " ; ".join(risk.mitigations[:3])
                lines.append(
                    f"| {risk.risk_id} | {risk.description[:80]} "
                    f"| {level_label} | {mitigations_short} |"
                )

        lines.extend([
            "",
            "#### Mesures d'attenuation detaillees\n",
        ])

        for risk in self.risks:
            lines.append(f"**{risk.risk_id} — {risk.domain}**")
            for m in risk.mitigations:
                lines.append(f"  - {m}")
            if risk.monitoring:
                lines.append(f"  - *Monitoring* : {risk.monitoring}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "risks": [r.to_dict() for r in self.risks],
            "session_risks": [r.to_dict() for r in self.session_risks],
            "total_risks": len(self.risks) + len(self.session_risks),
        }
