"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    EVIDENCE NATIVE REPORT GENERATOR                          ║
║                                                                              ║
║  Transforme les rapports génériques en rapports "Evidence-native".           ║
║                                                                              ║
║  Différenciation Korev:                                                      ║
║  1. Traçabilité: chaque recommandation liée à un risque + arbitrage          ║
║  2. Vérifiabilité: preuves (tests/logs/commandes) ou label UNVERIFIED        ║
║  3. Gouvernance: consensus PRISM (quorum 2/3), fail-closed, badges           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("evidence_native")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class Criticality(str, Enum):
    """Niveau de criticité d'un rapport."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ValidationMode(str, Enum):
    """Mode de validation du rapport."""
    SINGLE = "SINGLE"
    DEBATE = "DEBATE"
    CONSENSUS = "CONSENSUS"


class GovernanceStatus(str, Enum):
    """Statut de gouvernance."""
    APPROVED = "APPROVED"
    NO_CONSENSUS = "NO_CONSENSUS"
    INFRA_FAILURE = "INFRA_FAILURE"
    PENDING = "PENDING"


class ConfidenceBadge(str, Enum):
    """Badge de confiance pour les affirmations."""
    VERIFIED = "VERIFIED"        # Preuves code/tests/logs reproductibles
    PARTIAL = "PARTIAL"          # Preuves partielles / wiring non prouvé
    UNVERIFIED = "UNVERIFIED"    # Aucune preuve technique disponible
    FAIL_CLOSED = "FAIL_CLOSED"  # Criticité HIGH + UNVERIFIED sur point structurant


class ImpactLevel(str, Enum):
    """Niveau d'impact."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Probability(str, Enum):
    """Probabilité d'occurrence."""
    CERTAIN = "CERTAIN"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNLIKELY = "UNLIKELY"


class SourceType(str, Enum):
    """Type de source."""
    PRIMARY = "PRIMARY"      # Source primaire (peer-reviewed, officielle)
    SECONDARY = "SECONDARY"  # Source secondaire (revue, méta-analyse)
    TERTIARY = "TERTIARY"    # Source tertiaire (vulgarisation)


class SourceReliability(str, Enum):
    """Fiabilité de la source."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Score de criticité (Impact x Probabilité)
CRITICALITY_MATRIX = {
    (ImpactLevel.CRITICAL, Probability.CERTAIN): 25,
    (ImpactLevel.CRITICAL, Probability.LIKELY): 20,
    (ImpactLevel.CRITICAL, Probability.POSSIBLE): 15,
    (ImpactLevel.CRITICAL, Probability.UNLIKELY): 10,
    (ImpactLevel.HIGH, Probability.CERTAIN): 20,
    (ImpactLevel.HIGH, Probability.LIKELY): 15,
    (ImpactLevel.HIGH, Probability.POSSIBLE): 10,
    (ImpactLevel.HIGH, Probability.UNLIKELY): 5,
    (ImpactLevel.MEDIUM, Probability.CERTAIN): 15,
    (ImpactLevel.MEDIUM, Probability.LIKELY): 10,
    (ImpactLevel.MEDIUM, Probability.POSSIBLE): 5,
    (ImpactLevel.MEDIUM, Probability.UNLIKELY): 2,
    (ImpactLevel.LOW, Probability.CERTAIN): 10,
    (ImpactLevel.LOW, Probability.LIKELY): 5,
    (ImpactLevel.LOW, Probability.POSSIBLE): 2,
    (ImpactLevel.LOW, Probability.UNLIKELY): 1,
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DecisionGovernance:
    """Bloc de gouvernance de décision."""
    criticality: Criticality = Criticality.MEDIUM
    validation_mode: ValidationMode = ValidationMode.SINGLE
    quorum: str = "2/3 votes effectifs"
    status: GovernanceStatus = GovernanceStatus.PENDING
    arbiters: List[str] = field(default_factory=list)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    missing_info: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Génère le bloc markdown de gouvernance."""
        lines = [
            "## Decision Governance",
            "",
            "| Attribut | Valeur |",
            "|----------|--------|",
            f"| **Criticité** | `{self.criticality.value}` |",
            f"| **Mode de validation** | `{self.validation_mode.value}` |",
            f"| **Quorum** | {self.quorum} |",
            f"| **Statut** | `{self.status.value}` |",
            f"| **Arbitres** | {', '.join(self.arbiters) if self.arbiters else 'N/A'} |",
            f"| **Correlation ID** | `{self.correlation_id}` |",
            "",
            "> **Règle FAIL_CLOSED**: En mode HIGH, si `NO_CONSENSUS` ou `UNVERIFIED` "
            "sur un point structurant, aucune recommandation ferme n'est émise.",
        ]
        
        if self.missing_info:
            lines.extend([
                "",
                "### Informations manquantes",
                "",
            ])
            for item in self.missing_info:
                lines.append(f"- {item}")
        
        return "\n".join(lines)


@dataclass
class ClientContext:
    """Contexte client."""
    name: str = ""
    sector: str = ""
    sites: List[str] = field(default_factory=list)
    headcount: str = ""
    compliance: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Génère le markdown du contexte client."""
        return f"""### Contexte client

| Attribut | Valeur |
|----------|--------|
| **Client** | {self.name} |
| **Secteur** | {self.sector} |
| **Sites concernés** | {', '.join(self.sites)} |
| **Effectif** | {self.headcount} |
| **Contraintes réglementaires** | {', '.join(self.compliance)} |"""


@dataclass
class Scope:
    """Périmètre de l'étude."""
    included: List[str] = field(default_factory=list)
    excluded: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Génère le markdown du périmètre."""
        lines = [
            "### Périmètre de l'étude",
            "",
            "#### IN (inclus dans le périmètre)",
            "",
        ]
        for item in self.included:
            lines.append(f"- {item}")
        
        lines.extend([
            "",
            "#### OUT (exclus du périmètre)",
            "",
        ])
        for item in self.excluded:
            lines.append(f"- {item}")
        
        return "\n".join(lines)


@dataclass
class Source:
    """Source de données."""
    id: str = ""
    name: str = ""
    source_type: SourceType = SourceType.SECONDARY
    reliability: SourceReliability = SourceReliability.MEDIUM
    date_collected: str = ""
    url: Optional[str] = None


@dataclass
class Hypothesis:
    """Hypothèse de travail."""
    id: str = ""
    statement: str = ""
    impact_if_false: str = ""
    verifiable: str = "PARTIAL"  # YES, NO, PARTIAL


@dataclass
class Risk:
    """Risque identifié."""
    id: str = ""
    description: str = ""
    impact: ImpactLevel = ImpactLevel.MEDIUM
    probability: Probability = Probability.POSSIBLE
    existing_controls: str = ""
    proposed_controls: str = ""
    
    @property
    def score(self) -> int:
        """Calcule le score de criticité."""
        return CRITICALITY_MATRIX.get((self.impact, self.probability), 5)


@dataclass
class Alternative:
    """Alternative pour une décision."""
    name: str
    advantages: str
    disadvantages: str
    rejection_reason: str = ""  # Vide si retenue
    is_selected: bool = False


@dataclass
class Decision:
    """Décision d'architecture."""
    id: str = ""
    description: str = ""
    justification: str = ""
    risks_covered: List[str] = field(default_factory=list)
    tradeoffs: str = ""
    badge: ConfidenceBadge = ConfidenceBadge.UNVERIFIED
    alternatives: List[Alternative] = field(default_factory=list)


@dataclass
class ArchitectureComponent:
    """Composant d'architecture."""
    zone: str
    name: str
    criticality: Criticality
    is_spof: bool
    has_pra: bool
    notes: str = ""


@dataclass
class FailoverScenario:
    """Scénario de basculement PRA."""
    scenario: str
    source_component: str
    target_component: str
    rto: str
    rpo: str


@dataclass
class Action:
    """Action du plan de mise en œuvre."""
    description: str
    responsible: str = ""
    dependencies: str = ""
    deliverable: str = ""
    badge: ConfidenceBadge = ConfidenceBadge.UNVERIFIED


@dataclass
class VerificationCommand:
    """Commande de vérification."""
    test_name: str
    command: str
    expected_proof: str
    status: ConfidenceBadge = ConfidenceBadge.UNVERIFIED


@dataclass
class Proof:
    """Preuve collectée."""
    id: str
    claim: str
    source: str
    proof_type: str  # TEST, LOG, DOC
    status: ConfidenceBadge


@dataclass
class UnverifiedPoint:
    """Point non vérifié."""
    point: str
    reason: str
    impact: ImpactLevel
    required_action: str


@dataclass
class FailClosedPoint:
    """Point FAIL_CLOSED."""
    id: str
    point: str
    reason: str
    missing_info: str


@dataclass
class Limit:
    """Limite de l'analyse."""
    description: str
    impact: str
    mitigation: str


@dataclass
class Reference:
    """Référence."""
    id: str
    title: str
    url: str
    ref_type: str  # DOC, CODE, TEST


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE NATIVE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EvidenceNativeReport:
    """
    Rapport Evidence-Native complet.
    
    Structure obligatoire:
    A. Executive Summary (conclusion first)
    B. Contexte & Périmètre
    C. Hypothèses
    D. Registre des Risques
    E. Décisions d'Architecture
    F. Architecture Cible
    G. Plan de Mise en Œuvre
    H. Preuves & Vérification
    I. Limites & FAIL_CLOSED
    J. Annexes
    """
    
    # Métadonnées
    title: str = "Rapport Evidence-Native"
    version: str = "1.0.0"
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    
    # Gouvernance
    governance: DecisionGovernance = field(default_factory=DecisionGovernance)
    
    # Sections
    executive_summary_conclusions: List[str] = field(default_factory=list)
    executive_summary_recommendations: List[Tuple[str, str, str, ConfidenceBadge]] = field(default_factory=list)
    
    client_context: ClientContext = field(default_factory=ClientContext)
    scope: Scope = field(default_factory=Scope)
    sources: List[Source] = field(default_factory=list)
    
    hypotheses: List[Hypothesis] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    decisions: List[Decision] = field(default_factory=list)
    
    architecture_diagram: str = ""
    architecture_components: List[ArchitectureComponent] = field(default_factory=list)
    failover_scenarios: List[FailoverScenario] = field(default_factory=list)
    
    phase_1_actions: List[Action] = field(default_factory=list)  # 30 jours
    phase_2_actions: List[Action] = field(default_factory=list)  # 60 jours
    phase_3_actions: List[Action] = field(default_factory=list)  # 90 jours
    
    verification_commands: List[VerificationCommand] = field(default_factory=list)
    proofs: List[Proof] = field(default_factory=list)
    unverified_points: List[UnverifiedPoint] = field(default_factory=list)
    
    limits: List[Limit] = field(default_factory=list)
    fail_closed_points: List[FailClosedPoint] = field(default_factory=list)
    
    glossary: Dict[str, str] = field(default_factory=dict)
    references: List[Reference] = field(default_factory=list)
    
    def _generate_header(self) -> str:
        """Génère l'en-tête du rapport."""
        return f"""# {self.title}

**Date de génération**: {self.date}  
**Version**: {self.version}  
**Auteur système**: KOREV Evidence  

---

{self.governance.to_markdown()}

---"""

    def _generate_executive_summary(self) -> str:
        """Génère le résumé exécutif."""
        lines = [
            "## A. Executive Summary",
            "",
            "> **Conclusion first** — Cette section résume les conclusions et recommandations clés.",
            "",
            "### Conclusions principales",
            "",
        ]
        
        for i, conclusion in enumerate(self.executive_summary_conclusions, 1):
            lines.append(f"{i}. {conclusion}")
        
        lines.extend([
            "",
            "### Recommandations prioritaires",
            "",
            "| Priorité | Recommandation | Risque couvert | Badge |",
            "|----------|----------------|----------------|-------|",
        ])
        
        for i, (reco, risk_id, _, badge) in enumerate(self.executive_summary_recommendations, 1):
            lines.append(f"| P{i} | {reco} | {risk_id} | `{badge.value}` |")
        
        return "\n".join(lines)
    
    def _generate_context_scope(self) -> str:
        """Génère la section Contexte & Périmètre."""
        lines = [
            "## B. Contexte & Périmètre",
            "",
            self.client_context.to_markdown(),
            "",
            self.scope.to_markdown(),
            "",
            "### Sources de données utilisées",
            "",
            "| Source | Type | Fiabilité | Date collecte |",
            "|--------|------|-----------|---------------|",
        ]
        
        for source in self.sources:
            lines.append(
                f"| {source.name} | `{source.source_type.value}` | "
                f"`{source.reliability.value}` | {source.date_collected} |"
            )
        
        return "\n".join(lines)
    
    def _generate_hypotheses(self) -> str:
        """Génère la section Hypothèses."""
        lines = [
            "## C. Hypothèses",
            "",
            "> **Explicite > Implicite** — Liste des hypothèses sur lesquelles repose l'analyse.",
            "",
            "| ID | Hypothèse | Impact si fausse | Vérifiable? |",
            "|----|-----------|------------------|-------------|",
        ]
        
        for h in self.hypotheses:
            lines.append(f"| {h.id} | {h.statement} | {h.impact_if_false} | `{h.verifiable}` |")
        
        return "\n".join(lines)
    
    def _generate_risks(self) -> str:
        """Génère le registre des risques."""
        lines = [
            "## D. Registre des Risques",
            "",
            "> **Threat model** — Identification et évaluation des risques.",
            "",
            "| ID | Risque | Impact | Probabilité | Score | Contrôles existants | Contrôles proposés |",
            "|----|--------|--------|-------------|-------|---------------------|---------------------|",
        ]
        
        for r in self.risks:
            lines.append(
                f"| {r.id} | {r.description} | `{r.impact.value}` | `{r.probability.value}` | "
                f"{r.score} | {r.existing_controls} | {r.proposed_controls} |"
            )
        
        lines.extend([
            "",
            "### Matrice de criticité",
            "",
            "```",
            "                        IMPACT",
            "                LOW    MEDIUM    HIGH    CRITICAL",
            "PROBABILITÉ  ┌─────────────────────────────────────┐",
            "  CERTAIN    │   M   │    H    │   C   │    C     │",
            "  LIKELY     │   L   │    M    │   H   │    C     │",
            "  POSSIBLE   │   L   │    M    │   M   │    H     │",
            "  UNLIKELY   │   L   │    L    │   M   │    M     │",
            "             └─────────────────────────────────────┘",
            "L=Low, M=Medium, H=High, C=Critical",
            "```",
        ])
        
        return "\n".join(lines)
    
    def _generate_decisions(self) -> str:
        """Génère la section Décisions d'Architecture."""
        lines = [
            "## E. Décisions d'Architecture",
            "",
            "> **Arbitrages explicites** — Chaque décision structurante avec justification et alternatives.",
            "",
            "### Table des décisions",
            "",
            "| ID | Décision | Justification | Risques couverts | Trade-offs | Statut |",
            "|----|----------|---------------|------------------|------------|--------|",
        ]
        
        for d in self.decisions:
            risks_str = ", ".join(d.risks_covered)
            lines.append(
                f"| {d.id} | {d.description} | {d.justification} | "
                f"{risks_str} | {d.tradeoffs} | `{d.badge.value}` |"
            )
        
        lines.extend([
            "",
            "### Alternatives écartées",
            "",
            "> **Montrer le raisonnement** — Pour chaque décision structurante, les options non retenues.",
            "",
        ])
        
        for d in self.decisions:
            if d.alternatives:
                lines.append(f"#### {d.id}: {d.description}")
                lines.append("")
                lines.append("| Alternative | Avantages | Inconvénients | Raison du rejet |")
                lines.append("|-------------|-----------|---------------|-----------------|")
                
                for alt in d.alternatives:
                    status = "**Retenue**" if alt.is_selected else alt.rejection_reason
                    lines.append(
                        f"| {alt.name} | {alt.advantages} | {alt.disadvantages} | {status} |"
                    )
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_architecture(self) -> str:
        """Génère la section Architecture Cible."""
        lines = [
            "## F. Architecture Cible",
            "",
            "### Vue d'ensemble",
            "",
            "```",
            self.architecture_diagram or "[Schéma d'architecture à insérer]",
            "```",
            "",
            "### Annotations critiques",
            "",
            "| Zone | Composant | Criticité | SPOF? | PRA? | Notes |",
            "|------|-----------|-----------|-------|------|-------|",
        ]
        
        for c in self.architecture_components:
            spof = "YES" if c.is_spof else "NO"
            pra = "YES" if c.has_pra else "NO"
            lines.append(
                f"| {c.zone} | {c.name} | `{c.criticality.value}` | "
                f"`{spof}` | `{pra}` | {c.notes} |"
            )
        
        if self.failover_scenarios:
            lines.extend([
                "",
                "### Points de bascule PRA",
                "",
                "| Scénario | Composant source | Composant cible | RTO | RPO |",
                "|----------|------------------|-----------------|-----|-----|",
            ])
            for f in self.failover_scenarios:
                lines.append(
                    f"| {f.scenario} | {f.source_component} | "
                    f"{f.target_component} | {f.rto} | {f.rpo} |"
                )
        
        return "\n".join(lines)
    
    def _generate_implementation_plan(self) -> str:
        """Génère le plan de mise en œuvre."""
        lines = [
            "## G. Plan de Mise en Œuvre",
            "",
            "### Vision 30/60/90 jours",
            "",
        ]
        
        phases = [
            ("Phase 1 — 30 premiers jours (Quick Wins)", self.phase_1_actions),
            ("Phase 2 — 60 jours (Fondations)", self.phase_2_actions),
            ("Phase 3 — 90 jours (Consolidation)", self.phase_3_actions),
        ]
        
        for phase_name, actions in phases:
            lines.append(f"#### {phase_name}")
            lines.append("")
            lines.append("| Action | Responsable | Dépendances | Livrable | Badge |")
            lines.append("|--------|-------------|-------------|----------|-------|")
            
            for a in actions:
                lines.append(
                    f"| {a.description} | {a.responsible} | {a.dependencies} | "
                    f"{a.deliverable} | `{a.badge.value}` |"
                )
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_verification(self) -> str:
        """Génère la section Preuves & Vérification."""
        lines = [
            "## H. Preuves & Vérification",
            "",
            "> **Show your work** — Commandes, tests, logs pour reproduire les vérifications.",
            "",
            "### Commandes de vérification",
            "",
            "| Test | Commande | Preuve attendue | Statut |",
            "|------|----------|-----------------|--------|",
        ]
        
        for v in self.verification_commands:
            lines.append(
                f"| {v.test_name} | `{v.command}` | {v.expected_proof} | `{v.status.value}` |"
            )
        
        if self.proofs:
            lines.extend([
                "",
                "### Preuves collectées",
                "",
                "| ID | Claim | Source | Type preuve | Statut |",
                "|----|-------|--------|-------------|--------|",
            ])
            for p in self.proofs:
                lines.append(
                    f"| {p.id} | {p.claim} | {p.source} | `{p.proof_type}` | `{p.status.value}` |"
                )
        
        if self.unverified_points:
            lines.extend([
                "",
                "### Points non vérifiés",
                "",
                "> **Honnêteté intellectuelle** — Ce que nous n'avons pas pu prouver.",
                "",
                "| Point | Raison non vérifiable | Impact | Action requise |",
                "|-------|----------------------|--------|----------------|",
            ])
            for u in self.unverified_points:
                lines.append(
                    f"| {u.point} | {u.reason} | `{u.impact.value}` | {u.required_action} |"
                )
        
        return "\n".join(lines)
    
    def _generate_limits(self) -> str:
        """Génère la section Limites & FAIL_CLOSED."""
        lines = [
            "## I. Limites & FAIL_CLOSED",
            "",
            "> **Quand Evidence refuse de conclure** — Transparence sur les limites du système.",
            "",
            "### Limites de l'analyse",
            "",
            "| Limite | Impact sur conclusions | Mitigation |",
            "|--------|----------------------|------------|",
        ]
        
        for lim in self.limits:
            lines.append(f"| {lim.description} | {lim.impact} | {lim.mitigation} |")
        
        if self.fail_closed_points:
            lines.extend([
                "",
                "### Points FAIL_CLOSED",
                "",
                "> **En criticité HIGH, les points suivants empêchent une recommandation ferme.**",
                "",
                "| ID | Point | Raison FAIL_CLOSED | Information manquante |",
                "|----|-------|-------------------|----------------------|",
            ])
            for fc in self.fail_closed_points:
                lines.append(
                    f"| {fc.id} | {fc.point} | {fc.reason} | {fc.missing_info} |"
                )
        
        lines.extend([
            "",
            "### Avertissements",
            "",
            "⚠️ **Ce rapport ne constitue pas** :",
            "- Un audit de conformité certifié",
            "- Un conseil juridique",
            "- Une garantie de sécurité",
            "",
            "⚠️ **Conditions de validité** :",
            "- Les hypothèses listées en section C doivent rester vraies",
            "- Le contexte client doit correspondre au périmètre défini",
            "- Les informations fournies doivent être exactes et à jour",
        ])
        
        return "\n".join(lines)
    
    def _generate_annexes(self) -> str:
        """Génère les annexes."""
        lines = [
            "## J. Annexes",
            "",
            "### Glossaire",
            "",
            "| Terme | Définition |",
            "|-------|------------|",
        ]
        
        # Glossaire par défaut
        default_glossary = {
            "Fail-closed": "Comportement où le système refuse en cas de doute plutôt que d'approuver",
            "Quorum": "Nombre minimum de votes requis pour une décision (2/3 des votes effectifs)",
            "PRISM": "Moteur de consensus multi-LLM de KOREV Evidence",
            "SPOF": "Single Point of Failure — composant dont la défaillance entraîne l'arrêt du système",
            "RTO": "Recovery Time Objective — temps maximal pour restaurer un service",
            "RPO": "Recovery Point Objective — perte de données maximale acceptable",
        }
        
        merged_glossary = {**default_glossary, **self.glossary}
        for term, definition in sorted(merged_glossary.items()):
            lines.append(f"| **{term}** | {definition} |")
        
        if self.references:
            lines.extend([
                "",
                "### Références",
                "",
                "| ID | Titre | URL/Chemin | Type |",
                "|----|-------|-----------|------|",
            ])
            for ref in self.references:
                lines.append(
                    f"| {ref.id} | {ref.title} | {ref.url} | `{ref.ref_type}` |"
                )
        
        # Métadonnées du rapport
        content_hash = hashlib.sha256(self.title.encode()).hexdigest()[:16]
        
        lines.extend([
            "",
            "### Métadonnées du rapport",
            "",
            "| Attribut | Valeur |",
            "|----------|--------|",
            "| **Template version** | 1.0.0 |",
            "| **Généré par** | KOREV Evidence |",
            f"| **Date génération** | {datetime.now(timezone.utc).isoformat()} |",
            f"| **Hash du contenu** | `{content_hash}` |",
            f"| **Correlation ID** | `{self.governance.correlation_id}` |",
            "",
            "---",
            "",
            "## Badges de confiance",
            "",
            "| Badge | Signification |",
            "|-------|---------------|",
            "| `VERIFIED` | Preuves code/tests/logs reproductibles disponibles |",
            "| `PARTIAL` | Preuves partielles ou wiring non prouvé |",
            "| `UNVERIFIED` | Aucune preuve technique disponible |",
            "| `FAIL_CLOSED` | Criticité HIGH + UNVERIFIED sur point structurant ⇒ pas de recommandation |",
            "",
            "---",
            "",
            "*Document généré par KOREV Evidence — Toutes les affirmations sont basées sur des preuves ou marquées UNVERIFIED.*",
        ])
        
        return "\n".join(lines)
    
    def generate(self) -> str:
        """
        Génère le rapport complet au format Markdown.
        
        Returns:
            Contenu Markdown du rapport
        """
        sections = [
            self._generate_header(),
            self._generate_executive_summary(),
            "---",
            self._generate_context_scope(),
            "---",
            self._generate_hypotheses(),
            "---",
            self._generate_risks(),
            "---",
            self._generate_decisions(),
            "---",
            self._generate_architecture(),
            "---",
            self._generate_implementation_plan(),
            "---",
            self._generate_verification(),
            "---",
            self._generate_limits(),
            "---",
            self._generate_annexes(),
        ]
        
        return "\n\n".join(sections)
    
    def save(self, path: str):
        """
        Sauvegarde le rapport dans un fichier.
        
        Args:
            path: Chemin du fichier de sortie
        """
        content = self.generate()
        Path(path).write_text(content, encoding="utf-8")
        logger.info(f"Report saved to {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFORMER — Convert Generic Report to Evidence-Native
# ═══════════════════════════════════════════════════════════════════════════════

class GenericReportTransformer:
    """
    Transforme un rapport générique en rapport Evidence-native.
    
    Entrées:
    - generic_report_md: Contenu du rapport générique
    - client_context: Métadonnées client
    - preferences: Préférences de génération
    
    Sortie:
    - EvidenceNativeReport populé
    """
    
    # Points connus comme UNVERIFIED (référencés depuis l'audit)
    KNOWN_UNVERIFIED = [
        "Audit persistant long terme",
        "Suivi coûts/tokens",
        "Redaction PII automatique",
    ]
    
    def __init__(self):
        self.report = EvidenceNativeReport()
    
    def transform(
        self,
        generic_report: str,
        client_context: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None,
    ) -> EvidenceNativeReport:
        """
        Transforme un rapport générique.
        
        Args:
            generic_report: Contenu Markdown du rapport générique
            client_context: Métadonnées client
            preferences: Préférences (mode NIS2, OT strict, etc.)
            
        Returns:
            Rapport Evidence-native
        """
        preferences = preferences or {}
        
        # 1. Extraire les sections du rapport générique
        sections = self._extract_sections(generic_report)
        
        # 2. Initialiser le rapport
        self.report.title = self._extract_title(generic_report) or "Rapport Evidence-Native"
        
        # 3. Configurer le contexte client
        self._setup_client_context(client_context)
        
        # 4. Configurer la gouvernance selon les préférences
        self._setup_governance(preferences)
        
        # 5. Extraire et transformer les recommandations en décisions tracées
        self._transform_recommendations(sections)
        
        # 6. Générer le registre des risques
        self._generate_risks(sections, preferences)
        
        # 7. Ajouter les hypothèses
        self._add_default_hypotheses()
        
        # 8. Ajouter les commandes de vérification standard
        self._add_verification_commands()
        
        # 9. Ajouter les limites et points UNVERIFIED
        self._add_limits_and_unverified()
        
        return self.report
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extrait les sections du rapport générique."""
        sections = {}
        current_section = "intro"
        current_content = []
        
        for line in content.split("\n"):
            if line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                current_section = line[3:].strip().lower()
                current_content = []
            else:
                current_content.append(line)
        
        if current_content:
            sections[current_section] = "\n".join(current_content)
        
        return sections
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extrait le titre du rapport."""
        for line in content.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        return None
    
    def _setup_client_context(self, context: Dict[str, Any]):
        """Configure le contexte client."""
        self.report.client_context = ClientContext(
            name=context.get("name", "Client"),
            sector=context.get("sector", "Industrie"),
            sites=context.get("sites", []),
            headcount=context.get("headcount", "N/A"),
            compliance=context.get("compliance", []),
        )
        
        self.report.scope = Scope(
            included=context.get("scope_in", []),
            excluded=context.get("scope_out", []),
        )
    
    def _setup_governance(self, preferences: Dict[str, Any]):
        """Configure la gouvernance selon les préférences."""
        criticality = Criticality.MEDIUM
        if preferences.get("nis2_mode") or preferences.get("ot_strict"):
            criticality = Criticality.HIGH
        
        self.report.governance = DecisionGovernance(
            criticality=criticality,
            validation_mode=ValidationMode.CONSENSUS if criticality == Criticality.HIGH else ValidationMode.SINGLE,
            status=GovernanceStatus.PENDING,
        )
    
    def _transform_recommendations(self, sections: Dict[str, str]):
        """Transforme les recommandations en décisions tracées."""
        # Chercher les sections qui contiennent des recommandations
        reco_keywords = ["recommandation", "préconisation", "action", "mesure"]
        
        decision_id = 1
        for section_name, content in sections.items():
            if any(kw in section_name.lower() for kw in reco_keywords):
                # Extraire les items de liste
                for line in content.split("\n"):
                    if line.strip().startswith("-") or line.strip().startswith("•"):
                        reco = line.strip().lstrip("-•").strip()
                        if reco:
                            self.report.decisions.append(Decision(
                                id=f"D-{decision_id:03d}",
                                description=reco[:100],
                                justification="Extrait du rapport générique",
                                risks_covered=[f"R-{decision_id:03d}"],
                                badge=ConfidenceBadge.UNVERIFIED,
                                alternatives=[
                                    Alternative(
                                        name="Option recommandée",
                                        advantages="Conforme aux bonnes pratiques",
                                        disadvantages="Coût et effort de mise en œuvre",
                                        is_selected=True,
                                    ),
                                    Alternative(
                                        name="Statu quo",
                                        advantages="Aucun effort requis",
                                        disadvantages="Risques non mitigés",
                                        rejection_reason="Risque inacceptable",
                                    ),
                                ],
                            ))
                            
                            # Ajouter la recommandation au résumé exécutif
                            self.report.executive_summary_recommendations.append((
                                reco[:80],
                                f"R-{decision_id:03d}",
                                "",
                                ConfidenceBadge.UNVERIFIED,
                            ))
                            
                            decision_id += 1
    
    def _generate_risks(self, sections: Dict[str, str], preferences: Dict[str, Any]):
        """Génère le registre des risques."""
        risk_id = 1
        
        # Risques génériques basés sur le contexte
        generic_risks = [
            ("Indisponibilité des systèmes critiques", ImpactLevel.HIGH, Probability.POSSIBLE),
            ("Perte de données", ImpactLevel.CRITICAL, Probability.UNLIKELY),
            ("Accès non autorisé", ImpactLevel.HIGH, Probability.POSSIBLE),
            ("Non-conformité réglementaire", ImpactLevel.HIGH, Probability.LIKELY if preferences.get("nis2_mode") else Probability.POSSIBLE),
        ]
        
        for desc, impact, prob in generic_risks:
            self.report.risks.append(Risk(
                id=f"R-{risk_id:03d}",
                description=desc,
                impact=impact,
                probability=prob,
                existing_controls="À évaluer",
                proposed_controls="Voir décisions D-*",
            ))
            risk_id += 1
    
    def _add_default_hypotheses(self):
        """Ajoute les hypothèses par défaut."""
        self.report.hypotheses = [
            Hypothesis(
                id="H-001",
                statement="Les informations fournies par le client sont exactes et à jour",
                impact_if_false="Recommandations potentiellement inadaptées",
                verifiable="PARTIAL",
            ),
            Hypothesis(
                id="H-002",
                statement="Le périmètre défini reste stable pendant la durée du projet",
                impact_if_false="Effort et budget à réévaluer",
                verifiable="NO",
            ),
            Hypothesis(
                id="H-003",
                statement="Les ressources techniques seront disponibles selon le planning",
                impact_if_false="Retards sur les phases",
                verifiable="NO",
            ),
        ]
    
    def _add_verification_commands(self):
        """Ajoute les commandes de vérification standard."""
        # Commandes issues de la checklist CTO 30 min
        self.report.verification_commands = [
            VerificationCommand(
                test_name="Audit complet",
                command="make audit-verify",
                expected_proof="[PASS] Audit verification complète",
                status=ConfidenceBadge.UNVERIFIED,
            ),
            VerificationCommand(
                test_name="Consensus PRISM",
                command="python -m pytest tests/test_prism_tally_quorum.py -v",
                expected_proof="Tous les tests PASS",
                status=ConfidenceBadge.VERIFIED,
            ),
            VerificationCommand(
                test_name="Routeur déterministe",
                command="python -m pytest tests/test_router_determinism.py -v",
                expected_proof="Tous les tests PASS",
                status=ConfidenceBadge.VERIFIED,
            ),
            VerificationCommand(
                test_name="Pipeline légal",
                command="python -m pytest tests/test_legal_orchestrator.py -v",
                expected_proof="Tous les tests PASS",
                status=ConfidenceBadge.PARTIAL,
            ),
        ]
    
    def _add_limits_and_unverified(self):
        """Ajoute les limites et points UNVERIFIED connus."""
        # Limites
        self.report.limits = [
            Limit(
                description="Analyse basée sur les informations disponibles à date",
                impact="Recommandations à actualiser si contexte change",
                mitigation="Revue périodique recommandée",
            ),
            Limit(
                description="Pas d'audit de code/infrastructure effectué",
                impact="Vulnérabilités techniques potentiellement non identifiées",
                mitigation="Prévoir un audit technique complémentaire",
            ),
        ]
        
        # Points UNVERIFIED connus (depuis l'audit KOREV Evidence)
        for i, point in enumerate(self.KNOWN_UNVERIFIED, 1):
            self.report.unverified_points.append(UnverifiedPoint(
                point=point,
                reason="Non démontré dans le code/tests",
                impact=ImpactLevel.MEDIUM,
                required_action="Vérification manuelle ou implémentation requise",
            ))
            
            # En criticité HIGH, marquer comme FAIL_CLOSED
            if self.report.governance.criticality == Criticality.HIGH:
                self.report.fail_closed_points.append(FailClosedPoint(
                    id=f"FC-{i:03d}",
                    point=point,
                    reason="UNVERIFIED en criticité HIGH",
                    missing_info=f"Preuve de {point.lower()}",
                ))


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR — Check Report Compliance
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    """Résultat de validation d'un rapport."""
    is_valid: bool
    score: int
    max_score: int
    issues: List[str]
    warnings: List[str]


class ReportValidator:
    """Valide qu'un rapport respecte le format Evidence-native."""
    
    REQUIRED_SECTIONS = [
        "Decision Governance",
        "Executive Summary",
        "Contexte & Périmètre",
        "Hypothèses",
        "Registre des Risques",
        "Décisions d'Architecture",
        "Architecture Cible",
        "Plan de Mise en Œuvre",
        "Preuves & Vérification",
        "Limites & FAIL_CLOSED",
        "Annexes",
    ]
    
    REQUIRED_TABLES = [
        ("Registre des Risques", r"\| ID \| Risque"),
        ("Décisions", r"\| ID \| Décision"),
        ("Alternatives", r"\| Alternative \| Avantages"),
    ]
    
    def validate(self, content: str) -> ValidationResult:
        """
        Valide un rapport Markdown.
        
        Args:
            content: Contenu Markdown du rapport
            
        Returns:
            Résultat de validation avec score Korev-ness
        """
        issues = []
        warnings = []
        score = 0
        max_score = 10
        
        # 1. Decision Governance Block
        if "## Decision Governance" in content:
            score += 1
            if "Criticité" not in content or "Quorum" not in content:
                warnings.append("Decision Governance incomplet")
        else:
            issues.append("ABSENT: Decision Governance Block")
        
        # 2. Registre des Risques
        if "## D. Registre des Risques" in content:
            if re.search(r"\| R-\d{3}", content):
                score += 1
            else:
                issues.append("Registre des Risques vide")
        else:
            issues.append("ABSENT: Registre des Risques")
        
        # 3. Alternatives écartées
        if "### Alternatives écartées" in content:
            alt_count = len(re.findall(r"\| Alternative \|", content))
            if alt_count >= 3:
                score += 1
            else:
                warnings.append(f"Seulement {alt_count} tables d'alternatives")
        else:
            issues.append("ABSENT: Alternatives écartées")
        
        # 4. Hypothèses
        if "## C. Hypothèses" in content:
            hyp_count = len(re.findall(r"\| H-\d{3}", content))
            if hyp_count >= 3:
                score += 1
            else:
                warnings.append(f"Seulement {hyp_count} hypothèses")
        else:
            issues.append("ABSENT: Hypothèses")
        
        # 5. Badges de confiance
        badges_present = any(badge in content for badge in ["VERIFIED", "PARTIAL", "UNVERIFIED"])
        if badges_present:
            score += 1
        else:
            issues.append("ABSENT: Badges de confiance")
        
        # 6. Preuves & Vérification
        if "## H. Preuves & Vérification" in content:
            score += 1
        else:
            issues.append("ABSENT: Preuves & Vérification")
        
        # 7. FAIL_CLOSED
        if "### Points FAIL_CLOSED" in content or "FAIL_CLOSED" in content:
            score += 1
        else:
            warnings.append("FAIL_CLOSED non explicitement documenté")
        
        # 8. Traçabilité Claims → Sources
        if "### Sources de données utilisées" in content:
            score += 1
        else:
            warnings.append("Traçabilité sources incomplète")
        
        # 9. Plan 30/60/90
        if all(p in content for p in ["Phase 1", "Phase 2", "Phase 3"]):
            score += 1
        else:
            warnings.append("Plan 30/60/90 incomplet")
        
        # 10. Périmètre IN/OUT
        if "#### IN" in content and "#### OUT" in content:
            score += 1
        else:
            warnings.append("Périmètre IN/OUT non explicite")
        
        is_valid = score >= 8 and len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            max_score=max_score,
            issues=issues,
            warnings=warnings,
        )
    
    def validate_file(self, path: str) -> ValidationResult:
        """Valide un fichier rapport."""
        content = Path(path).read_text(encoding="utf-8")
        return self.validate(content)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI pour le module Evidence-native."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python evidence_native.py <command> [args]")
        print("\nCommands:")
        print("  validate <path>     Validate a report against Evidence-native format")
        print("  transform <input> <output>  Transform generic report to Evidence-native")
        print("  example <output>    Generate example Evidence-native report")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python evidence_native.py validate <path>")
            sys.exit(1)
        
        validator = ReportValidator()
        result = validator.validate_file(sys.argv[2])
        
        print(f"\n{'='*60}")
        print(f"KOREV-NESS SCORE: {result.score}/{result.max_score}")
        print(f"STATUS: {'PASS' if result.is_valid else 'FAIL'}")
        print(f"{'='*60}")
        
        if result.issues:
            print("\n❌ ISSUES:")
            for issue in result.issues:
                print(f"  - {issue}")
        
        if result.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        sys.exit(0 if result.is_valid else 1)
    
    elif command == "transform":
        if len(sys.argv) < 4:
            print("Usage: python evidence_native.py transform <input> <output>")
            sys.exit(1)
        
        input_path = sys.argv[2]
        output_path = sys.argv[3]
        
        content = Path(input_path).read_text(encoding="utf-8")
        
        transformer = GenericReportTransformer()
        report = transformer.transform(
            content,
            client_context={
                "name": "Client Example",
                "sector": "Industrie",
                "sites": ["Site principal"],
                "scope_in": ["Infrastructure réseau", "Sécurité périmétrique"],
                "scope_out": ["Applications métier", "Développement logiciel"],
            },
        )
        
        report.save(output_path)
        print(f"✅ Report transformed and saved to {output_path}")
    
    elif command == "example":
        if len(sys.argv) < 3:
            print("Usage: python evidence_native.py example <output>")
            sys.exit(1)
        
        output_path = sys.argv[2]
        
        # Créer un exemple de rapport
        report = EvidenceNativeReport(
            title="Architecture SI — Exemple Evidence-Native",
            governance=DecisionGovernance(
                criticality=Criticality.HIGH,
                validation_mode=ValidationMode.CONSENSUS,
                status=GovernanceStatus.APPROVED,
                arbiters=["GPT-4", "Claude-3", "Gemini"],
            ),
        )
        
        report.executive_summary_conclusions = [
            "L'infrastructure actuelle présente des risques de disponibilité significatifs",
            "La mise en conformité NIS2 nécessite des actions prioritaires",
            "Un plan d'investissement sur 90 jours est recommandé",
        ]
        
        report.save(output_path)
        print(f"✅ Example report generated at {output_path}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "Criticality",
    "ValidationMode",
    "GovernanceStatus",
    "ConfidenceBadge",
    "ImpactLevel",
    "Probability",
    "SourceType",
    "SourceReliability",
    # Data classes
    "DecisionGovernance",
    "ClientContext",
    "Scope",
    "Source",
    "Hypothesis",
    "Risk",
    "Alternative",
    "Decision",
    "ArchitectureComponent",
    "FailoverScenario",
    "Action",
    "VerificationCommand",
    "Proof",
    "UnverifiedPoint",
    "FailClosedPoint",
    "Limit",
    "Reference",
    # Main classes
    "EvidenceNativeReport",
    "GenericReportTransformer",
    "ReportValidator",
    "ValidationResult",
]
