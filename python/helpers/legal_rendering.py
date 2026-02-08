"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      LEGAL RENDERING — EVIDENCE                              ║
║                                                                              ║
║  Cabinet-grade templates for legal output rendering.                         ║
║                                                                              ║
║  STYLES:                                                                     ║
║  • INFO: Court, pédagogique, sources compactes                               ║
║  • OPERATIONAL: FIRAC complet + next_action + checklist                      ║
║  • BOARD: Executive memo + risques classés + décisions + points manquants    ║
║                                                                              ║
║  GUARANTEES:                                                                 ║
║  • Bandeau always in header                                                  ║
║  • Disclaimer always present                                                 ║
║  • Sources always present (non-refusal)                                      ║
║  • Citations + pinpoint + origin_url when available                          ║
║                                                                              ║
║  Version: 1.0.0 (P0.9 Premium Output)                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Any, Dict, List, Literal, Optional, Union
from datetime import datetime
import logging

from python.helpers.legal_pipeline import (
    LegalOutput,
    LegalOutputMode,
)

# P2.d: PDF rendering via evidence_document
try:
    from python.helpers.evidence_document import (
        Document,
        DocumentMetadata,
        parse_markdown,
        render_to_pdf,
        render_to_file,
        get_template,
    )
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    Document = None
    parse_markdown = None
    render_to_pdf = None
    render_to_file = None
    get_template = None

logger = logging.getLogger("legal_rendering")


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE STYLES
# ═══════════════════════════════════════════════════════════════════════════════

OutputStyle = Literal["info", "operational", "board"]


# ═══════════════════════════════════════════════════════════════════════════════
# BANNERS
# ═══════════════════════════════════════════════════════════════════════════════

BANNERS = {
    LegalOutputMode.APPROVED_POSITION: "✅ **POSITION JURIDIQUE VALIDÉE**\n*Consensus multi-arbitre atteint. Sources vérifiées.*",
    LegalOutputMode.SAFE_ANALYSIS: "🔒 **ANALYSE JURIDIQUE SÉCURISÉE**\n*Structure conforme. Vérification des sources recommandée.*",
    LegalOutputMode.REFUSAL_REQUEST_INFO: "⚠️ **INFORMATION INSUFFISANTE**\n*Des éléments manquent pour fournir une analyse juridique complète.*",
}


# ═══════════════════════════════════════════════════════════════════════════════
# DISCLAIMER
# ═══════════════════════════════════════════════════════════════════════════════

DISCLAIMER = """
---
> **Avertissement juridique** : Ce document garantit la **provenance** et la **traçabilité** 
> des sources citées, mais ne constitue pas un conseil juridique personnalisé. L'exhaustivité 
> et l'interprétation juridique ne sont pas garanties. Le droit opposable n'est authentifié 
> que sur les sites officiels (Légifrance, EUR-Lex).
"""


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE: INFO
# ═══════════════════════════════════════════════════════════════════════════════

def render_info_style(output: LegalOutput) -> str:
    """
    INFO style: Court, pédagogique, sources compactes.
    
    Target audience: General users seeking information.
    """
    lines = []
    
    # Banner
    lines.append(BANNERS.get(output.mode, ""))
    lines.append("")
    
    # Context bar (compact)
    context_parts = []
    if output.jurisdiction:
        context_parts.append(f"📍 {output.jurisdiction.upper()}")
    if output.risk_tier:
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(output.risk_tier, "⚪")
        context_parts.append(f"{risk_emoji} Risque {output.risk_tier}")
    if context_parts:
        lines.append(" | ".join(context_parts))
        lines.append("")
    
    # Answer (main content)
    lines.append("## Réponse")
    lines.append("")
    lines.append(output.answer)
    lines.append("")
    
    # Refusal specifics
    if output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO and output.missing_info:
        lines.append("### Informations manquantes")
        lines.append("")
        for info in output.missing_info:
            # Human-readable labels
            labels = {
                "facts_list": "Liste des faits du dossier",
                "jurisdiction": "Précision de la juridiction applicable",
                "jurisdiction_clarification": "Clarification FR/EU",
                "claims_required": "Claims juridiques explicites",
                "provenance_missing": "Sources avec provenance",
                "consensus_required": "Validation par consensus",
                "consensus_rejected": "Révision après rejet du consensus",
            }
            lines.append(f"- ❓ {labels.get(info, info)}")
        lines.append("")
    
    # Sources (compact)
    if output.citations and output.mode != LegalOutputMode.REFUSAL_REQUEST_INFO:
        lines.append("### Sources")
        lines.append("")
        for citation in output.citations[:5]:  # Max 5 for INFO
            lines.append(f"- 📖 {citation}")
        if len(output.citations) > 5:
            lines.append(f"- *... et {len(output.citations) - 5} autres sources*")
        lines.append("")
    
    # Audit reference (minimal)
    lines.append(f"*Réf: {output.audit_bundle_id}*")
    
    # Disclaimer
    lines.append(DISCLAIMER)
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE: OPERATIONAL
# ═══════════════════════════════════════════════════════════════════════════════

def render_operational_style(output: LegalOutput) -> str:
    """
    OPERATIONAL style: FIRAC complet + next_action + checklist.
    
    Target audience: Legal professionals, operations teams.
    """
    lines = []
    
    # Banner
    lines.append(BANNERS.get(output.mode, ""))
    lines.append("")
    
    # Context block
    lines.append("## Contexte")
    lines.append("")
    lines.append(f"| Paramètre | Valeur |")
    lines.append(f"|-----------|--------|")
    lines.append(f"| **Juridiction** | {output.jurisdiction or 'Non spécifiée'} |")
    lines.append(f"| **Niveau de risque** | {output.risk_tier or 'Non évalué'} |")
    lines.append(f"| **Portée** | {output.scope or 'Non définie'} |")
    lines.append(f"| **Statut** | {output.mode.value.replace('_', ' ').title()} |")
    if output.consensus_status:
        lines.append(f"| **Consensus** | {output.consensus_status} |")
    lines.append("")
    
    # Refusal handling
    if output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO:
        lines.append("## ⚠️ Analyse incomplète")
        lines.append("")
        lines.append(output.answer)
        lines.append("")
        
        if output.missing_info:
            lines.append("### Checklist des éléments manquants")
            lines.append("")
            for info in output.missing_info:
                lines.append(f"- [ ] {info}")
            lines.append("")
        
        lines.append(DISCLAIMER)
        return "\n".join(lines)
    
    # FIRAC Structure
    lines.append("## Structure FIRAC")
    lines.append("")
    
    # Facts
    lines.append("### 📋 Faits")
    lines.append("")
    if output.facts:
        for fact in output.facts:
            lines.append(f"- {fact}")
    else:
        lines.append("*Aucun fait explicitement identifié*")
    lines.append("")
    
    # Issue (implied from query/answer)
    lines.append("### ❓ Question juridique")
    lines.append("")
    lines.append(output.answer[:200] + "..." if len(output.answer) > 200 else output.answer)
    lines.append("")
    
    # Rules
    lines.append("### 📚 Règles applicables")
    lines.append("")
    if output.rules:
        for i, rule in enumerate(output.rules, 1):
            lines.append(f"{i}. {rule}")
    else:
        lines.append("*Aucune règle explicitement citée*")
    lines.append("")
    
    # Application
    lines.append("### ⚖️ Application")
    lines.append("")
    lines.append(output.application if output.application else "*Section application non renseignée*")
    lines.append("")
    
    # Conclusion/Risks
    if output.risks:
        lines.append("### ⚠️ Risques identifiés")
        lines.append("")
        for risk in output.risks:
            lines.append(f"- 🔴 {risk}")
        lines.append("")
    
    # Next Action (checklist)
    lines.append("### 📌 Prochaines étapes")
    lines.append("")
    if output.next_action:
        lines.append(f"- [ ] {output.next_action}")
    lines.append("- [ ] Vérifier les sources sur Légifrance")
    lines.append("- [ ] Consulter un professionnel du droit si nécessaire")
    lines.append("")
    
    # Sources (detailed)
    lines.append("### 📖 Sources")
    lines.append("")
    if output.citations:
        for i, citation in enumerate(output.citations, 1):
            prov = output.provenance[i-1] if i <= len(output.provenance) else {}
            source_type = prov.get("source", "").upper() if prov else ""
            lines.append(f"{i}. **{citation}** {f'[{source_type}]' if source_type else ''}")
    else:
        lines.append("*Aucune source citée*")
    lines.append("")
    
    # Audit
    lines.append("---")
    lines.append(f"📋 **Audit Bundle**: `{output.audit_bundle_id}`")
    if output.consensus_id:
        lines.append(f"🗳️ **Consensus**: `{output.consensus_id}` — {output.consensus_status}")
    lines.append(f"⚖️ **Judge**: {output.judge_verdict}")
    lines.append("")
    
    # Disclaimer
    lines.append(DISCLAIMER)
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE: BOARD
# ═══════════════════════════════════════════════════════════════════════════════

def render_board_style(output: LegalOutput) -> str:
    """
    BOARD style: Executive memo + risques classés + décisions + points manquants.
    
    Target audience: Board members, executives, strategic decision makers.
    """
    lines = []
    
    # Executive Header
    lines.append("# 📊 MÉMO JURIDIQUE — NIVEAU STRATÉGIQUE")
    lines.append("")
    lines.append(f"**Date**: {datetime.now().strftime('%d/%m/%Y')}")
    lines.append(f"**Référence**: {output.audit_bundle_id}")
    lines.append("")
    
    # Banner (prominent)
    lines.append("---")
    lines.append(BANNERS.get(output.mode, ""))
    lines.append("---")
    lines.append("")
    
    # Executive Summary
    lines.append("## 📝 Synthèse exécutive")
    lines.append("")
    
    # Status box
    status_emoji = {"approved_position": "✅", "safe_analysis": "🔒", "refusal_request_info": "⚠️"}.get(output.mode.value, "❓")
    lines.append(f"> **Statut**: {status_emoji} {output.mode.value.replace('_', ' ').upper()}")
    lines.append(f"> ")
    lines.append(f"> **Juridiction**: {output.jurisdiction or 'À confirmer'}")
    lines.append(f"> **Niveau de risque**: {output.risk_tier or 'Non évalué'}")
    lines.append(f"> **Portée décisionnelle**: {output.scope or 'Non définie'}")
    if output.consensus_status:
        lines.append(f"> **Consensus**: {output.consensus_status}")
    lines.append("")
    
    # Refusal handling (prominent for board)
    if output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO:
        lines.append("## ⚠️ ATTENTION — ANALYSE NON FINALISÉE")
        lines.append("")
        lines.append("L'analyse juridique ne peut être complétée en l'état. Les éléments suivants sont requis:")
        lines.append("")
        
        if output.missing_info:
            for info in output.missing_info:
                labels = {
                    "facts_list": "**Faits du dossier** — Description factuelle de la situation",
                    "jurisdiction": "**Juridiction** — Précision du droit applicable (FR/EU/autre)",
                    "claims_required": "**Claims juridiques** — Arguments juridiques structurés",
                    "provenance_missing": "**Provenance des sources** — Traçabilité des citations",
                    "consensus_required": "**Consensus** — Validation multi-arbitre requise",
                    "consensus_rejected": "**Révision** — Le consensus a été rejeté",
                }
                lines.append(f"1. {labels.get(info, info)}")
            lines.append("")
        
        lines.append("### Recommandation")
        lines.append("")
        lines.append("- Compléter les éléments manquants avant toute décision stratégique")
        lines.append("- Consulter le service juridique pour validation")
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)
    
    # Main Answer
    lines.append("## 📋 Analyse")
    lines.append("")
    lines.append(output.answer)
    lines.append("")
    
    # Structured Content (collapsed for board)
    if output.facts or output.rules:
        lines.append("<details>")
        lines.append("<summary>📚 Détail de l'analyse (FIRAC)</summary>")
        lines.append("")
        
        if output.facts:
            lines.append("### Faits retenus")
            for fact in output.facts:
                lines.append(f"- {fact}")
            lines.append("")
        
        if output.rules:
            lines.append("### Règles applicables")
            for rule in output.rules:
                lines.append(f"- {rule}")
            lines.append("")
        
        if output.application:
            lines.append("### Application")
            lines.append(output.application)
            lines.append("")
        
        lines.append("</details>")
        lines.append("")
    
    # Risk Matrix
    if output.risks:
        lines.append("## ⚠️ Matrice des risques")
        lines.append("")
        lines.append("| Risque | Niveau | Action requise |")
        lines.append("|--------|--------|----------------|")
        for i, risk in enumerate(output.risks, 1):
            # Classify risk level based on keywords
            level = "🔴 ÉLEVÉ" if any(kw in risk.lower() for kw in ["majeur", "critique", "élevé"]) else "🟡 MODÉRÉ"
            lines.append(f"| {risk[:50]}... | {level} | À évaluer |")
        lines.append("")
    
    # Decision Points
    lines.append("## 🎯 Points de décision")
    lines.append("")
    if output.next_action:
        lines.append(f"1. **Action immédiate**: {output.next_action}")
    lines.append("2. **Validation juridique**: Confirmer avec le département juridique")
    lines.append("3. **Documentation**: Archiver ce mémo dans le dossier stratégique")
    lines.append("")
    
    # Sources (summary for board)
    if output.citations:
        lines.append("## 📖 Sources principales")
        lines.append("")
        for citation in output.citations[:3]:  # Top 3 for board
            lines.append(f"- {citation}")
        if len(output.citations) > 3:
            lines.append(f"- *+ {len(output.citations) - 3} sources additionnelles (voir annexe)*")
        lines.append("")
    
    # Consensus Details
    if output.consensus_id:
        lines.append("## 🗳️ Validation par consensus")
        lines.append("")
        lines.append(f"- **ID Consensus**: {output.consensus_id}")
        lines.append(f"- **Statut**: {output.consensus_status}")
        if output.arbiter_votes:
            lines.append("- **Votes**:")
            for arbiter, vote in output.arbiter_votes.items():
                vote_emoji = "✅" if vote == "approve" else "❌" if vote == "reject" else "⚪"
                lines.append(f"  - {arbiter}: {vote_emoji} {vote}")
        lines.append("")
    
    # Audit Trail
    lines.append("---")
    lines.append("### 📋 Traçabilité")
    lines.append("")
    lines.append(f"- **Audit Bundle**: `{output.audit_bundle_id}`")
    lines.append(f"- **Judge Verdict**: {output.judge_verdict}")
    lines.append(f"- **Généré le**: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append("")
    
    # Disclaimer (prominent for board)
    lines.append(DISCLAIMER)
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def render_legal_output_markdown(
    output: LegalOutput,
    *,
    style: OutputStyle = "operational",
) -> str:
    """
    Render a LegalOutput to premium Markdown.
    
    Args:
        output: The LegalOutput to render
        style: Rendering style ("info", "operational", "board")
        
    Returns:
        Formatted Markdown string
        
    Guarantees:
    - Banner always in header
    - Disclaimer always present
    - Sources always present (non-refusal)
    """
    renderers = {
        "info": render_info_style,
        "operational": render_operational_style,
        "board": render_board_style,
    }
    
    renderer = renderers.get(style, render_operational_style)
    return renderer(output)


def render_legal_output_html(
    output: LegalOutput,
    *,
    style: OutputStyle = "operational",
) -> str:
    """
    P1.5: Render a LegalOutput to HTML with robust fallback.
    
    Uses markdown library if available, otherwise falls back to native HTML builder.
    
    GUARANTEES:
    - Banner always present
    - Disclaimer always present
    - Sources always present (non-refusal)
    """
    # Try markdown library first
    try:
        import markdown
        md_content = render_legal_output_markdown(output, style=style)
        html = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
    except ImportError:
        # Fallback: native HTML builder
        html = _render_html_native(output, style)
    
    # Wrap in styled container
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Analyse Juridique - KOREV Evidence</title>
    <style>
        .legal-output {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .legal-output h1 {{ color: #1A1A2E; border-bottom: 2px solid #1A1A2E; padding-bottom: 10px; }}
        .legal-output h2 {{ color: #2D3436; margin-top: 1.5em; }}
        .legal-output h3 {{ color: #636E72; }}
        .legal-output blockquote {{ border-left: 4px solid #DFE6E9; padding-left: 16px; margin-left: 0; color: #636E72; font-style: italic; }}
        .legal-output table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
        .legal-output th, .legal-output td {{ border: 1px solid #DFE6E9; padding: 8px 12px; text-align: left; }}
        .legal-output th {{ background-color: #F1F2F6; }}
        .legal-output .banner {{ padding: 16px; border-radius: 8px; margin-bottom: 20px; }}
        .legal-output .banner-approved {{ background-color: #D5F5E3; border: 1px solid #27AE60; }}
        .legal-output .banner-safe {{ background-color: #EBF5FB; border: 1px solid #3498DB; }}
        .legal-output .banner-refusal {{ background-color: #FDEBD0; border: 1px solid #F39C12; }}
        .legal-output .disclaimer {{ background-color: #F8F9FA; padding: 16px; border-radius: 4px; margin-top: 20px; font-size: 0.9em; color: #636E72; }}
        .legal-output .sources {{ margin-top: 20px; padding: 16px; background-color: #F1F2F6; border-radius: 4px; }}
        .legal-output .audit {{ font-size: 0.85em; color: #95A5A6; margin-top: 20px; padding-top: 10px; border-top: 1px solid #DFE6E9; }}
        .legal-style-board h1 {{ font-size: 1.8em; }}
        .legal-style-info {{ font-size: 0.95em; }}
    </style>
</head>
<body>
    <div class="legal-output legal-style-{style}">
        {html}
    </div>
</body>
</html>"""


def _render_html_native(output: LegalOutput, style: OutputStyle) -> str:
    """
    P1.5: Native HTML builder (fallback when markdown lib unavailable).
    
    GUARANTEES same as markdown version:
    - Banner always present
    - Disclaimer always present  
    - Sources always present (non-refusal)
    """
    lines = []
    
    # Banner
    banner_class = {
        LegalOutputMode.APPROVED_POSITION: "banner-approved",
        LegalOutputMode.SAFE_ANALYSIS: "banner-safe",
        LegalOutputMode.REFUSAL_REQUEST_INFO: "banner-refusal",
    }.get(output.mode, "banner-safe")
    
    banner_text = BANNERS.get(output.mode, "").replace("**", "").replace("*", "")
    lines.append(f'<div class="banner {banner_class}">{_escape_html(banner_text)}</div>')
    
    # Context bar
    if output.jurisdiction or output.risk_tier:
        lines.append('<p>')
        if output.jurisdiction:
            lines.append(f'<strong>Juridiction:</strong> {_escape_html(output.jurisdiction.upper())} | ')
        if output.risk_tier:
            lines.append(f'<strong>Risque:</strong> {_escape_html(output.risk_tier)} | ')
        if output.scope:
            lines.append(f'<strong>Portée:</strong> {_escape_html(output.scope)}')
        lines.append('</p>')
    
    # Main answer
    lines.append('<h2>Analyse</h2>')
    lines.append(f'<p>{_escape_html(output.answer)}</p>')
    
    # Missing info (for refusal)
    if output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO and output.missing_info:
        lines.append('<h3>Informations manquantes</h3>')
        lines.append('<ul>')
        for info in output.missing_info:
            lines.append(f'<li>{_escape_html(info)}</li>')
        lines.append('</ul>')
    
    # FIRAC sections (operational/board)
    if style in ("operational", "board") and output.mode != LegalOutputMode.REFUSAL_REQUEST_INFO:
        if output.facts:
            lines.append('<h3>Faits</h3><ul>')
            for fact in output.facts:
                lines.append(f'<li>{_escape_html(fact)}</li>')
            lines.append('</ul>')
        
        if output.rules:
            lines.append('<h3>Règles applicables</h3><ul>')
            for rule in output.rules:
                lines.append(f'<li>{_escape_html(rule)}</li>')
            lines.append('</ul>')
        
        if output.application:
            lines.append('<h3>Application</h3>')
            lines.append(f'<p>{_escape_html(output.application)}</p>')
        
        if output.risks:
            lines.append('<h3>Risques</h3><ul>')
            for risk in output.risks:
                lines.append(f'<li>{_escape_html(risk)}</li>')
            lines.append('</ul>')
    
    # Sources (always present for non-refusal)
    if output.citations and output.mode != LegalOutputMode.REFUSAL_REQUEST_INFO:
        lines.append('<div class="sources">')
        lines.append('<h3>Sources</h3><ul>')
        for citation in output.citations:
            lines.append(f'<li>{_escape_html(citation)}</li>')
        lines.append('</ul></div>')
    
    # Audit
    lines.append('<div class="audit">')
    lines.append(f'<strong>Réf:</strong> {_escape_html(output.audit_bundle_id)}')
    if output.consensus_status:
        lines.append(f' | <strong>Consensus:</strong> {_escape_html(output.consensus_status)}')
    lines.append('</div>')
    
    # Disclaimer (always present)
    disclaimer_text = DISCLAIMER.replace(">", "").replace("**", "").replace("*", "").strip()
    lines.append(f'<div class="disclaimer">{_escape_html(disclaimer_text)}</div>')
    
    return '\n'.join(lines)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED RENDERER (P1.5)
# ═══════════════════════════════════════════════════════════════════════════════

OutputFormat = Literal["md", "markdown", "html", "pdf"]


def render_legal_output(
    output: LegalOutput,
    *,
    format: OutputFormat = "md",
    style: Optional[OutputStyle] = None,
    output_path: Optional[str] = None,
) -> Union[str, bytes]:
    """
    P1.5/P2.d: Unified rendering function for legal outputs.
    
    Args:
        output: The LegalOutput to render
        format: Output format ("md", "markdown", "html", "pdf")
        style: Rendering style (auto-detected if None)
        output_path: For PDF, optional file path to write to
        
    Returns:
        Formatted string (Markdown/HTML) or bytes (PDF)
        
    GUARANTEES:
    - Banner always present
    - Disclaimer always present
    - Sources always present (non-refusal)
    """
    # Auto-detect style if not provided
    if style is None:
        style = detect_optimal_style(output)
    
    # Render based on format
    if format in ("md", "markdown"):
        return render_legal_output_markdown(output, style=style)
    elif format == "html":
        return render_legal_output_html(output, style=style)
    elif format == "pdf":
        return render_legal_output_pdf(output, style=style, output_path=output_path)
    else:
        raise ValueError(f"Unknown format: {format}")


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_optimal_style(output: LegalOutput) -> OutputStyle:
    """
    Automatically detect the optimal rendering style based on output metadata.
    
    Priority:
    1. BOARD scope => board style
    2. HIGH risk => board style (regardless of scope)
    3. OPERATIONAL scope => operational style
    4. MEDIUM risk => operational style
    5. Default (LOW/INFO) => info style
    
    Returns:
        Optimal style for the given output
    """
    # BOARD scope always gets board style
    if output.scope == "board":
        return "board"
    
    # HIGH risk escalates to board style
    if output.risk_tier == "high":
        return "board"
    
    # OPERATIONAL scope or MEDIUM risk gets operational style
    if output.scope == "operational":
        return "operational"
    if output.risk_tier == "medium":
        return "operational"
    
    # Default: info style
    return "info"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# PDF RENDERING (P2.d)
# ═══════════════════════════════════════════════════════════════════════════════

def render_legal_output_pdf(
    output: LegalOutput,
    *,
    style: Optional[OutputStyle] = None,
    output_path: Optional[str] = None,
) -> Union[bytes, str]:
    """
    P2.d: Render a LegalOutput to PDF using evidence_document.
    
    Args:
        output: The LegalOutput to render
        style: Rendering style (auto-detected if None)
        output_path: If provided, writes to file and returns path
        
    Returns:
        PDF bytes if no output_path, otherwise file path
        
    GUARANTEES:
    - Uses "legal" template for professional appearance
    - Banner always present
    - Disclaimer always present
    - Sources always present (non-refusal)
    """
    if not PDF_AVAILABLE:
        raise ImportError("PDF rendering requires python.helpers.evidence_document")
    
    # Auto-detect style
    if style is None:
        style = detect_optimal_style(output)
    
    # Generate markdown first
    md_content = render_legal_output_markdown(output, style=style)
    
    # Parse markdown to Document AST
    try:
        doc = parse_markdown(
            content=md_content,
            title=_get_pdf_title(output),
            template="legal",  # Use legal template
            author="KOREV Evidence",
            confidentiality="internal",
        )
        
        # Add metadata
        doc.metadata.reference = output.audit_bundle_id
        doc.metadata.date = datetime.now().strftime("%Y-%m-%d")
        
        # Set options based on output
        doc.show_sources = bool(output.citations)
        doc.show_audit_trail = True
        
        # Render
        if output_path:
            return render_to_file(doc, output_path)
        else:
            return render_to_pdf(doc)
            
    except Exception as e:
        logger.error(f"PDF rendering error: {e}")
        raise


def _get_pdf_title(output: LegalOutput) -> str:
    """Generate PDF title based on output."""
    mode_titles = {
        LegalOutputMode.APPROVED_POSITION: "Position Juridique Validée",
        LegalOutputMode.SAFE_ANALYSIS: "Analyse Juridique Sécurisée",
        LegalOutputMode.REFUSAL_REQUEST_INFO: "Demande d'Information Complémentaire",
    }
    base_title = mode_titles.get(output.mode, "Analyse Juridique")
    
    if output.scope:
        scope_labels = {
            "info": "",
            "operational": " — Document Opérationnel",
            "board": " — Mémo Direction",
        }
        base_title += scope_labels.get(output.scope, "")
    
    return base_title


def is_pdf_available() -> bool:
    """Check if PDF rendering is available."""
    return PDF_AVAILABLE


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # P1.5: Unified renderer
    "render_legal_output",
    # Main renderer
    "render_legal_output_markdown",
    "render_legal_output_html",
    # P2.d: PDF renderer
    "render_legal_output_pdf",
    "is_pdf_available",
    # Style detection
    "detect_optimal_style",
    # Types
    "OutputStyle",
    "OutputFormat",
    # Individual renderers
    "render_info_style",
    "render_operational_style",
    "render_board_style",
    # Constants
    "BANNERS",
    "DISCLAIMER",
    # Availability
    "PDF_AVAILABLE",
]
