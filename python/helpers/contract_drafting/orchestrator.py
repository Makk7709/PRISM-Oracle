"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CONTRACT DRAFTING ORCHESTRATOR                                    ║
║                                                                              ║
║  Pipeline: Generate Draft → Gate Audit → Output (fail-closed)               ║
║                                                                              ║
║  Étapes:                                                                     ║
║    1. generate_contract()  — Rend les templates avec les variables          ║
║    2. gate_contract()      — Passe le draft par la Gate (leak guard)        ║
║    3. run_drafting_pipeline() — Pipeline complet                            ║
║                                                                              ║
║  Routage:                                                                    ║
║    detect_contract_drafting_intent() — Détecte si l'utilisateur veut        ║
║    un contrat (→ route vers legal_drafting_guarded)                          ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional

from python.helpers.contract_drafting.gate import run_gate
from python.helpers.contract_drafting.models import (
    ContractDraft,
    DraftingOutput,
    GateVerdict,
    GateVerdictEnum,
)
from python.helpers.contract_drafting.templates import (
    get_template_pack,
    render_template,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

_DISCLAIMER = "PROJET — À VALIDER PAR UN JURISTE QUALIFIÉ AVANT TOUTE SIGNATURE"

# DPA activation based on remote_access variable
_REMOTE_ACCESS_TRUE = {"true", "yes", "oui", "1"}


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT DETECTION (Router)
# ═══════════════════════════════════════════════════════════════════════════════

# Strong patterns: explicit contract drafting requests
_DRAFTING_STRONG_PATTERNS = [
    re.compile(r"r[eé]dig(?:e[zrs]?|er?)\s+(?:un|le|ce|mon|notre)\s+(?:contrat|accord|convention)", re.IGNORECASE),
    re.compile(r"produi(?:re|s|t|sez)\s+(?:un|le|ce)\s+contrat", re.IGNORECASE),
    re.compile(r"pr[eé]pare[zrs]?\s+(?:un|le|les|ce)\s+(?:contrat|conditions\s+g[eé]n[eé]rales)", re.IGNORECASE),
    re.compile(r"draft\s+(?:a|the|an?)?\s*(?:software\s+)?(?:contract|agreement|license|licence)", re.IGNORECASE),
    re.compile(r"contrat\s+(?:pr[eê]t\s+[àa]\s+signature|de\s+licence|logiciel)", re.IGNORECASE),
    re.compile(r"g[eé]n[eé]re[zrs]?\s+(?:un|le|ce)\s+contrat", re.IGNORECASE),
    re.compile(r"(?:cr[eé]e[zrs]?|[eé]tabli[rs]?)\s+(?:un|le|ce)\s+contrat", re.IGNORECASE),
]

# Exclusion patterns: analysis/information requests about contracts
_DRAFTING_EXCLUSION_PATTERNS = [
    re.compile(r"qu['\u2019]est[- ]ce\s+qu['\u2019]", re.IGNORECASE),
    re.compile(r"analyse[zrs]?\s+(?:ce|le|les|mon)\s+contrat", re.IGNORECASE),
    re.compile(r"expliqu[eé]", re.IGNORECASE),
    re.compile(r"(?:quel|quelle)\s+(?:est|sont)", re.IGNORECASE),
]


def detect_contract_drafting_intent(query: str) -> bool:
    """Détecte si la requête est une demande de rédaction de contrat.
    
    Retourne True UNIQUEMENT pour les demandes de rédaction/génération.
    Retourne False pour les demandes d'analyse, d'explication ou d'information.
    
    Args:
        query: La requête utilisateur
    
    Returns:
        True si l'intent est contract_drafting
    """
    # Check exclusions first
    for pattern in _DRAFTING_EXCLUSION_PATTERNS:
        if pattern.search(query):
            return False
    
    # Check strong patterns
    for pattern in _DRAFTING_STRONG_PATTERNS:
        if pattern.search(query):
            return True
    
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRACT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_contract(
    variables: Dict[str, str],
    contract_type: str = "on_prem_licence",
) -> ContractDraft:
    """Génère un brouillon de contrat en rendant les templates.
    
    Args:
        variables:     Dictionnaire variable_name → valeur
        contract_type: Type de contrat (actuellement seul "on_prem_licence")
    
    Returns:
        ContractDraft avec toutes les sections rendues
    """
    pack = get_template_pack()
    correlation_id = str(uuid.uuid4())
    
    # Determine DPA activation
    remote_access = variables.get("remote_access", "false").strip().lower()
    is_remote = remote_access in _REMOTE_ACCESS_TRUE
    
    # Select the right ANNEXE_4 template
    if is_remote:
        variables_with_dpa = dict(variables)
        variables_with_dpa.setdefault("dpa_status", "APPLICABLE — accès distant autorisé")
        variables_with_dpa.setdefault("data_types", "[À COMPLÉTER: types de données personnelles]")
        variables_with_dpa.setdefault("data_subjects", "[À COMPLÉTER: catégories de personnes]")
    else:
        # Use the non-applicable template
        from python.helpers.contract_drafting.templates import _TEMPLATE_ANNEXE_4_NOT_APPLICABLE
        pack = dict(pack)  # Copy to avoid modifying the original
        pack["ANNEXE_4"] = _TEMPLATE_ANNEXE_4_NOT_APPLICABLE
        variables_with_dpa = dict(variables)
        variables_with_dpa["dpa_status"] = "NON APPLICABLE"
    
    # Render all sections
    sections = {}
    for section_name, template in pack.items():
        sections[section_name] = render_template(template, variables_with_dpa)
    
    return ContractDraft(
        sections=sections,
        variables=variables,
        disclaimer=_DISCLAIMER,
        correlation_id=correlation_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GATE CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

def gate_contract(draft: ContractDraft) -> GateVerdict:
    """Passe un brouillon par la Gate d'audit.
    
    Args:
        draft: Le brouillon à auditer
    
    Returns:
        GateVerdict
    """
    return run_gate(draft)


# ═══════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_drafting_pipeline(
    variables: Dict[str, str],
    contract_type: str = "on_prem_licence",
    max_retries: int = 0,
) -> DraftingOutput:
    """Pipeline complet: Generate → Gate → Output (fail-closed).
    
    Si la Gate rejette et max_retries > 0, tente de corriger automatiquement
    (non implémenté dans V1 — fail-closed strict).
    
    Args:
        variables:     Variables du contrat
        contract_type: Type de contrat
        max_retries:   Nombre max de tentatives de correction (V1: 0)
    
    Returns:
        DraftingOutput
    """
    # Step 1: Generate draft
    draft = generate_contract(variables, contract_type)
    
    # Step 2: Gate audit
    verdict = gate_contract(draft)
    
    # Step 3: Output
    if verdict.can_release:
        # Render the full contract
        rendered_parts = []
        section_order = ["CP", "CG", "ANNEXE_1", "ANNEXE_2", "ANNEXE_3",
                         "ANNEXE_4", "ANNEXE_5", "ANNEXE_6"]
        for section_name in section_order:
            if section_name in draft.sections:
                rendered_parts.append(draft.sections[section_name])
        
        rendered_contract = "\n\n" + "=" * 60 + "\n\n".join(rendered_parts)
        
        return DraftingOutput(
            draft=draft,
            gate_verdict=verdict,
            gate_passed=True,
            gate_summary=verdict.summary,
            rendered_contract=rendered_contract,
        )
    else:
        # Fail-closed: output corrections only
        corrections = []
        for finding in verdict.findings:
            corrections.append(
                f"[{finding.severity.value}] {finding.pattern}: "
                f"{finding.recommendation} (section: {finding.section})"
            )
        
        return DraftingOutput(
            draft=draft,
            gate_verdict=verdict,
            gate_passed=False,
            gate_summary=verdict.summary,
            rendered_contract="",  # Fail-closed: no contract output
            corrections_needed=corrections,
        )
