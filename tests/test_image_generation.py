"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    IMAGE GENERATION — TESTS                                  ║
║                                                                              ║
║  Tests de validation pour le système de génération d'images.                ║
║  Vérifie : policies, providers, fallback, settings.                         ║
║                                                                              ║
║  Exécution : python tests/test_image_generation.py                          ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test que tous les modules s'importent correctement."""
    print("=" * 70)
    print("TEST 1: Imports des modules Image Generation")
    print("=" * 70)
    
    try:
        from python.helpers.tool_policy import (
            PolicyDecision,
            PolicyResult,
            check_tool_policy,
            get_policy_for_profile,
            get_allowed_tools_for_profile,
            is_tool_forbidden,
            format_forbidden_response,
        )
        print("  ✅ tool_policy")
        
        from python.tools.generate_image import GenerateImage
        print("  ✅ generate_image tool")
        
        from python.helpers import settings
        print("  ✅ settings")
        
        print("\n✅ Tous les imports réussis!\n")
        return True
        
    except ImportError as e:
        print(f"\n❌ Erreur d'import: {e}\n")
        return False


def test_policy_decisions():
    """Test des décisions de policy par profil."""
    print("=" * 70)
    print("TEST 2: Policy Decisions par Profil")
    print("=" * 70)
    
    from python.helpers.tool_policy import (
        check_tool_policy,
        PolicyDecision,
    )
    
    test_cases = [
        # (tool_name, profile, expected_decision, description)
        ("generate_image", "marketing", PolicyDecision.ALLOWED, "Marketing peut générer des images"),
        ("generate_image", "finance", PolicyDecision.ALLOWED, "Finance peut générer des images"),
        ("generate_image", "legal_safe", PolicyDecision.ALLOWED, "Legal peut générer des images"),
        ("generate_image", "multitask", PolicyDecision.ALLOWED, "Multitask peut générer des images"),
        ("generate_image", "developer", PolicyDecision.ALLOWED, "Developer peut générer des images"),
        
        # Forbidden tools for marketing
        ("huggingface_image", "marketing", PolicyDecision.FORBIDDEN, "HuggingFace interdit pour marketing"),
        ("stable_diffusion", "marketing", PolicyDecision.FORBIDDEN, "Stable Diffusion interdit pour marketing"),
        ("sd_generate", "marketing", PolicyDecision.FORBIDDEN, "SD interdit pour marketing"),
        ("midjourney_create", "marketing", PolicyDecision.FORBIDDEN, "Midjourney interdit pour marketing"),
        ("replicate_image", "marketing", PolicyDecision.FORBIDDEN, "Replicate interdit pour marketing"),
        
        # Other profiles don't have forbidden patterns
        ("huggingface_image", "developer", PolicyDecision.ALLOWED, "HuggingFace OK pour developer"),
        ("stable_diffusion", "multitask", PolicyDecision.ALLOWED, "SD OK pour multitask"),
    ]
    
    passed = 0
    failed = 0
    
    for tool_name, profile, expected, description in test_cases:
        result = check_tool_policy(tool_name, profile)
        is_pass = result.decision == expected
        status = "✅" if is_pass else "❌"
        
        if is_pass:
            passed += 1
        else:
            failed += 1
        
        print(f"  {status} {description}")
        if not is_pass:
            print(f"      Tool: {tool_name}, Profile: {profile}")
            print(f"      Expected: {expected}, Got: {result.decision}")
            print(f"      Reason: {result.reason}")
    
    print(f"\n  Résultat: {passed}/{passed+failed} tests passés\n")
    return failed == 0


def test_settings_structure():
    """Test que les settings image generation sont présents."""
    print("=" * 70)
    print("TEST 3: Structure des Settings Image Generation")
    print("=" * 70)
    
    from python.helpers.settings import get_default_settings
    
    defaults = get_default_settings()
    
    required_keys = [
        "image_gen_enabled",
        "image_gen_primary_provider",
        "image_gen_fallback_provider",
        "image_gen_openai_model",
        "image_gen_openai_api_key",
        "image_gen_google_model",
        "image_gen_google_api_key",
        "image_gen_default_size",
        "image_gen_default_quality",
    ]
    
    passed = 0
    for key in required_keys:
        if key in defaults:
            print(f"  ✅ {key}: {defaults[key]}")
            passed += 1
        else:
            print(f"  ❌ {key}: MISSING")
    
    print(f"\n  Résultat: {passed}/{len(required_keys)} clés présentes\n")
    return passed == len(required_keys)


def test_default_values():
    """Test des valeurs par défaut."""
    print("=" * 70)
    print("TEST 4: Valeurs par Défaut")
    print("=" * 70)
    
    from python.helpers.settings import get_default_settings
    
    defaults = get_default_settings()
    
    expected_defaults = {
        "image_gen_enabled": True,
        "image_gen_primary_provider": "openai",
        "image_gen_fallback_provider": "google",
        "image_gen_openai_model": "dall-e-3",
        "image_gen_default_size": "1024x1024",
        "image_gen_default_quality": "standard",
    }
    
    passed = 0
    for key, expected in expected_defaults.items():
        actual = defaults.get(key)
        is_pass = actual == expected
        status = "✅" if is_pass else "❌"
        if is_pass:
            passed += 1
        print(f"  {status} {key}: {actual} (expected: {expected})")
    
    print(f"\n  Résultat: {passed}/{len(expected_defaults)} valeurs correctes\n")
    return passed == len(expected_defaults)


def test_allowed_tools_by_profile():
    """Test de la liste des tools autorisés par profil."""
    print("=" * 70)
    print("TEST 5: Tools Autorisés par Profil")
    print("=" * 70)
    
    from python.helpers.tool_policy import get_allowed_tools_for_profile
    
    profiles = ["marketing", "finance", "legal_safe", "developer", "multitask"]
    
    all_pass = True
    for profile in profiles:
        allowed = get_allowed_tools_for_profile(profile, "image_tools")
        has_generate_image = "generate_image" in allowed
        status = "✅" if has_generate_image else "❌"
        if not has_generate_image:
            all_pass = False
        print(f"  {status} {profile}: {allowed}")
    
    print()
    return all_pass


def test_forbidden_response_format():
    """Test du format de réponse pour outil interdit."""
    print("=" * 70)
    print("TEST 6: Format Réponse Outil Interdit")
    print("=" * 70)
    
    from python.helpers.tool_policy import (
        check_tool_policy,
        format_forbidden_response,
        PolicyDecision,
    )
    
    # Simulate a forbidden tool call
    result = check_tool_policy("huggingface_image", "marketing")
    
    if result.decision == PolicyDecision.FORBIDDEN:
        response = format_forbidden_response(result)
        
        checks = [
            ("⚠️" in response, "Warning emoji present"),
            ("Tool Not Authorized" in response, "Title present"),
            ("huggingface_image" in response, "Tool name present"),
            ("generate_image" in response, "Alternative suggested"),
        ]
        
        passed = 0
        for check, description in checks:
            status = "✅" if check else "❌"
            if check:
                passed += 1
            print(f"  {status} {description}")
        
        print(f"\n  Résultat: {passed}/{len(checks)} checks passés\n")
        return passed == len(checks)
    else:
        print("  ❌ Test setup failed: tool should be forbidden")
        return False


def test_tool_file_exists():
    """Test que les fichiers du tool existent."""
    print("=" * 70)
    print("TEST 7: Fichiers du Tool Image Generation")
    print("=" * 70)
    
    base_path = Path(__file__).parent.parent
    
    required_files = [
        "prompts/agent.system.tool.generate_image.md",
        "python/tools/generate_image.py",
        "python/helpers/tool_policy.py",
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


def test_prompt_content():
    """Test que le prompt contient les éléments requis."""
    print("=" * 70)
    print("TEST 8: Contenu du Prompt Tool")
    print("=" * 70)
    
    base_path = Path(__file__).parent.parent
    prompt_path = base_path / "prompts/agent.system.tool.generate_image.md"
    
    if not prompt_path.exists():
        print("  ❌ Prompt file not found")
        return False
    
    content = prompt_path.read_text()
    
    required_elements = [
        ("generate_image", "Tool name"),
        ("prompt", "Prompt argument"),
        ("size", "Size argument"),
        ("quality", "Quality argument"),
        ("purpose", "Purpose argument"),
        ("tool_name", "Usage example with tool_name"),
        ("tool_args", "Usage example with tool_args"),
        ("marketing", "Marketing context"),
        ("MUST use this tool", "Requirement to use tool"),
    ]
    
    passed = 0
    for element, description in required_elements:
        found = element.lower() in content.lower()
        status = "✅" if found else "❌"
        if found:
            passed += 1
        print(f"  {status} {description}")
    
    print(f"\n  Résultat: {passed}/{len(required_elements)} éléments présents\n")
    return passed == len(required_elements)


def main():
    """Exécute tous les tests."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              IMAGE GENERATION — TESTS DE VALIDATION                         ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Policy Decisions", test_policy_decisions),
        ("Settings Structure", test_settings_structure),
        ("Default Values", test_default_values),
        ("Allowed Tools", test_allowed_tools_by_profile),
        ("Forbidden Response", test_forbidden_response_format),
        ("Tool Files", test_tool_file_exists),
        ("Prompt Content", test_prompt_content),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ Exception dans {name}: {e}")
            import traceback
            traceback.print_exc()
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
        print("\n  🎉 TOUS LES TESTS PASSENT! Image Generation est prêt.\n")
        return 0
    else:
        print(f"\n  ⚠️ {total - total_passed} test(s) en échec.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
