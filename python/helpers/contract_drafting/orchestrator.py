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

import hashlib
import logging
import re
import uuid
from typing import Dict, List, Optional

from python.helpers.contract_drafting.gate import run_gate
from python.helpers.contract_drafting.models import (
    ContractDraft,
    DraftAuditEntry,
    DraftingOutput,
    GateVerdict,
    GateVerdictEnum,
    VariableValidationResult,
)
from python.helpers.contract_drafting.templates import (
    get_template_pack,
    get_template_versions,
    render_template,
)

logger = logging.getLogger("contract_drafting.orchestrator")


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
# INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

# Allowed contract types — extensible
_ALLOWED_CONTRACT_TYPES = {"on_prem_licence"}

# Required variables for a minimal valid draft
_REQUIRED_VARIABLES = {"client_name", "editor_name", "software_name", "jurisdiction"}

# Forbidden characters/patterns in variable values (injection prevention)
_INJECTION_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\{\{"),  # Template injection
    re.compile(r"\$\{"),  # Template injection
    re.compile(r"__import__", re.IGNORECASE),
    re.compile(r"os\.system", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
]

# Max length per variable value (prevent abuse)
_MAX_VARIABLE_LENGTH = 2000


def validate_contract_variables(
    variables: Dict[str, str],
    contract_type: str = "on_prem_licence",
) -> VariableValidationResult:
    """Valide et assainit les variables d'entrée AVANT génération.
    
    Vérifie:
      1. Type de contrat autorisé
      2. Variables requises présentes
      3. Pas d'injection (XSS, template injection, code execution)
      4. Longueur maximale par variable
      5. Types corrects (str uniquement)
    
    Args:
        variables:     Dictionnaire variable_name → valeur
        contract_type: Type de contrat demandé
    
    Returns:
        VariableValidationResult avec is_valid, errors, warnings, sanitized_variables
    """
    errors = []  # type: List[str]
    warnings = []  # type: List[str]
    sanitized = {}  # type: Dict[str, str]

    # 1. Contract type
    if contract_type not in _ALLOWED_CONTRACT_TYPES:
        errors.append(
            f"Type de contrat non autorisé: '{contract_type}'. "
            f"Types autorisés: {_ALLOWED_CONTRACT_TYPES}"
        )

    # 2. Required variables
    missing = _REQUIRED_VARIABLES - set(variables.keys())
    for var in missing:
        warnings.append(f"Variable requise manquante: '{var}' — sera marquée [À COMPLÉTER]")

    # 3. Validate each variable
    for key, value in variables.items():
        # Type check
        if not isinstance(key, str) or not isinstance(value, str):
            errors.append(f"Variable '{key}' doit être de type str, reçu: {type(value).__name__}")
            continue

        # Length check
        if len(value) > _MAX_VARIABLE_LENGTH:
            errors.append(
                f"Variable '{key}' dépasse la longueur max ({len(value)} > {_MAX_VARIABLE_LENGTH})"
            )
            continue

        # Injection check
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(value):
                errors.append(
                    f"Variable '{key}' contient un pattern d'injection interdit: "
                    f"'{pattern.pattern}'"
                )
                break
        else:
            # Sanitize: strip leading/trailing whitespace, normalize internal spaces
            clean_value = " ".join(value.split())
            sanitized[key] = clean_value

    return VariableValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        sanitized_variables=sanitized,
    )


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
    """Pipeline complet: Validate → Generate → Gate → Output (fail-closed).
    
    HARDENED V2:
      - Validation des variables en entrée (injection, longueur, type)
      - Error handling complet avec audit log
      - Fail-closed strict: toute exception → REJECT
      - Template version tracking
    
    Args:
        variables:     Variables du contrat
        contract_type: Type de contrat
        max_retries:   Nombre max de tentatives de correction (V1: 0)
    
    Returns:
        DraftingOutput
    
    Raises:
        Jamais — fail-closed, retourne toujours un DraftingOutput
    """
    correlation_id = str(uuid.uuid4())
    audit = DraftAuditEntry(correlation_id=correlation_id, action="run_drafting_pipeline")

    try:
        # ─── STEP 0: Input validation (NEW) ───
        validation = validate_contract_variables(variables, contract_type)
        if not validation.is_valid:
            logger.warning(
                f"[{correlation_id}] Input validation FAILED: {validation.errors}"
            )
            audit.success = False
            audit.error = f"Validation errors: {validation.errors}"
            # Fail-closed: return rejected output
            error_draft = ContractDraft(
                sections={},
                variables=variables,
                disclaimer="",
                correlation_id=correlation_id,
            )
            error_findings = []
            from python.helpers.contract_drafting.models import LeakFinding, FindingSeverity
            for err in validation.errors:
                error_findings.append(LeakFinding(
                    severity=FindingSeverity.P0,
                    pattern="input_validation_failed",
                    context=err[:120],
                    recommendation="Corriger les variables d'entrée avant de relancer le pipeline",
                    section="INPUT",
                ))
            error_verdict = GateVerdict(
                verdict=GateVerdictEnum.REJECT,
                findings=error_findings,
                can_release=False,
                summary=f"REJETÉ — Validation des entrées échouée: {'; '.join(validation.errors)}",
            )
            return DraftingOutput(
                draft=error_draft,
                gate_verdict=error_verdict,
                gate_passed=False,
                gate_summary=error_verdict.summary,
                rendered_contract="",
                corrections_needed=[f"[INPUT] {e}" for e in validation.errors],
            )

        # Use sanitized variables
        safe_variables = validation.sanitized_variables
        # Log warnings (missing optional vars)
        for w in validation.warnings:
            logger.info(f"[{correlation_id}] Validation warning: {w}")

        # ─── STEP 1: Generate draft ───
        draft = generate_contract(safe_variables, contract_type)
        draft.correlation_id = correlation_id  # Ensure consistent correlation

        # Track template versions in audit
        try:
            versions = get_template_versions()
            audit.template_versions = {k: v.version for k, v in versions.items()}
        except Exception:
            pass  # Non-blocking

        # Compute variables hash for audit
        try:
            vars_str = str(sorted(safe_variables.items()))
            audit.variables_hash = hashlib.sha256(vars_str.encode()).hexdigest()[:16]
        except Exception:
            pass  # Non-blocking

        # ─── STEP 2: Gate audit ───
        verdict = gate_contract(draft)
        audit.verdict = verdict.verdict.value
        audit.findings_count = len(verdict.findings)

        # ─── STEP 3: Output ───
        if verdict.can_release:
            # Render the full contract
            rendered_parts = []
            section_order = ["CP", "CG", "ANNEXE_1", "ANNEXE_2", "ANNEXE_3",
                             "ANNEXE_4", "ANNEXE_5", "ANNEXE_6"]
            for section_name in section_order:
                if section_name in draft.sections:
                    rendered_parts.append(draft.sections[section_name])

            rendered_contract = "\n\n" + "=" * 60 + "\n\n".join(rendered_parts)

            logger.info(
                f"[{correlation_id}] Pipeline APPROVED — "
                f"P0: {verdict.p0_count()}, P1: {verdict.p1_count()}"
            )
            audit.success = True

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

            logger.info(
                f"[{correlation_id}] Pipeline REJECTED — "
                f"P0: {verdict.p0_count()}, P1: {verdict.p1_count()}"
            )
            audit.success = True  # Pipeline ran correctly, just rejected

            return DraftingOutput(
                draft=draft,
                gate_verdict=verdict,
                gate_passed=False,
                gate_summary=verdict.summary,
                rendered_contract="",  # Fail-closed: no contract output
                corrections_needed=corrections,
            )

    except Exception as exc:
        # ─── FAIL-CLOSED: Pipeline exception → REJECT ───
        logger.error(
            f"[{correlation_id}] Pipeline EXCEPTION (fail-closed): {exc}",
            exc_info=True,
        )
        audit.success = False
        audit.error = str(exc)[:200]

        error_draft = ContractDraft(
            sections={},
            variables=variables,
            disclaimer="",
            correlation_id=correlation_id,
        )
        from python.helpers.contract_drafting.models import LeakFinding, FindingSeverity
        error_verdict = GateVerdict(
            verdict=GateVerdictEnum.REJECT,
            findings=[LeakFinding(
                severity=FindingSeverity.P0,
                pattern="pipeline_exception",
                context=f"Exception interne: {str(exc)[:100]}",
                recommendation="Erreur interne du pipeline — contacter le support technique",
                section="SYSTEM",
            )],
            can_release=False,
            summary=f"REJETÉ — Erreur interne du pipeline (fail-closed). Correlation: {correlation_id}",
        )
        return DraftingOutput(
            draft=error_draft,
            gate_verdict=error_verdict,
            gate_passed=False,
            gate_summary=error_verdict.summary,
            rendered_contract="",
            corrections_needed=[f"[SYSTEM] Erreur interne: {str(exc)[:100]}"],
        )
