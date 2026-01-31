#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     KOREV Evidence — Validation du Dossier Stratégique Evidence-Grade        ║
║                                                                              ║
║  Loop de contrôle obligatoire avant livraison                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs" / "reports"


@dataclass
class ValidationResult:
    """Résultat d'une validation"""
    rule_id: str
    rule_name: str
    passed: bool
    details: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO


def validate_document(md_content: str) -> List[ValidationResult]:
    """Valide le document selon les règles Evidence-grade"""
    results = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 1: Chaque chiffre a une source OU une hypothèse explicitée
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Trouver les chiffres dans le texte
    numbers_in_text = re.findall(r'(\d+(?:[\s.,]\d+)*(?:\s*[kMB€%])?)', md_content)
    
    # Vérifier la présence de sources
    sources_section = "## Sources citées" in md_content
    hypotheses_section = "## C. Hypothèses structurantes" in md_content
    
    # Vérifier que les tableaux d'hypothèses existent
    hypothesis_tables = len(re.findall(r'\|\s*H-[A-Z]+-\d+\s*\|', md_content))
    
    results.append(ValidationResult(
        rule_id="R1",
        rule_name="Sourcing des chiffres",
        passed=sources_section and hypothesis_tables >= 5,
        details=f"Sources citées: {'✓' if sources_section else '✗'} | "
                f"Hypothèses documentées: {hypothesis_tables}",
        severity="ERROR" if not sources_section else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 2: Aucune recommandation n'est faite sans conditions
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Vérifier la présence des conditions de succès/échec
    has_success_conditions = "Conditions de succès" in md_content
    has_failure_conditions = "Conditions d'échec" in md_content
    has_go_nogo = "Go/No-Go" in md_content or "Go / No-Go" in md_content
    
    results.append(ValidationResult(
        rule_id="R2",
        rule_name="Recommandations conditionnelles",
        passed=has_success_conditions and has_failure_conditions,
        details=f"Conditions succès: {'✓' if has_success_conditions else '✗'} | "
                f"Conditions échec: {'✓' if has_failure_conditions else '✗'} | "
                f"Jalons Go/No-Go: {'✓' if has_go_nogo else '✗'}",
        severity="ERROR" if not (has_success_conditions and has_failure_conditions) else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 3: Au moins 3 scénarios distincts
    # ═══════════════════════════════════════════════════════════════════════════
    
    scenarios = ["Conservateur", "Central", "Ambitieux"]
    scenarios_found = [s for s in scenarios if s in md_content]
    
    results.append(ValidationResult(
        rule_id="R3",
        rule_name="Présence des 3 scénarios",
        passed=len(scenarios_found) >= 3,
        details=f"Scénarios trouvés: {', '.join(scenarios_found)} ({len(scenarios_found)}/3)",
        severity="ERROR" if len(scenarios_found) < 3 else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 4: Section FAIL_CLOSED présente
    # ═══════════════════════════════════════════════════════════════════════════
    
    has_fail_closed_section = "FAIL_CLOSED" in md_content
    fail_closed_count = md_content.count("FAIL_CLOSED")
    has_limits_section = "Limites, incertitudes" in md_content or "Ce que KOREV Evidence ne peut pas" in md_content
    
    results.append(ValidationResult(
        rule_id="R4",
        rule_name="Section FAIL_CLOSED",
        passed=has_fail_closed_section and has_limits_section,
        details=f"FAIL_CLOSED mentionné: {fail_closed_count}x | "
                f"Section limites: {'✓' if has_limits_section else '✗'}",
        severity="ERROR" if not has_fail_closed_section else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 5: Lisibilité board non technique
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Vérifier l'absence de frameworks visibles
    frameworks_visible = []
    forbidden_frameworks = ["PESTEL", "SWOT", "7S McKinsey", "BCG Matrix", "Porter", "Gantt"]
    for fw in forbidden_frameworks:
        if fw in md_content:
            frameworks_visible.append(fw)
    
    # Vérifier la présence d'un Executive Summary
    has_exec_summary = "Executive Summary" in md_content
    
    # Vérifier le format "conclusion first"
    sections_with_conclusion = len(re.findall(r'###\s+Conclusion\s*:', md_content))
    
    results.append(ValidationResult(
        rule_id="R5",
        rule_name="Lisibilité board",
        passed=len(frameworks_visible) == 0 and has_exec_summary,
        details=f"Exec Summary: {'✓' if has_exec_summary else '✗'} | "
                f"Frameworks visibles: {frameworks_visible if frameworks_visible else 'Aucun'} | "
                f"Sections 'Conclusion first': {sections_with_conclusion}",
        severity="WARNING" if frameworks_visible else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 6: Sections obligatoires présentes
    # ═══════════════════════════════════════════════════════════════════════════
    
    required_sections = [
        ("A. Executive Summary", "## A."),
        ("B. Reformulation du problème", "## B."),
        ("C. Hypothèses structurantes", "## C."),
        ("D. Analyse marché", "## D."),
        ("E. Positionnement", "## E."),
        ("F. Modèle économique", "## F."),
        ("G. Prévisionnel financier", "## G."),
        ("H. Trajectoire de déploiement", "## H."),
        ("I. Risques majeurs", "## I."),
        ("J. Limites", "## J."),
    ]
    
    sections_present = []
    sections_missing = []
    for name, marker in required_sections:
        if marker in md_content:
            sections_present.append(name.split(".")[0])
        else:
            sections_missing.append(name)
    
    results.append(ValidationResult(
        rule_id="R6",
        rule_name="Sections obligatoires",
        passed=len(sections_missing) == 0,
        details=f"Présentes: {len(sections_present)}/10 | "
                f"Manquantes: {sections_missing if sections_missing else 'Aucune'}",
        severity="ERROR" if sections_missing else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 7: Sources européennes
    # ═══════════════════════════════════════════════════════════════════════════
    
    eu_sources = [
        "Eurostat", "INSEE", "Bpifrance", "Commission européenne",
        "EU AI Act", "RGPD", "Syntec", "IDC European"
    ]
    
    eu_sources_found = [s for s in eu_sources if s.lower() in md_content.lower()]
    
    results.append(ValidationResult(
        rule_id="R7",
        rule_name="Sources européennes",
        passed=len(eu_sources_found) >= 3,
        details=f"Sources EU trouvées: {', '.join(eu_sources_found)} ({len(eu_sources_found)})",
        severity="WARNING" if len(eu_sources_found) < 3 else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 8: Tableaux de risques et décisions non vides
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Compter les lignes de tableau avec données
    table_rows = re.findall(r'\|\s*[^|]+\s*\|', md_content)
    hypothesis_rows = re.findall(r'\|\s*H-[A-Z]+-\d+\s*\|', md_content)
    risk_indicators = ["Risque", "Impact", "Mitigation", "Probabilité"]
    risk_tables = any(r in md_content for r in risk_indicators)
    
    results.append(ValidationResult(
        rule_id="R8",
        rule_name="Tableaux structurés",
        passed=len(hypothesis_rows) >= 5 and risk_tables,
        details=f"Hypothèses structurées: {len(hypothesis_rows)} | "
                f"Tableaux de risques: {'✓' if risk_tables else '✗'}",
        severity="ERROR" if len(hypothesis_rows) < 5 else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 9: Graphiques présents
    # ═══════════════════════════════════════════════════════════════════════════
    
    charts = re.findall(r'!\[.*?\]\(.*?\.png\)', md_content)
    
    results.append(ValidationResult(
        rule_id="R9",
        rule_name="Visualisations",
        passed=len(charts) >= 3,
        details=f"Graphiques intégrés: {len(charts)}",
        severity="WARNING" if len(charts) < 3 else "INFO"
    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLE 10: Pas de chiffres "magiques" (sans contexte)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Vérifier que les chiffres clés sont dans des tableaux ou avec des sources
    arpa_mentioned = "ARPA" in md_content
    arr_mentioned = "ARR" in md_content
    breakeven_mentioned = "Break-even" in md_content or "break-even" in md_content
    
    results.append(ValidationResult(
        rule_id="R10",
        rule_name="Métriques documentées",
        passed=arpa_mentioned and arr_mentioned and breakeven_mentioned,
        details=f"ARPA défini: {'✓' if arpa_mentioned else '✗'} | "
                f"ARR documenté: {'✓' if arr_mentioned else '✗'} | "
                f"Break-even: {'✓' if breakeven_mentioned else '✗'}",
        severity="WARNING" if not (arpa_mentioned and arr_mentioned) else "INFO"
    ))
    
    return results


def print_results(results: List[ValidationResult]) -> bool:
    """Affiche les résultats de validation"""
    print("\n" + "=" * 70)
    print("LOOP DE CONTRÔLE — VALIDATION EVIDENCE-GRADE")
    print("=" * 70 + "\n")
    
    all_passed = True
    errors = []
    warnings = []
    
    for r in results:
        if r.passed:
            status = "✅ PASS"
        elif r.severity == "WARNING":
            status = "⚠️  WARN"
            warnings.append(r)
        else:
            status = "❌ FAIL"
            errors.append(r)
            all_passed = False
        
        print(f"[{r.rule_id}] {r.rule_name}")
        print(f"    Status: {status}")
        print(f"    Détails: {r.details}")
        print()
    
    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    
    print(f"\n  Règles validées: {passed_count}/{total}")
    print(f"  Erreurs: {len(errors)}")
    print(f"  Avertissements: {len(warnings)}")
    
    if errors:
        print("\n  ❌ ERREURS À CORRIGER:")
        for e in errors:
            print(f"    - [{e.rule_id}] {e.rule_name}: {e.details}")
    
    if warnings:
        print("\n  ⚠️  AVERTISSEMENTS:")
        for w in warnings:
            print(f"    - [{w.rule_id}] {w.rule_name}: {w.details}")
    
    print()
    
    if all_passed:
        print("  ✅ DOCUMENT VALIDÉ — Prêt pour livraison")
    else:
        print("  ❌ DOCUMENT NON CONFORME — Corrections requises")
    
    print("\n" + "=" * 70)
    
    return all_passed


def main():
    """Point d'entrée"""
    # Trouver le fichier MD le plus récent
    md_files = list(OUTPUT_DIR.glob("KOREV_Evidence_Dossier_Strategique_*.md"))
    if not md_files:
        print("Erreur: Aucun fichier Markdown trouvé")
        sys.exit(1)
    
    md_file = max(md_files, key=lambda f: f.stat().st_mtime)
    print(f"Validation du fichier: {md_file.name}")
    
    # Lire le contenu
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Valider
    results = validate_document(content)
    
    # Afficher
    all_passed = print_results(results)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
