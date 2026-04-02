"""
SESSION 15 — ProcessingRegister: Registre des activites de traitement (RGPD Art. 30).

Implements the formal register of processing activities required by
Art. 30 of the GDPR (Regulation EU 2016/679):

  (a) Purposes of processing
  (b) Categories of data subjects
  (c) Categories of recipients
  (d) Transfers to third countries
  (e) Envisaged time limits for erasure
  (f) Technical and organisational security measures

This register is static + session-enriched: static entries describe the
system-wide processing policies, and session data adds specifics.

Author: Korev AI
License: Proprietary
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.session_envelope import SessionEnvelope

logger = logging.getLogger("processing_register")


@dataclass
class ProcessingActivity:
    """A single processing activity entry per Art. 30 RGPD."""
    activity_id: str
    purpose: str
    legal_basis: str
    data_categories: List[str]
    data_subject_categories: List[str]
    recipients: List[str]
    third_country_transfers: str
    retention_period: str
    security_measures: List[str]

    def to_dict(self) -> dict:
        return {
            "activity_id": self.activity_id,
            "purpose": self.purpose,
            "legal_basis": self.legal_basis,
            "data_categories": self.data_categories,
            "data_subject_categories": self.data_subject_categories,
            "recipients": self.recipients,
            "third_country_transfers": self.third_country_transfers,
            "retention_period": self.retention_period,
            "security_measures": self.security_measures,
        }


_STATIC_ACTIVITIES: List[ProcessingActivity] = [
    ProcessingActivity(
        activity_id="PROC-001",
        purpose="Assistance par intelligence artificielle : analyse de requetes "
                "utilisateur et generation de reponses structurees "
                "(recherche, finance, juridique, marketing, strategique)",
        legal_basis="Interet legitime (Art. 6(1)(f) RGPD) — fourniture du service "
                    "contractuel d'aide a la decision par IA",
        data_categories=[
            "Requetes textuelles de l'utilisateur",
            "Identifiant de session (pseudonymise)",
            "Nom d'utilisateur et organisation",
            "Horodatages de traitement",
        ],
        data_subject_categories=[
            "Utilisateurs du service KOREV Evidence (professionnels B2B)",
            "Administrateurs de la plateforme",
        ],
        recipients=[
            "KOREV AI (responsable de traitement)",
            "Equipe technique KOREV (sous obligation de confidentialite)",
            "Aucun sous-traitant tiers avec acces aux donnees personnelles",
        ],
        third_country_transfers="Aucun transfert hors UE. Infrastructure hebergee "
                                "chez OVH Cloud, datacenter de Gravelines (France). "
                                "Modeles LLM appeles via OpenRouter (API), "
                                "requetes anonymisees (pas de PII transmises).",
        retention_period="Logs d'audit : 12 mois (configurable via audit_retention_days). "
                         "Sessions et conversations : duree de la session active + 90 jours. "
                         "Rapports d'audit : 12 mois. "
                         "Suppression automatique a echeance.",
        security_measures=[
            "Chiffrement TLS 1.3 en transit (Caddy reverse proxy, Let's Encrypt)",
            "Hash d'integrite SHA-256 sur sessions, requetes, reponses et documents",
            "Signature RSA-PSS-SHA256 pour non-repudiation des rapports d'audit",
            "Fallback HMAC-SHA256 si cle RSA indisponible",
            "Sanitization systematique des PII dans les logs (no-PII policy)",
            "Authentification par compte utilisateur (users.json, role-based)",
            "Cle privee RSA stockee en volume Docker isole (permissions 400)",
            "Acces audit restreint : Admin + DPO + RSSI (role-based)",
            "Pare-feu UFW + fail2ban sur le serveur OVH",
        ],
    ),
    ProcessingActivity(
        activity_id="PROC-002",
        purpose="Journalisation et audit de conformite : generation de rapports "
                "d'audit tracables pour les obligations AI Act et RGPD",
        legal_basis="Obligation legale (Art. 6(1)(c) RGPD) — conformite AI Act "
                    "(Art. 13, 17) et RGPD (Art. 30)",
        data_categories=[
            "Metadonnees de session (ID, horodatages, durees)",
            "Hashes d'integrite (SHA-256) des requetes et reponses",
            "Signatures cryptographiques des rapports (RSA/HMAC)",
            "Statuts de conformite par article reglementaire",
        ],
        data_subject_categories=[
            "Utilisateurs du service KOREV Evidence (indirectement via session ID)",
        ],
        recipients=[
            "KOREV AI (responsable de traitement)",
            "DPO designe (acces lecture aux rapports d'audit)",
            "RSSI (acces lecture aux logs de securite)",
        ],
        third_country_transfers="Aucun transfert hors UE. Rapports stockes sur le serveur "
                                "OVH Gravelines (France).",
        retention_period="Rapports d'audit : 12 mois. "
                         "Logs applicatifs : 12 mois. "
                         "Metriques d'observabilite : 90 jours.",
        security_measures=[
            "Integrite garantie par hash SHA-256 et signature RSA-PSS-SHA256",
            "Acces restreint par role (Admin, DPO, RSSI)",
            "Stockage sur volume Docker dedie (evidence-audit)",
            "Aucune PII dans les rapports d'audit (hashes uniquement)",
        ],
    ),
]


@dataclass
class ProcessingRegister:
    """Registre des activites de traitement — RGPD Art. 30."""
    controller: str = "KOREV AI"
    dpo_contact: str = "dpo@korev-evidence.com"
    activities: List[ProcessingActivity] = field(default_factory=list)
    session_user: Optional[str] = None
    session_organization: Optional[str] = None

    @classmethod
    def from_session(
        cls,
        envelope: Optional["SessionEnvelope"] = None,
    ) -> "ProcessingRegister":
        """Build the register, enriched with session metadata."""
        register = cls(activities=list(_STATIC_ACTIVITIES))

        if envelope is not None:
            register.session_user = envelope.username
            register.session_organization = envelope.organization

        return register

    def to_report_section(self) -> str:
        """Render as a markdown section for the audit report."""
        lines = [
            "### Registre des activites de traitement (RGPD Art. 30)\n",
            "> *Ce registre documente les activites de traitement de donnees "
            "personnelles conformement a l'Art. 30 du Reglement General "
            "sur la Protection des Donnees (UE) 2016/679.*\n",
            "#### Informations generales\n",
            "| Champ | Valeur |",
            "|---|---|",
            f"| Responsable de traitement | {self.controller} |",
            f"| Contact DPO | {self.dpo_contact} |",
            f"| Utilisateur de la session | {self.session_user or '—'} |",
            f"| Organisation | {self.session_organization or '—'} |",
            "",
        ]

        for activity in self.activities:
            lines.extend([
                f"#### {activity.activity_id} — Finalite\n",
                f"**{activity.purpose}**\n",
                f"**Base legale** : {activity.legal_basis}\n",
                "**Categories de donnees traitees** :",
            ])
            for cat in activity.data_categories:
                lines.append(f"  - {cat}")
            lines.append("\n**Categories de personnes concernees** :")
            for cat in activity.data_subject_categories:
                lines.append(f"  - {cat}")
            lines.append("\n**Destinataires** :")
            for r in activity.recipients:
                lines.append(f"  - {r}")
            lines.extend([
                f"\n**Transferts hors UE** : {activity.third_country_transfers}",
                f"\n**Delais de conservation** : {activity.retention_period}",
                "\n**Mesures de securite techniques et organisationnelles** :",
            ])
            for m in activity.security_measures:
                lines.append(f"  - {m}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "controller": self.controller,
            "dpo_contact": self.dpo_contact,
            "activities": [a.to_dict() for a in self.activities],
            "session_user": self.session_user,
            "session_organization": self.session_organization,
        }

    def has_required_fields(self) -> bool:
        """Check if all Art. 30 mandatory fields are present."""
        if not self.activities:
            return False
        for a in self.activities:
            if not (a.purpose and a.legal_basis and a.data_categories
                    and a.data_subject_categories and a.recipients
                    and a.third_country_transfers and a.retention_period
                    and a.security_measures):
                return False
        return True
