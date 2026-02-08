"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           GATE D'AUDIT — Fail-Closed Contract Gate (HARDENED V2)            ║
║                                                                              ║
║  Pipeline: Draft → GATE → Output                                            ║
║                                                                              ║
║  CHECKS (V2):                                                                ║
║    1. Disclaimer obligatoire                                                 ║
║    2. Leak Guard (P0/P1/P2 patterns)                                        ║
║    3. Citation verification (Légifrance index)                              ║
║    4. Template staleness check (> 12 mois = P1)                            ║
║    5. Section completeness (toutes les sections requises)                   ║
║                                                                              ║
║  INVARIANTS:                                                                 ║
║    1. P0 trouvé ⟹ REJECT (can_release = False)                             ║
║    2. Disclaimer absent ⟹ REJECT                                            ║
║    3. can_release = True ⟺ verdict = APPROVE                               ║
║    4. Fail-closed : tout doute ⟹ REJECT                                    ║
║    5. Exception interne ⟹ REJECT (jamais APPROVE par défaut)               ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from python.helpers.contract_drafting.leak_guard import scan_for_leaks_by_section
from python.helpers.contract_drafting.models import (
    ContractDraft,
    FindingSeverity,
    GateVerdict,
    GateVerdictEnum,
    LeakFinding,
)

logger = logging.getLogger("contract_drafting.gate")


# ═══════════════════════════════════════════════════════════════════════════════
# CITATION VERIFICATION — Bridge to Légifrance Index
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern pour extraire des citations complètes (article + code)
# NOTE: "articles?" gère le singulier ET le pluriel.
_CITATION_FULL_PATTERNS = [
    # "art. 1170 C. civ." / "articles 1240 et 1241 du Code civil"
    re.compile(
        r"art(?:icles?)?\.?\s*"
        r"([LRDA]?\.?\s*[\d][\d.\-]*(?:\s*(?:et\s+s(?:uiv)?\.?))?)"
        r"\s+(?:du\s+|de\s+|et\s+\S+\s+(?:du\s+|de\s+))?"
        r"(C(?:ode)?\.\s*(?:civ|com|pén|trav|conso|urb|env|ass)\.?"
        r"|Code\s+(?:civil|de\s+commerce|pénal|du\s+travail|de\s+la\s+consommation"
        r"|de\s+la\s+propriété\s+intellectuelle|de\s+l'environnement)"
        r"|CPI|CGI)",
        re.IGNORECASE,
    ),
    # "articles 1240 et 1241 du Code civil" → capture second article too
    re.compile(
        r"(?:et|,)\s+"
        r"(\d[\d.\-]*)"
        r"\s+(?:du\s+|de\s+)?"
        r"(C(?:ode)?\.\s*(?:civ|com|pén|trav|conso|urb|env|ass)\.?"
        r"|Code\s+(?:civil|de\s+commerce|pénal|du\s+travail|de\s+la\s+consommation"
        r"|de\s+la\s+propriété\s+intellectuelle|de\s+l'environnement)"
        r"|CPI|CGI)",
        re.IGNORECASE,
    ),
    # "article 28 du RGPD"
    re.compile(
        r"art(?:icles?)?\.?\s*(\d{1,3})\s+(?:du\s+)?(RGPD|Règlement\s+\(UE\)\s+\d{4}/\d+)",
        re.IGNORECASE,
    ),
    # "art. L.122-6-1 CPI" / "art. L.441-10 C. com."
    re.compile(
        r"art(?:icles?)?\.?\s*"
        r"([LRDA]\.?\s*[\d][\d.\-]+(?:-\d+)?)"
        r"\s+(?:du\s+)?"
        r"(C\.\s*(?:civ|com|pén|trav|conso|urb|env|ass)\.?|CPI|CGI)",
        re.IGNORECASE,
    ),
]

# Map abréviations → noms complets pour normalisation
_CODE_ABBREVIATIONS = {
    "c. civ": "Code civil",
    "c.civ": "Code civil",
    "code civil": "Code civil",
    "cc": "Code civil",
    "c. com": "Code de commerce",
    "c.com": "Code de commerce",
    "code de commerce": "Code de commerce",
    "c. pén": "Code pénal",
    "c.pén": "Code pénal",
    "code pénal": "Code pénal",
    "c. trav": "Code du travail",
    "c.trav": "Code du travail",
    "code du travail": "Code du travail",
    "c. conso": "Code de la consommation",
    "c.conso": "Code de la consommation",
    "code de la consommation": "Code de la consommation",
    "cpi": "Code de la propriété intellectuelle",
    "code de la propriété intellectuelle": "Code de la propriété intellectuelle",
    "cgi": "Code général des impôts",
    "rgpd": "RGPD",
}


def _normalize_citation(article: str, code_abbrev: str) -> str:
    """Normalise une citation extraite en format standard pour validate_citation().
    
    Ex: ("1170", "C. civ.") → "Code civil, art. 1170"
        ("L.441-10", "C. com.") → "Code de commerce, art. L441-10"
        ("28", "RGPD") → "RGPD art. 28"
    """
    # Clean article number
    article_clean = article.strip().replace(" ", "")
    
    # Resolve code abbreviation
    code_lower = code_abbrev.lower().rstrip(".")
    code_full = _CODE_ABBREVIATIONS.get(code_lower, code_abbrev)
    
    if code_full == "RGPD":
        return f"RGPD art. {article_clean}"
    return f"{code_full}, art. {article_clean}"


def _normalize_article_number(article: str) -> str:
    """Normalise un numéro d'article pour la recherche FTS5.
    
    Supprime les points après les préfixes L/R/D/A pour matcher
    les deux formats (L.441-10 et L441-10).
    """
    # "L.441-10" → "L441-10", "D.441-5" → "D441-5"
    return re.sub(r'^([LRDA])\.', r'\1', article.strip())


def _try_legifrance_index_lookup(article: str, code_name: str) -> Optional[bool]:
    """Tente une vérification dans l'index FTS5 Légifrance.
    
    Strategy:
      1. Normalize the article number (strip dots after L/R/D/A prefix).
      2. Search FTS5 by article number only (citations use abbreviations
         like "C. civ." while code_name is "Code civil" — avoid mismatch).
      3. Among the FTS5 results, verify that the code_name matches the
         document metadata (docs.code_name column) for at least one hit.
      4. If FTS5 misses, fall back to direct SQL lookup on docs table.
    
    Returns:
        True  si trouvé dans l'index
        False si cherché dans un index peuplé mais non trouvé
        None  si l'index n'est pas disponible OU est vide (pas encore ingéré)
    """
    try:
        from python.legal_sources.indexing import LegalIndex
        from pathlib import Path
        import os
        import sqlite3
        
        # Determine index path
        index_path = os.environ.get("LEGAL_INDEX_PATH", "data/legal/index")
        index_dir = Path(index_path)
        db_file = index_dir / "legal_index.sqlite"
        
        if not db_file.exists():
            logger.debug(f"Légifrance index not found at {db_file}")
            return None
        
        # ─── CHECK: index must be populated (not empty) ───
        conn = sqlite3.connect(str(db_file))
        try:
            doc_count = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        except sqlite3.OperationalError:
            doc_count = 0
        finally:
            conn.close()
        
        if doc_count == 0:
            logger.debug(
                f"Légifrance index at {db_file} is EMPTY (0 docs) — "
                f"ingestion required. Treating as unavailable."
            )
            return None
        
        index = LegalIndex(index_dir)

        # Normalize article number: "L.441-10" → "L441-10"
        article_normalized = _normalize_article_number(article)
        code_lower = code_name.lower().strip()

        # ─── STEP A: FTS5 search by article number ───
        results = index.search(article_normalized, source="legi", limit=10)
        
        # ─── STEP B: Cross-check code_name via docs metadata ───
        conn2 = sqlite3.connect(str(db_file))
        conn2.row_factory = sqlite3.Row
        try:
            if results:
                for r in results:
                    row = conn2.execute(
                        "SELECT code_name, article_number FROM docs WHERE doc_id = ?",
                        (r.doc_id,)
                    ).fetchone()
                    if row:
                        db_code = (row["code_name"] or "").lower().strip()
                        if db_code == code_lower:
                            logger.debug(
                                f"Légifrance INDEX VERIFIED (FTS5): art. {article} {code_name} "
                                f"→ doc_id={r.doc_id}"
                            )
                            return True

            # ─── STEP C: Direct SQL fallback (handles FTS5 tokenization gaps) ───
            # Try both "L.441-10" and "L441-10" variants
            variants = {article.strip(), article_normalized}
            for art_variant in variants:
                row = conn2.execute(
                    "SELECT doc_id, article_number FROM docs "
                    "WHERE article_number = ? AND LOWER(code_name) = ?",
                    (art_variant, code_lower),
                ).fetchone()
                if row:
                    logger.debug(
                        f"Légifrance INDEX VERIFIED (SQL): art. {article} {code_name} "
                        f"→ doc_id={row['doc_id']}"
                    )
                    return True
        finally:
            conn2.close()

        logger.debug(
            f"Légifrance INDEX MISS: article='{article}' (normalized='{article_normalized}') "
            f"code='{code_name}' → not found"
        )
        return False
            
    except Exception as e:
        logger.debug(f"Légifrance index lookup error: {e}")
        return None


def verify_legal_citations(sections: Dict[str, str]) -> List[LeakFinding]:
    """Vérifie que les références légales dans le contrat sont valides.
    
    Stratégie de vérification (par priorité):
      1. Index FTS5 Légifrance (si disponible) → VERIFIED / UNVERIFIED
      2. legal_citations_db.validate_citation() → validation de format
      3. Si aucun disponible → citation marquée UNVERIFIED (P1)
    
    IMPORTANT: Les citations non vérifiables sont P1 (warning),
    pas P0 (bloquant). La vérification est conservative.
    
    Args:
        sections: Dict section_name → texte du contrat
    
    Returns:
        Liste de LeakFinding pour les citations problématiques
    """
    findings = []  # type: List[LeakFinding]
    verified_citations = set()  # type: set
    
    # Try loading validate_citation
    _validate_citation = None
    try:
        from python.helpers.legal_citations_db import validate_citation as _vc
        _validate_citation = _vc
    except ImportError:
        logger.debug("legal_citations_db not available")
    
    # Track matched spans to prevent overlapping patterns from producing
    # duplicate findings for the same physical citation.
    matched_spans = {}  # type: Dict[str, set]  # section → set of (start, end)
    
    for section_name, section_text in sections.items():
        if section_name not in matched_spans:
            matched_spans[section_name] = set()
        
        for pattern in _CITATION_FULL_PATTERNS:
            for match in pattern.finditer(section_text):
                # ─── DEDUP by position: skip if this span overlaps ───
                span = (match.start(), match.end())
                overlaps = any(
                    not (span[1] <= existing[0] or span[0] >= existing[1])
                    for existing in matched_spans[section_name]
                )
                if overlaps:
                    continue
                matched_spans[section_name].add(span)
                
                article_part = match.group(1).strip()
                code_part = match.group(2).strip()
                
                # Normalize citation
                normalized = _normalize_citation(article_part, code_part)
                
                # Deduplicate by normalized form
                if normalized in verified_citations:
                    continue
                verified_citations.add(normalized)
                
                # ─── STEP 1: Try Légifrance FTS5 index ───
                code_full = _CODE_ABBREVIATIONS.get(
                    code_part.lower().rstrip("."), code_part
                )

                # RGPD / EU regulations: NOT in Légifrance index — skip index lookup
                if code_full in ("RGPD",) or code_full.startswith("Règlement"):
                    # Accept RGPD citations by format — they are EU law, not in our index
                    logger.debug(f"Citation EU/RGPD accepted by format: {normalized}")
                    continue

                index_result = _try_legifrance_index_lookup(article_part, code_full)
                
                if index_result is True:
                    # Found in Légifrance index → VERIFIED, no finding
                    logger.debug(f"Citation VERIFIED via Légifrance index: {normalized}")
                    continue
                
                if index_result is False:
                    # Searched but NOT found in index → P1
                    findings.append(LeakFinding(
                        severity=FindingSeverity.P1,
                        pattern="citation_not_in_legifrance_index",
                        context=f"'{normalized}' non trouvé dans l'index Légifrance",
                        recommendation=(
                            f"L'article '{normalized}' n'a pas été trouvé dans l'index Légifrance local. "
                            f"Vérifier sur legifrance.gouv.fr qu'il est en vigueur."
                        ),
                        section=section_name,
                        legal_ref=normalized,
                    ))
                    continue
                
                # ─── STEP 2: Index not available, fall back to format validation ───
                if _validate_citation is not None:
                    try:
                        result = _validate_citation(normalized)
                        if result.is_valid and result.confidence >= 0.8:
                            # Format valid with high confidence → OK
                            logger.debug(f"Citation FORMAT VALID: {normalized} (conf={result.confidence})")
                            continue
                        elif result.is_valid:
                            # Valid but low confidence → P1 warning
                            findings.append(LeakFinding(
                                severity=FindingSeverity.P1,
                                pattern="citation_low_confidence",
                                context=f"'{normalized}' — format valide mais confiance faible ({result.confidence:.1f})",
                                recommendation=(
                                    f"Vérifier '{normalized}' sur legifrance.gouv.fr. "
                                    f"{'Note: ' + result.warning if result.warning else ''}"
                                ),
                                section=section_name,
                                legal_ref=normalized,
                            ))
                            continue
                    except Exception as e:
                        logger.debug(f"validate_citation error for '{normalized}': {e}")
                
                # ─── STEP 3: No index, no validator → UNVERIFIED ───
                findings.append(LeakFinding(
                    severity=FindingSeverity.P1,
                    pattern="citation_unverified",
                    context=f"'{normalized}' — non vérifiable (index Légifrance indisponible)",
                    recommendation=(
                        f"L'index Légifrance n'est pas disponible. "
                        f"Vérifier '{normalized}' manuellement sur legifrance.gouv.fr"
                    ),
                    section=section_name,
                    legal_ref=normalized,
                ))
    
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE STALENESS CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def check_template_staleness() -> List[LeakFinding]:
    """Vérifie si des templates n'ont pas été revus depuis > 12 mois.
    
    Templates périmés → P1 (warning, non bloquant).
    
    Returns:
        Liste de LeakFinding P1 pour les templates périmés
    """
    findings = []  # type: List[LeakFinding]
    try:
        from python.helpers.contract_drafting.templates import get_stale_templates
        stale = get_stale_templates()
        for tv in stale:
            findings.append(LeakFinding(
                severity=FindingSeverity.P1,
                pattern="template_stale",
                context=(
                    f"Template {tv.section} v{tv.version} — "
                    f"dernière revue: {tv.last_review_date} ({tv.days_since_review()} jours)"
                ),
                recommendation=(
                    f"Le template {tv.section} n'a pas été revu depuis {tv.days_since_review()} jours. "
                    f"Planifier une revue juridique."
                ),
                section=tv.section,
            ))
    except Exception as e:
        logger.debug(f"Template staleness check failed: {e}")
    
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION COMPLETENESS CHECK
# ═══════════════════════════════════════════════════════════════════════════════

_REQUIRED_SECTIONS = {"CP", "CG", "ANNEXE_1", "ANNEXE_2", "ANNEXE_3",
                      "ANNEXE_4", "ANNEXE_5", "ANNEXE_6"}


def check_section_completeness(sections: Dict[str, str]) -> List[LeakFinding]:
    """Vérifie que toutes les sections requises sont présentes et non vides.
    
    Section manquante → P0 (bloquant).
    Section vide → P0 (bloquant).
    
    Args:
        sections: Dict section_name → texte
    
    Returns:
        Liste de LeakFinding
    """
    findings = []  # type: List[LeakFinding]
    
    for section in _REQUIRED_SECTIONS:
        if section not in sections:
            findings.append(LeakFinding(
                severity=FindingSeverity.P0,
                pattern="section_missing",
                context=f"Section '{section}' absente du contrat",
                recommendation=f"Ajouter la section '{section}' au brouillon",
                section=section,
            ))
        elif not sections[section].strip():
            findings.append(LeakFinding(
                severity=FindingSeverity.P0,
                pattern="section_empty",
                context=f"Section '{section}' présente mais vide",
                recommendation=f"Générer le contenu de la section '{section}'",
                section=section,
            ))
    
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GATE FUNCTION (HARDENED V2)
# ═══════════════════════════════════════════════════════════════════════════════

def run_gate(draft: ContractDraft) -> GateVerdict:
    """Exécute la gate d'audit sur un brouillon de contrat.
    
    HARDENED V2 — 5 checks:
        1. Disclaimer obligatoire
        2. Leak Guard (patterns P0/P1)
        3. Citation verification (Légifrance)
        4. Template staleness
        5. Section completeness
    
    INVARIANTS ENFORCED:
        - P0 trouvé ⟹ REJECT (can_release = False)
        - Disclaimer absent ⟹ REJECT
        - can_release = True ⟺ verdict = APPROVE
        - Exception ⟹ REJECT (fail-closed)
    
    Args:
        draft: Le brouillon de contrat à auditer
    
    Returns:
        GateVerdict avec verdict, findings et can_release
    """
    try:
        findings = []  # type: List[LeakFinding]
        reject_reasons = []  # type: List[str]

        # ─── CHECK 1: Disclaimer obligatoire ───
        if not draft.disclaimer or not draft.disclaimer.strip():
            reject_reasons.append("Disclaimer absent ou vide")
            findings.append(LeakFinding(
                severity=FindingSeverity.P0,
                pattern="disclaimer_missing",
                context="Le brouillon ne contient pas de disclaimer 'PROJET — à valider'",
                recommendation="Ajouter le disclaimer: 'PROJET — À VALIDER PAR UN JURISTE QUALIFIÉ'",
                section="METADATA",
            ))

        # ─── CHECK 2: Scan Leak Guard sur toutes les sections ───
        leak_findings = scan_for_leaks_by_section(draft.sections)
        findings.extend(leak_findings)

        # ─── CHECK 3: Citation verification (NEW) ───
        citation_findings = verify_legal_citations(draft.sections)
        findings.extend(citation_findings)

        # ─── CHECK 4: Template staleness (NEW) ───
        stale_findings = check_template_staleness()
        findings.extend(stale_findings)

        # ─── CHECK 5: Section completeness (NEW) ───
        completeness_findings = check_section_completeness(draft.sections)
        findings.extend(completeness_findings)

        # ─── EVALUATE ───
        has_p0 = any(f.severity == FindingSeverity.P0 for f in findings)
        p0_count = sum(1 for f in findings if f.severity == FindingSeverity.P0)
        p1_count = sum(1 for f in findings if f.severity == FindingSeverity.P1)

        if has_p0:
            reject_reasons.append(f"{p0_count} finding(s) P0 bloquant(s)")

        # ─── VERDICT ───
        if reject_reasons:
            return GateVerdict(
                verdict=GateVerdictEnum.REJECT,
                findings=findings,
                can_release=False,  # INVARIANT: REJECT ⟹ can_release = False
                summary=f"REJETÉ — {'; '.join(reject_reasons)}. "
                        f"P0: {p0_count}, P1: {p1_count}. "
                        f"Corrections requises avant release.",
            )

        # Pas de P0, pas de reject — APPROVE
        summary_parts = ["APPROUVÉ"]
        if p1_count > 0:
            summary_parts.append(f"avec {p1_count} avertissement(s) P1")

        return GateVerdict(
            verdict=GateVerdictEnum.APPROVE,
            findings=findings,
            can_release=True,  # INVARIANT: APPROVE ⟹ can_release = True
            summary=" ".join(summary_parts),
        )

    except Exception as exc:
        # ─── FAIL-CLOSED: Exception ⟹ REJECT ───
        logger.error(f"Gate exception (fail-closed): {exc}", exc_info=True)
        return GateVerdict(
            verdict=GateVerdictEnum.REJECT,
            findings=[LeakFinding(
                severity=FindingSeverity.P0,
                pattern="gate_exception",
                context=f"Exception interne de la gate: {str(exc)[:100]}",
                recommendation="Erreur interne — contacter le support technique",
                section="SYSTEM",
            )],
            can_release=False,
            summary=f"REJETÉ — Exception interne de la gate (fail-closed): {str(exc)[:80]}",
        )
