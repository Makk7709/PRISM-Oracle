"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — MARKDOWN RENDERER                      ║
║                                                                              ║
║  Convertit une LegalSafeResponse en markdown lisible pour l'utilisateur.    ║
║  Le rendu est strictement dérivé du JSON, aucune information ajoutée.       ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import Optional

from .legal_safe_schema import (
    Complexity,
    LegalBasis,
    LegalDomain,
    LegalSafeResponse,
    Reliability,
    ReviewTrigger,
    RiskLevel,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATES — Blocs de texte statiques
# ═══════════════════════════════════════════════════════════════════════════════

HEADER_TEMPLATE = """# 📋 Analyse Juridique — Mode Sécurisé

> **Juridiction** : {jurisdiction} | **Domaine** : {domain} | **Confiance** : {confidence}%
"""

DISCLAIMER_TEMPLATE = """
---

## ⚠️ Avertissement Important

{disclaimer_text}

"""

ESCALATION_TEMPLATE = """
---

## 🔴 Validation Humaine Requise

Cette analyse nécessite une validation par un professionnel du droit pour les raisons suivantes :

{triggers_list}

**Recommandation** : Consultez un avocat ou un juriste qualifié avant toute action.
"""

FALLBACK_TEMPLATE = """# ⚠️ Impossible de Traiter Cette Demande

{safe_message}

### Raison
{reason}

---

*{disclaimer}*
"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAPPINGS — Traductions des enums
# ═══════════════════════════════════════════════════════════════════════════════

DOMAIN_LABELS = {
    LegalDomain.DROIT_TRAVAIL: "Droit du travail",
    LegalDomain.DROIT_SOCIETES: "Droit des sociétés",
    LegalDomain.FISCAL: "Droit fiscal",
    LegalDomain.PENAL: "Droit pénal",
    LegalDomain.IMMOBILIER: "Droit immobilier",
    LegalDomain.RGPD_DONNEES: "Protection des données (RGPD)",
    LegalDomain.CONTRATS: "Droit des contrats",
    LegalDomain.CONTENTIEUX: "Contentieux",
    LegalDomain.IMMIGRATION: "Droit de l'immigration",
    LegalDomain.FAMILLE: "Droit de la famille",
    LegalDomain.CONSOMMATION: "Droit de la consommation",
    LegalDomain.PROPRIETE_INTELLECTUELLE: "Propriété intellectuelle",
    LegalDomain.ASSURANCE: "Droit des assurances",
    LegalDomain.BANCAIRE: "Droit bancaire",
    LegalDomain.ENVIRONNEMENT: "Droit de l'environnement",
    LegalDomain.ADMINISTRATIF: "Droit administratif",
    LegalDomain.UNKNOWN: "Non déterminé",
}

TRIGGER_LABELS = {
    ReviewTrigger.MISSING_CITATIONS: "Citations juridiques manquantes",
    ReviewTrigger.HIGH_IMPACT: "Impact potentiellement élevé",
    ReviewTrigger.CRIMINAL_LIABILITY: "Responsabilité pénale potentielle",
    ReviewTrigger.EMPLOYMENT_LAW_SENSITIVE: "Sujet sensible en droit du travail",
    ReviewTrigger.TAX_HEAVY: "Implications fiscales importantes",
    ReviewTrigger.IMMIGRATION_CASE: "Dossier d'immigration",
    ReviewTrigger.CONTRACT_HIGH_VALUE: "Contrat de valeur élevée",
    ReviewTrigger.NON_COMPETE_CLAUSE: "Clause de non-concurrence",
    ReviewTrigger.RGPD_INCIDENT: "Incident RGPD potentiel",
    ReviewTrigger.HARASSMENT_DISCRIMINATION: "Harcèlement ou discrimination",
    ReviewTrigger.TERMINATION_DISMISSAL: "Licenciement ou rupture de contrat",
    ReviewTrigger.LITIGATION_COURT: "Contentieux ou procédure judiciaire",
    ReviewTrigger.LOW_CONFIDENCE: "Niveau de confiance insuffisant",
    ReviewTrigger.JURISDICTION_UNKNOWN: "Juridiction non identifiée",
    ReviewTrigger.NO_RELIABLE_SOURCE: "Aucune source fiable",
    ReviewTrigger.CERTAINTY_REQUEST: "Demande de certitude juridique",
    ReviewTrigger.DOMAIN_PENAL: "Domaine pénal (escalade obligatoire)",
    ReviewTrigger.COMPLEXITY_EXPERT: "Complexité nécessitant un expert",
    ReviewTrigger.RESTRICTED_ACTIVITY: "Acte réservé aux professionnels",
    ReviewTrigger.CONFLICT_OF_INTEREST: "Conflit d'intérêts potentiel",
    ReviewTrigger.OUT_OF_SCOPE: "Hors du périmètre supporté",
    ReviewTrigger.ABUSE_DETECTED: "Utilisation anormale détectée",
}

RISK_ICONS = {
    RiskLevel.LOW: "🟢",
    RiskLevel.MEDIUM: "🟡",
    RiskLevel.HIGH: "🔴",
}

RELIABILITY_ICONS = {
    Reliability.HIGH: "✅",
    Reliability.MEDIUM: "⚠️",
    Reliability.LOW: "❓",
    Reliability.UNKNOWN: "❌",
}

COMPLEXITY_LABELS = {
    Complexity.SIMPLE: "Simple",
    Complexity.MEDIUM: "Moyen",
    Complexity.COMPLEX: "Complexe",
    Complexity.EXPERT_ONLY: "Expert requis",
}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS PURES — Rendu des sections
# ═══════════════════════════════════════════════════════════════════════════════

def render_response(response: LegalSafeResponse) -> str:
    """
    Rend une LegalSafeResponse en markdown lisible.
    
    Fonction pure : le markdown est strictement dérivé du JSON.
    
    Args:
        response: Réponse à rendre
        
    Returns:
        String markdown formatée
    """
    # Si fallback déclenché, utiliser le template fallback
    if response.fallback.triggered:
        return render_fallback(response)
    
    sections: list[str] = []
    
    # Header avec métadonnées clés
    sections.append(_render_header(response))
    
    # Conclusion (en premier pour l'essentiel)
    sections.append(_render_conclusion(response))
    
    # Ce que je peux dire / ne peux pas garantir
    sections.append(_render_certainty_sections(response))
    
    # Bases légales
    if response.legal_basis:
        sections.append(_render_legal_basis(response.legal_basis))
    
    # Analyse détaillée
    sections.append(_render_analysis(response))
    
    # Informations manquantes
    if response.facts.missing_info:
        sections.append(_render_missing_info(response))
    
    # Risques identifiés
    if response.analysis.risks:
        sections.append(_render_risks(response))
    
    # Escalade si nécessaire
    if response.safety.requires_human_review:
        sections.append(_render_escalation(response))
    
    # Disclaimer obligatoire
    sections.append(_render_disclaimer(response))
    
    # Métadonnées techniques (discret)
    sections.append(_render_meta(response))
    
    return "\n".join(sections)


def render_fallback(response: LegalSafeResponse) -> str:
    """Rend une réponse fallback."""
    return FALLBACK_TEMPLATE.format(
        safe_message=response.fallback.safe_message,
        reason=response.fallback.reason or "Raison non spécifiée",
        disclaimer=response.disclaimers.text_fr,
    )


def _render_header(response: LegalSafeResponse) -> str:
    """Rend l'en-tête."""
    domain_label = DOMAIN_LABELS.get(response.classification.domain, "Non déterminé")
    confidence_pct = int(response.conclusion.confidence * 100)
    
    return HEADER_TEMPLATE.format(
        jurisdiction=response.scope.jurisdiction_requested.value,
        domain=domain_label,
        confidence=confidence_pct,
    )


def _render_conclusion(response: LegalSafeResponse) -> str:
    """Rend la conclusion principale."""
    risk_icon = RISK_ICONS.get(response.safety.hallucination_risk, "⚪")
    
    return f"""
## 📌 Réponse

{response.conclusion.answer}

### Recommandation
{response.conclusion.recommendation}

**Niveau de risque d'erreur** : {risk_icon} {response.safety.hallucination_risk.value.capitalize()}
"""


def _render_certainty_sections(response: LegalSafeResponse) -> str:
    """Rend les sections 'ce que je peux dire' / 'ce que je ne peux pas garantir'."""
    
    # Ce que je peux dire = éléments avec confiance élevée
    can_say: list[str] = []
    cannot_guarantee: list[str] = []
    
    # Faits utilisateur avec haute confiance
    for fact in response.facts.provided_by_user:
        if fact.confidence >= 0.75:
            can_say.append(f"- {fact.text}")
        else:
            cannot_guarantee.append(f"- Interprétation du fait '{fact.id}' (confiance: {int(fact.confidence*100)}%)")
    
    # Hypothèses formulées
    for assumption in response.facts.assumptions:
        cannot_guarantee.append(f"- Hypothèse {assumption.id}: {assumption.text} (risque si faux: {assumption.risk.value})")
    
    # Bases légales incertaines
    for lb in response.legal_basis:
        if lb.reliability in [Reliability.LOW, Reliability.UNKNOWN]:
            cannot_guarantee.append(f"- Citation {lb.id}: {lb.citation} (fiabilité: {lb.reliability.value})")
        elif lb.reliability in [Reliability.HIGH, Reliability.MEDIUM]:
            can_say.append(f"- Référence: {lb.citation}")
    
    sections = []
    
    if can_say:
        sections.append("### ✅ Ce que je peux affirmer\n" + "\n".join(can_say))
    
    if cannot_guarantee:
        sections.append("### ⚠️ Ce que je ne peux pas garantir\n" + "\n".join(cannot_guarantee))
    
    return "\n\n".join(sections) if sections else ""


def _render_legal_basis(legal_basis: list[LegalBasis]) -> str:
    """Rend les bases légales."""
    lines = ["## 📚 Bases Légales Citées\n"]
    lines.append("| Réf. | Type | Citation | Fiabilité |")
    lines.append("|------|------|----------|-----------|")
    
    for lb in legal_basis:
        icon = RELIABILITY_ICONS.get(lb.reliability, "❓")
        citation = lb.citation
        if lb.version_date:
            citation += f" (v. {lb.version_date})"
        
        lines.append(f"| {lb.id} | {lb.type.value} | {citation} | {icon} {lb.reliability.value} |")
    
    return "\n".join(lines)


def _render_analysis(response: LegalSafeResponse) -> str:
    """Rend l'analyse détaillée."""
    lines = ["## 🔍 Analyse\n"]
    lines.append("### Raisonnement\n")
    
    for i, step in enumerate(response.analysis.reasoning_steps, 1):
        lines.append(f"{i}. {step}")
    
    if response.analysis.counterarguments:
        lines.append("\n### Arguments contraires à considérer\n")
        for arg in response.analysis.counterarguments:
            lines.append(f"- {arg}")
    
    return "\n".join(lines)


def _render_missing_info(response: LegalSafeResponse) -> str:
    """Rend les informations manquantes."""
    lines = ["## ❓ Informations Manquantes\n"]
    lines.append("Pour une réponse plus fiable, les informations suivantes seraient nécessaires :\n")
    
    for info in response.facts.missing_info:
        lines.append(f"**Question** : {info.question}")
        lines.append(f"- *Pourquoi* : {info.why_needed}")
        lines.append(f"- *Risque si absent* : {info.risk_if_missing}")
        lines.append("")
    
    return "\n".join(lines)


def _render_risks(response: LegalSafeResponse) -> str:
    """Rend les risques identifiés."""
    lines = ["## ⚠️ Risques Identifiés\n"]
    
    for risk in response.analysis.risks:
        icon = RISK_ICONS.get(risk.level, "⚪")
        lines.append(f"### {icon} {risk.id} — Niveau {risk.level.value.capitalize()}")
        lines.append(f"**Description** : {risk.description}")
        lines.append(f"**Mitigation** : {risk.mitigation}")
        lines.append("")
    
    return "\n".join(lines)


def _render_escalation(response: LegalSafeResponse) -> str:
    """Rend la section d'escalade."""
    triggers_list = "\n".join(
        f"- {TRIGGER_LABELS.get(t, t.value)}"
        for t in response.safety.review_triggers
    )
    
    return ESCALATION_TEMPLATE.format(triggers_list=triggers_list)


def _render_disclaimer(response: LegalSafeResponse) -> str:
    """Rend le disclaimer obligatoire."""
    return DISCLAIMER_TEMPLATE.format(disclaimer_text=response.disclaimers.text_fr)


def _render_meta(response: LegalSafeResponse) -> str:
    """Rend les métadonnées (discret)."""
    return f"""
<details>
<summary>📊 Métadonnées techniques</summary>

- **ID** : `{response.meta.correlation_id}`
- **Timestamp** : {response.meta.timestamp_utc}
- **Modèle** : {response.meta.provider} / {response.meta.model}
- **Température** : {response.meta.temperature}
- **Latence** : {response.meta.latency_ms}ms
- **Version schéma** : {response.meta.schema_version}

</details>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES — Rendu partiel
# ═══════════════════════════════════════════════════════════════════════════════

def render_quick_summary(response: LegalSafeResponse) -> str:
    """
    Rend un résumé court pour les logs ou notifications.
    
    Args:
        response: Réponse à résumer
        
    Returns:
        Résumé en une ligne
    """
    if response.fallback.triggered:
        return f"⚠️ FALLBACK: {response.fallback.reason}"
    
    escalation = "🔴 ESCALADE" if response.safety.requires_human_review else "🟢 OK"
    confidence = int(response.conclusion.confidence * 100)
    domain = DOMAIN_LABELS.get(response.classification.domain, "?")
    
    return f"{escalation} | {domain} | Confiance: {confidence}% | Triggers: {len(response.safety.review_triggers)}"


def render_audit_line(response: LegalSafeResponse) -> str:
    """
    Rend une ligne d'audit pour les logs NDJSON.
    
    Args:
        response: Réponse à auditer
        
    Returns:
        Ligne formatée pour log
    """
    return (
        f"[{response.meta.timestamp_utc}] "
        f"id={response.meta.correlation_id} "
        f"domain={response.classification.domain.value} "
        f"confidence={response.conclusion.confidence:.2f} "
        f"escalation={response.safety.requires_human_review} "
        f"triggers={len(response.safety.review_triggers)}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "render_response",
    "render_fallback",
    "render_quick_summary",
    "render_audit_line",
    "DOMAIN_LABELS",
    "TRIGGER_LABELS",
    "RISK_ICONS",
    "RELIABILITY_ICONS",
    "COMPLEXITY_LABELS",
]
