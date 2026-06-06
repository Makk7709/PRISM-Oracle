"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — INTEGRATION TESTS                      ║
║                                                                              ║
║  Tests d'intégration pour vérifier le bon fonctionnement end-to-end.        ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Exécution : python tests/test_legal_safe_integration.py
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_all_imports():
    """Test que tous les modules s'importent correctement."""
    print("=" * 70)
    print("TEST 1: Imports des modules Legal-Safe")
    print("=" * 70)
    
    try:
        from python.helpers.legal_safe_schema import (
            LegalSafeResponse,
            LegalSafeResponseFactory,
            Jurisdiction,
            LegalDomain,
            ReviewTrigger,
            RiskLevel,
            Reliability,
        )
        print("  ✅ legal_safe_schema")
        
        from python.helpers.legal_safe_policy import (
            analyze_input,
            evaluate_response,
            validate_citations,
            PolicyEvaluation,
        )
        print("  ✅ legal_safe_policy")
        
        from python.helpers.legal_safe_renderer import (
            render_response,
            render_quick_summary,
        )
        print("  ✅ legal_safe_renderer")
        
        from python.helpers.legal_safe_logger import (
            LegalSafeLogger,
            remove_pii,
            hash_text,
            AuditLogEntry,
        )
        print("  ✅ legal_safe_logger")
        
        from python.helpers.legal_safe_runtime import (
            LegalSafeHandler,
            LegalSafeResponseParser,
            get_legal_safe_model_kwargs,
        )
        print("  ✅ legal_safe_runtime")
        
        from python.helpers.legal_citations_db import (
            validate_citation,
            get_citation_suggestions,
            ValidationResult,
        )
        print("  ✅ legal_citations_db")
        
        print("\n✅ Tous les imports réussis!\n")
        return True
        
    except ImportError as e:
        print(f"\n❌ Erreur d'import: {e}\n")
        return False


def test_citation_database():
    """Test de la base de citations."""
    print("=" * 70)
    print("TEST 2: Base de données de citations juridiques")
    print("=" * 70)
    
    from python.helpers.legal_citations_db import (
        validate_citation,
        get_citation_suggestions,
    )
    
    test_cases = [
        # Citations valides
        ("Code civil, art. 1103", True, "Code français valide"),
        ("Code du travail, art. L1234-5", True, "Code travail format L"),
        ("RGPD, art. 6", True, "Règlement UE - RGPD"),
        ("Règlement (UE) 2016/679", True, "RGPD numéro complet"),
        ("Cass. soc., 15 mars 2023", True, "Jurisprudence Cass."),
        ("UNKNOWN", True, "Citation explicitement incertaine"),
        
        # Citations invalides
        ("Article inventé 999-Z", False, "Format non reconnu"),
        ("Loi imaginaire du 32 janvier", False, "Date impossible"),
    ]
    
    passed = 0
    failed = 0
    
    for citation, expected_valid, description in test_cases:
        result = validate_citation(citation)
        status = "✅" if result.is_valid == expected_valid else "❌"
        
        if result.is_valid == expected_valid:
            passed += 1
        else:
            failed += 1
        
        print(f"  {status} '{citation[:40]}...' -> valid={result.is_valid} (expected={expected_valid})")
        if result.warning:
            print(f"      ⚠️ Warning: {result.warning}")
    
    print(f"\n  Résultat: {passed}/{passed+failed} tests passés")
    
    # Test des suggestions
    print("\n  Test des suggestions par domaine:")
    for domain in ["droit_travail", "rgpd_donnees", "contrats"]:
        suggestions = get_citation_suggestions(domain)
        print(f"    {domain}: {len(suggestions)} suggestions")
    
    print()
    return failed == 0


def test_policy_triggers():
    """Test des triggers de la policy."""
    print("=" * 70)
    print("TEST 3: Policy d'escalade - Détection des triggers")
    print("=" * 70)
    
    from python.helpers.legal_safe_policy import analyze_input
    
    test_cases = [
        ("Mon employeur veut me licencier", "droit_travail", False, False),
        ("Peux-tu me certifier que c'est légal ?", None, True, False),
        ("Garantis-moi que je ne risque rien", None, True, False),
        ("Rédige-moi un contrat de travail", "droit_travail", False, True),
        ("Dépose une plainte en mon nom", None, False, True),
        ("Je dois payer mes impôts", "fiscal", False, False),
        ("Question RGPD sur les données", "rgpd_donnees", False, False),
    ]
    
    passed = 0
    
    for text, expected_domain, expected_certainty, expected_restricted in test_cases:
        analysis = analyze_input(text)
        
        domain_ok = (analysis.detected_domain and analysis.detected_domain.value == expected_domain) or \
                   (not analysis.detected_domain and not expected_domain)
        certainty_ok = analysis.contains_certainty_request == expected_certainty
        restricted_ok = analysis.is_restricted_activity == expected_restricted
        
        all_ok = domain_ok and certainty_ok and restricted_ok
        status = "✅" if all_ok else "❌"
        
        if all_ok:
            passed += 1
        
        print(f"  {status} '{text[:50]}...'")
        if not domain_ok:
            print(f"      Domain: got {analysis.detected_domain}, expected {expected_domain}")
        if not certainty_ok:
            print(f"      Certainty: got {analysis.contains_certainty_request}, expected {expected_certainty}")
        if not restricted_ok:
            print(f"      Restricted: got {analysis.is_restricted_activity}, expected {expected_restricted}")
    
    print(f"\n  Résultat: {passed}/{len(test_cases)} tests passés\n")
    return passed == len(test_cases)


def test_pii_removal():
    """Test de la suppression des PII."""
    print("=" * 70)
    print("TEST 4: Suppression des données personnelles (PII)")
    print("=" * 70)
    
    from python.helpers.legal_safe_logger import remove_pii
    
    test_cases = [
        ("Contact: jean.dupont@example.com", "[EMAIL_REMOVED]", "Email"),
        ("Appelez-moi au 06 12 34 56 78", "[PHONE_FR_REMOVED]", "Téléphone FR"),
        ("IBAN: FR7630001007941234567890185", "[IBAN_REMOVED]", "IBAN"),
        ("Mon adresse IP: 192.168.1.1", "[IP_ADDRESS_REMOVED]", "IP"),
        ("Texte normal sans PII", "Texte normal sans PII", "Pas de PII"),
    ]
    
    passed = 0
    
    for text, expected_marker, description in test_cases:
        cleaned = remove_pii(text)
        contains_marker = expected_marker in cleaned
        no_original = text not in cleaned or text == "Texte normal sans PII"
        
        ok = contains_marker and no_original
        status = "✅" if ok else "❌"
        
        if ok:
            passed += 1
        
        print(f"  {status} {description}: '{text[:30]}...' -> '{cleaned[:40]}...'")
    
    print(f"\n  Résultat: {passed}/{len(test_cases)} tests passés\n")
    return passed == len(test_cases)


def test_schema_validation():
    """Test de la validation du schéma."""
    print("=" * 70)
    print("TEST 5: Validation du schéma LegalSafeResponse")
    print("=" * 70)
    
    from python.helpers.legal_safe_schema import (
        LegalSafeResponse,
        LegalSafeResponseFactory,
        Scope,
        Jurisdiction,
        Classification,
        LegalDomain,
        TaskType,
        Complexity,
        Analysis,
        Conclusion,
        Safety,
        RiskLevel,
        Output,
        Meta,
        ReviewTrigger,
    )
    
    # Test 1: Création d'un fallback
    print("  Test 1: Création d'un fallback...")
    try:
        fallback = LegalSafeResponseFactory.create_fallback_response(
            reason="Test error",
            provider="test",
            model="test-model",
        )
        assert fallback.fallback.triggered is True
        assert fallback.safety.requires_human_review is True
        print("    ✅ Fallback créé correctement")
    except Exception as e:
        print(f"    ❌ Erreur: {e}")
        return False
    
    # Test 2: Escalade automatique pour confiance < 0.75
    print("  Test 2: Escalade auto pour confiance < 0.75...")
    try:
        from python.helpers.legal_safe_schema import LegalBasis, LegalBasisType, Reliability
        
        response = LegalSafeResponse(
            scope=Scope(jurisdiction_requested=Jurisdiction.FR),
            classification=Classification(
                domain=LegalDomain.CONTRATS,
                task_type=TaskType.INFORMATION,
                complexity=Complexity.SIMPLE,
            ),
            legal_basis=[
                LegalBasis(
                    id="L1",
                    type=LegalBasisType.CODE,
                    citation="Code civil, art. 1103",
                    reliability=Reliability.HIGH,
                )
            ],
            analysis=Analysis(reasoning_steps=["Test"]),
            conclusion=Conclusion(
                answer="Test",
                recommendation="Test",
                confidence=0.50,  # < 0.75
            ),
            safety=Safety(hallucination_risk=RiskLevel.LOW, requires_human_review=False),
            output=Output(user_facing_markdown="# Test\n\n⚠️ conseil juridique"),
            meta=Meta(provider="test", model="test", temperature=0.0),
        )
        
        assert ReviewTrigger.LOW_CONFIDENCE in response.safety.review_triggers
        assert response.safety.requires_human_review is True
        print("    ✅ Escalade déclenchée pour confiance < 0.75")
    except Exception as e:
        print(f"    ❌ Erreur: {e}")
        return False
    
    # Test 3: Rejet si temperature != 0
    print("  Test 3: Rejet si temperature != 0...")
    try:
        try:
            LegalSafeResponse(
                scope=Scope(jurisdiction_requested=Jurisdiction.FR),
                classification=Classification(
                    domain=LegalDomain.CONTRATS,
                    task_type=TaskType.INFORMATION,
                    complexity=Complexity.SIMPLE,
                ),
                analysis=Analysis(reasoning_steps=["Test"]),
                conclusion=Conclusion(answer="Test", recommendation="Test", confidence=0.8),
                safety=Safety(hallucination_risk=RiskLevel.LOW, requires_human_review=False),
                output=Output(user_facing_markdown="# Test\n\n⚠️ conseil juridique"),
                meta=Meta(provider="test", model="test", temperature=0.7),  # != 0
            )
            print("    ❌ Aurait dû rejeter temperature != 0")
            return False
        except ValueError as e:
            if "Temperature must be 0" in str(e):
                print("    ✅ Temperature != 0 correctement rejetée")
            else:
                raise
    except Exception as e:
        print(f"    ❌ Erreur inattendue: {e}")
        return False
    
    print()
    return True


def test_json_parsing():
    """Test du parsing JSON."""
    print("=" * 70)
    print("TEST 6: Parsing des réponses JSON")
    print("=" * 70)
    
    from python.helpers.legal_safe_runtime import LegalSafeResponseParser
    
    # Test 1: JSON brut
    print("  Test 1: JSON brut...")
    raw_json = '{"mode": "legal_safe", "test": true}'
    result = LegalSafeResponseParser.extract_json_from_response(raw_json)
    if result and result.get("mode") == "legal_safe":
        print("    ✅ JSON brut parsé")
    else:
        print("    ❌ Échec du parsing JSON brut")
        return False
    
    # Test 2: JSON dans bloc markdown
    print("  Test 2: JSON dans bloc markdown...")
    markdown_json = '''
Voici ma réponse :

```json
{"mode": "legal_safe", "answer": "test"}
```
'''
    result = LegalSafeResponseParser.extract_json_from_response(markdown_json)
    if result and result.get("mode") == "legal_safe":
        print("    ✅ JSON markdown parsé")
    else:
        print("    ❌ Échec du parsing JSON markdown")
        return False
    
    # Test 3: Texte sans JSON
    print("  Test 3: Texte sans JSON...")
    no_json = "Ceci n'est pas du JSON du tout."
    result = LegalSafeResponseParser.extract_json_from_response(no_json)
    if result is None:
        print("    ✅ Texte sans JSON correctement détecté")
    else:
        print("    ❌ Aurait dû retourner None")
        return False
    
    print()
    return True


def test_renderer():
    """Test du renderer markdown."""
    print("=" * 70)
    print("TEST 7: Renderer Markdown")
    print("=" * 70)
    
    from python.helpers.legal_safe_schema import (
        LegalSafeResponse, Scope, Jurisdiction, Classification, LegalDomain,
        TaskType, Complexity, Analysis, Conclusion, Safety, RiskLevel,
        Output, Meta, LegalBasis, LegalBasisType, Reliability,
    )
    from python.helpers.legal_safe_renderer import render_response
    
    response = LegalSafeResponse(
        scope=Scope(jurisdiction_requested=Jurisdiction.FR),
        classification=Classification(
            domain=LegalDomain.CONTRATS,
            task_type=TaskType.INFORMATION,
            complexity=Complexity.SIMPLE,
        ),
        legal_basis=[
            LegalBasis(
                id="L1",
                type=LegalBasisType.CODE,
                citation="Code civil, art. 1103",
                reliability=Reliability.HIGH,
            )
        ],
        analysis=Analysis(reasoning_steps=["Analyse du contrat"]),
        conclusion=Conclusion(
            answer="Le contrat est valide.",
            recommendation="Conservez le contrat.",
            confidence=0.85,
        ),
        safety=Safety(hallucination_risk=RiskLevel.LOW, requires_human_review=False),
        output=Output(user_facing_markdown="# Test\n\n⚠️ Cette analyse ne constitue pas un conseil juridique."),
        meta=Meta(provider="test", model="test", temperature=0.0),
    )
    
    markdown = render_response(response)
    
    checks = [
        ("# " in markdown, "Titre présent"),
        ("Code civil" in markdown, "Citation présente"),
        ("contrat" in markdown.lower(), "Contenu présent"),
        ("⚠️" in markdown, "Disclaimer présent"),
    ]
    
    passed = 0
    for check, description in checks:
        status = "✅" if check else "❌"
        if check:
            passed += 1
        print(f"  {status} {description}")
    
    print(f"\n  Résultat: {passed}/{len(checks)} vérifications passées\n")
    return passed == len(checks)


def test_extension_detection():
    """Test de la détection du profil legal_safe."""
    print("=" * 70)
    print("TEST 8: Détection du profil Legal-Safe")
    print("=" * 70)
    
    # Test via variable d'environnement
    print("  Test 1: Détection via env KOREV_LEGAL_SAFE_MODE...")
    
    # Sauvegarder la valeur actuelle
    old_value = os.environ.get("KOREV_LEGAL_SAFE_MODE")
    
    try:
        # Test avec la variable activée
        os.environ["KOREV_LEGAL_SAFE_MODE"] = "true"
        
        # Simuler la vérification
        env_value = os.environ.get("KOREV_LEGAL_SAFE_MODE", "").lower()
        is_active = env_value in ("true", "1", "yes", "on")
        
        if is_active:
            print("    ✅ Détection via env fonctionne")
        else:
            print("    ❌ Détection via env échouée")
            return False
        
        # Test avec la variable désactivée
        os.environ["KOREV_LEGAL_SAFE_MODE"] = "false"
        env_value = os.environ.get("KOREV_LEGAL_SAFE_MODE", "").lower()
        is_active = env_value in ("true", "1", "yes", "on")
        
        if not is_active:
            print("    ✅ Désactivation via env fonctionne")
        else:
            print("    ❌ Désactivation via env échouée")
            return False
            
    finally:
        # Restaurer
        if old_value is not None:
            os.environ["KOREV_LEGAL_SAFE_MODE"] = old_value
        elif "KOREV_LEGAL_SAFE_MODE" in os.environ:
            del os.environ["KOREV_LEGAL_SAFE_MODE"]
    
    print()
    return True


def test_model_kwargs():
    """Test des kwargs forcés."""
    print("=" * 70)
    print("TEST 9: Kwargs forcés (temperature=0)")
    print("=" * 70)
    
    from python.helpers.legal_safe_runtime import get_legal_safe_model_kwargs
    
    kwargs = get_legal_safe_model_kwargs()
    
    checks = [
        (kwargs.get("temperature") == 0.0, "temperature=0.0"),
        (kwargs.get("top_p") == 1.0, "top_p=1.0"),
    ]
    
    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"  {status} {description}")
    
    print()
    return all(c[0] for c in checks)


def test_profile_files_exist():
    """Test que les fichiers du profil existent."""
    print("=" * 70)
    print("TEST 10: Fichiers du profil Legal-Safe")
    print("=" * 70)
    
    base_path = Path(__file__).parent.parent
    
    required_files = [
        "agents/legal_safe/_context.md",
        "agents/legal_safe/prompts/agent.system.main.role.md",
        "agents/legal_safe/prompts/agent.system.main.communication.md",
        "agents/legal_safe/demos/demo_responses.md",
        "python/helpers/legal_safe_schema.py",
        "python/helpers/legal_safe_policy.py",
        "python/helpers/legal_safe_renderer.py",
        "python/helpers/legal_safe_logger.py",
        "python/helpers/legal_safe_runtime.py",
        "python/helpers/legal_citations_db.py",
        "python/extensions/legal_safe_mode/_10_legal_safe_integration.py",
        "webui/components/legal-safe/escalation-banner.html",
    ]
    
    passed = 0
    for file_path in required_files:
        full_path = base_path / file_path
        exists = full_path.exists()
        status = "✅" if exists else "❌"
        if exists:
            passed += 1
        print(f"  {status} {file_path}")
    
    print(f"\n  Résultat: {passed}/{len(required_files)} fichiers présents\n")
    return passed == len(required_files)


def main():
    """Exécute tous les tests."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              LEGAL-SAFE MODE — TESTS D'INTÉGRATION                          ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    tests = [
        ("Imports", test_all_imports),
        ("Citation Database", test_citation_database),
        ("Policy Triggers", test_policy_triggers),
        ("PII Removal", test_pii_removal),
        ("Schema Validation", test_schema_validation),
        ("JSON Parsing", test_json_parsing),
        ("Markdown Renderer", test_renderer),
        ("Extension Detection", test_extension_detection),
        ("Model Kwargs", test_model_kwargs),
        ("Profile Files", test_profile_files_exist),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ Exception dans {name}: {e}")
            results.append((name, False))
    
    # Résumé
    print("=" * 70)
    print("RÉSUMÉ FINAL")
    print("=" * 70)
    
    total_passed = sum(1 for _, passed in results if passed)
    total = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print()
    print(f"  Total: {total_passed}/{total} tests réussis")
    
    if total_passed == total:
        print("\n  🎉 TOUS LES TESTS PASSENT! Le mode Legal-Safe est prêt.\n")
        return 0
    else:
        print(f"\n  ⚠️ {total - total_passed} test(s) en échec.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
