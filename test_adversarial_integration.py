#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         TEST INTÉGRATION ADVERSARIAL + PRISM CONSENSUS                       ║
║                                                                              ║
║  Test du pipeline intégré avec les vraies briques KOREV.                     ║
║                                                                              ║
║  Usage: python test_adversarial_integration.py                               ║
║                                                                              ║
║  Pour utiliser les vrais LLMs, configurez:                                   ║
║  - Les arbiters PRISM dans les Settings UI                                   ║
║  - Ou les variables CONSENSUS_ARBITER_* dans .env                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment for test
os.environ.setdefault("EVIDENCE_ENV", "development")
os.environ.setdefault("CONSENSUS_SIMULATION", "true")  # Pour test sans vrais LLMs


def print_header(title: str):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def print_result(test: str, passed: bool, details: str = ""):
    emoji = "✅" if passed else "❌"
    print(f"  {emoji} {test}")
    if details:
        print(f"      └─ {details}")


async def test_integration_imports():
    """Test que tous les imports fonctionnent."""
    print_header("Test 1: Imports d'intégration")
    
    try:
        from python.helpers.adversarial_consensus_integration import (
            IntegratedAdversarialPipeline,
            AdversarialLLMCaller,
            get_adversarial_pipeline,
            analyze_with_adversarial,
            DOMAIN_MAPPING,
        )
        print_result("Import adversarial_consensus_integration", True)
        
        from python.helpers.consensus_arbiter import (
            ConsensusOrchestrator,
            get_consensus_orchestrator,
            load_consensus_config,
        )
        print_result("Import consensus_arbiter", True)
        
        from python.helpers.criticality_router import (
            CriticalityRouter,
            get_criticality_router,
            assess_criticality,
        )
        print_result("Import criticality_router", True)
        
        from python.helpers.consensus_manager import (
            ConsensusManager,
            ConsensusStatus,
            VoteType,
        )
        print_result("Import consensus_manager", True)
        
        return True
    except ImportError as e:
        print_result(f"Import failed: {e}", False)
        return False


async def test_config_loading():
    """Test le chargement de la configuration PRISM."""
    print_header("Test 2: Configuration PRISM")
    
    from python.helpers.consensus_arbiter import load_consensus_config
    
    try:
        config = load_consensus_config()
        
        print_result(
            f"Arbiters configurés: {len(config.arbiters)}", 
            len(config.arbiters) > 0,
            f"Models: {[f'{a.provider}/{a.model}' for a in config.arbiters[:3]]}"
        )
        
        print_result(
            f"Timeout: {config.global_timeout_ms}ms",
            config.global_timeout_ms > 0
        )
        
        print_result(
            f"Simulation: {config.simulation_enabled}",
            True,  # Juste info
            "Mode simulation activé pour test" if config.simulation_enabled else "Mode réel"
        )
        
        return True
    except Exception as e:
        print_result(f"Config loading failed: {e}", False)
        return False


async def test_criticality_router():
    """Test le CriticalityRouter."""
    print_header("Test 3: Criticality Router")
    
    from python.helpers.criticality_router import get_criticality_router, assess_criticality
    
    router = get_criticality_router()
    
    test_cases = [
        ("Mon client risque la prison pour fraude fiscale", "legal_safe", True),
        ("Quels sont les effets secondaires de ce médicament?", "medical", True),
        ("Comment configurer mon serveur?", "developer", False),
        ("Recherche sur les biomarqueurs du cancer", "researcher", True),
    ]
    
    all_passed = True
    for query, profile, expected_consensus in test_cases:
        assessment = assess_criticality(query, profile)
        result = assessment.requires_consensus
        passed = result == expected_consensus
        all_passed = all_passed and passed
        
        print_result(
            f"'{query[:40]}...' (profile={profile})",
            passed,
            f"Consensus requis: {result} (attendu: {expected_consensus})"
        )
    
    return all_passed


async def test_adversarial_pipeline_creation():
    """Test la création du pipeline intégré."""
    print_header("Test 4: Création Pipeline Intégré")
    
    from python.helpers.adversarial_consensus_integration import (
        get_adversarial_pipeline,
        IntegratedAdversarialPipeline,
    )
    
    try:
        pipeline = get_adversarial_pipeline()
        
        print_result(
            "Pipeline créé",
            isinstance(pipeline, IntegratedAdversarialPipeline)
        )
        
        print_result(
            "Entry Gate initialisé",
            pipeline._entry_gate is not None
        )
        
        print_result(
            "LLM Caller initialisé",
            pipeline._llm_caller is not None
        )
        
        print_result(
            "Consensus Orchestrator lié",
            pipeline._consensus is not None
        )
        
        return True
    except Exception as e:
        print_result(f"Pipeline creation failed: {e}", False)
        return False


async def test_llm_caller_models():
    """Test que le LLM Caller voit les modèles PRISM."""
    print_header("Test 5: LLM Caller - Modèles PRISM")
    
    from python.helpers.adversarial_consensus_integration import AdversarialLLMCaller
    
    caller = AdversarialLLMCaller()
    models = caller.get_available_models()
    
    print_result(
        f"Modèles disponibles: {len(models)}",
        len(models) > 0,
        f"Premiers: {models[:3]}" if models else "Aucun modèle"
    )
    
    return len(models) > 0


async def test_full_analysis_simulation():
    """Test une analyse complète en mode simulation."""
    print_header("Test 6: Analyse Complète (Simulation)")
    
    from python.helpers.adversarial_consensus_integration import analyze_with_adversarial
    
    query = """
    Notre client, startup biotech en phase préclinique, doit choisir entre 
    trois term sheets pour sa série A. Le CSO menace de partir.
    Quelle stratégie financière et juridique recommandez-vous?
    """
    
    try:
        start_time = time.time()
        
        dossier = await analyze_with_adversarial(
            query=query,
            context={"urgency": "high", "domain": "finance"},
            agent_profile="legal_safe",
        )
        
        elapsed = time.time() - start_time
        
        print_result(
            f"Dossier créé en {elapsed:.2f}s",
            dossier is not None,
            f"ID: {dossier.id[:16]}..."
        )
        
        print_result(
            f"Domaine détecté: {dossier.domain.value}",
            dossier.domain is not None
        )
        
        print_result(
            f"Criticité: {dossier.criticality.value}",
            dossier.criticality is not None
        )
        
        print_result(
            f"Protocole: {dossier.protocol.value}",
            dossier.protocol is not None
        )
        
        print_result(
            f"Analyses: {len(dossier.agent_analyses)}",
            len(dossier.agent_analyses) > 0
        )
        
        print_result(
            f"Revues: {len(dossier.peer_reviews)}",
            True  # Peut être 0 pour LIGHT protocol
        )
        
        print_result(
            f"Audit score: {dossier.audit_report.overall_reliability_score:.2f}",
            dossier.audit_report is not None
        )
        
        print_result(
            f"Status: {dossier.status}",
            dossier.status == "awaiting_human_decision"
        )
        
        return True
        
    except Exception as e:
        import traceback
        print_result(f"Analysis failed: {e}", False)
        print(f"      Traceback: {traceback.format_exc()[:500]}")
        return False


async def test_trace_generation():
    """Test la génération de trace."""
    print_header("Test 7: Génération Trace")
    
    from python.helpers.adversarial_consensus_integration import get_adversarial_pipeline
    
    pipeline = get_adversarial_pipeline()
    
    # Utiliser un dossier existant s'il y en a
    if pipeline._dossiers:
        dossier_id = list(pipeline._dossiers.keys())[0]
        
        try:
            trace_md = pipeline.get_trace_markdown(dossier_id)
            
            print_result(
                f"Trace générée: {len(trace_md)} chars",
                len(trace_md) > 100
            )
            
            # Vérifier le contenu
            has_title = "# " in trace_md
            has_sections = "## " in trace_md
            
            print_result("Contient titre", has_title)
            print_result("Contient sections", has_sections)
            
            return True
        except Exception as e:
            print_result(f"Trace generation failed: {e}", False)
            return False
    else:
        print_result("Aucun dossier pour test", False, "Exécutez test 6 d'abord")
        return False


async def test_decision_interface():
    """Test l'interface de décision."""
    print_header("Test 8: Interface Décision Humaine")
    
    from python.helpers.adversarial_consensus_integration import get_adversarial_pipeline
    
    pipeline = get_adversarial_pipeline()
    
    if pipeline._dossiers:
        dossier_id = list(pipeline._dossiers.keys())[0]
        
        try:
            presentation = pipeline.get_decision_presentation(dossier_id)
            
            print_result(
                "Présentation générée",
                "decision_form" in presentation
            )
            
            print_result(
                "Options présentes",
                len(presentation.get("decision_form", {}).get("options", [])) > 0
            )
            
            print_result(
                "Acknowledgments présents",
                len(presentation.get("decision_form", {}).get("required_acknowledgments", [])) > 0
            )
            
            # Tester l'enregistrement de décision
            success = pipeline.record_decision(
                dossier_id,
                "accept_with_reserves",
                ["J'ai lu les incertitudes", "J'accepte les risques"],
                "Test de décision"
            )
            
            print_result("Décision enregistrée", success)
            
            return True
        except Exception as e:
            print_result(f"Decision interface failed: {e}", False)
            return False
    else:
        print_result("Aucun dossier pour test", False)
        return False


async def test_with_real_llms():
    """Test avec vrais LLMs si configurés."""
    print_header("Test 9: Vrais LLMs (optionnel)")
    
    # Vérifier si les vrais LLMs sont disponibles
    from python.helpers import llm_provider
    
    if not llm_provider.is_provider_available():
        print_result(
            "LLM Provider non disponible",
            True,  # Pas un échec
            "Configurez les API keys pour tester avec vrais LLMs"
        )
        return True
    
    # Désactiver simulation pour ce test
    old_sim = os.environ.get("CONSENSUS_SIMULATION")
    os.environ["CONSENSUS_SIMULATION"] = "false"
    
    try:
        from python.helpers.adversarial_consensus_integration import AdversarialLLMCaller
        
        caller = AdversarialLLMCaller()
        models = caller.get_available_models()
        
        if models:
            provider, model = models[0]
            
            print(f"  🔄 Appel réel à {provider}/{model}...")
            
            response = await caller.call_model(
                provider=provider,
                model=model,
                prompt="Réponds 'OK' en une seule ligne.",
                role="test",
                timeout_ms=30000,
            )
            
            print_result(
                f"Réponse reçue de {provider}/{model}",
                len(response) > 0,
                f"Response: {response[:50]}..."
            )
            
            return True
        else:
            print_result("Aucun modèle configuré", False)
            return False
            
    except Exception as e:
        print_result(f"Real LLM test failed: {e}", False)
        return False
    finally:
        # Restaurer
        if old_sim:
            os.environ["CONSENSUS_SIMULATION"] = old_sim


async def main():
    """Exécute tous les tests."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║      🧪 TEST INTÉGRATION ADVERSARIAL + PRISM CONSENSUS 🧪                   ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    results = []
    
    # Tests
    results.append(await test_integration_imports())
    results.append(await test_config_loading())
    results.append(await test_criticality_router())
    results.append(await test_adversarial_pipeline_creation())
    results.append(await test_llm_caller_models())
    results.append(await test_full_analysis_simulation())
    results.append(await test_trace_generation())
    results.append(await test_decision_interface())
    results.append(await test_with_real_llms())
    
    # Résumé
    print_header("RÉSUMÉ")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Tests réussis: {passed}/{total}")
    print(f"  Taux de réussite: {100*passed/total:.1f}%")
    
    if passed == total:
        print("\n  ✅ TOUS LES TESTS SONT PASSÉS !")
        print("\n  Le pipeline adversarial est intégré avec PRISM Consensus.")
        print("  Pour utiliser les vrais LLMs:")
        print("    1. Configurez les arbiters dans Settings UI")
        print("    2. Ou définissez CONSENSUS_SIMULATION=false")
        print("")
        return 0
    else:
        print("\n  ❌ Certains tests ont échoué")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
