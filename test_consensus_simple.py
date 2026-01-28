#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TEST SIMPLE DU PIPELINE DE CONSENSUS                      ║
║                                                                              ║
║  Test rapide pour valider le fonctionnement du système de consensus/débat.  ║
║                                                                              ║
║  Usage: python test_consensus_simple.py                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
    DecisionProposal,
    VoteCount,
    build_vote_prompt,
    generate_decision_hash,
    is_critical_action,
)


def print_header(title: str):
    """Affiche un header formaté."""
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Affiche le résultat d'un test."""
    emoji = "✅" if passed else "❌"
    status = "PASS" if passed else "FAIL"
    print(f"  {emoji} [{status}] {test_name}")
    if details:
        print(f"           └─ {details}")


async def test_basic_approval():
    """Test 1: Approbation avec majorité 2/3."""
    print_header("Test 1: Approbation (2/3 approuve)")
    
    manager = ConsensusManager(timeout_ms=5000, total_providers=3)
    
    proposal_id = await manager.propose(
        generate_decision_hash("recherche_médicale", {"topic": "test"}),
        {
            "action": "Valider conclusion de recherche",
            "context": "Test de validation simple"
        },
        DecisionType.RESEARCH_VALIDATION
    )
    
    # 2 APPROVE + 1 REJECT = APPROVED (2/3 quorum)
    manager.submit_vote(proposal_id, "Claude", VoteType.APPROVE, 
                       "Analyse cohérente et sources vérifiées", 0.9)
    manager.submit_vote(proposal_id, "GPT-4", VoteType.APPROVE, 
                       "Données scientifiques valides", 0.85)
    manager.submit_vote(proposal_id, "Gemini", VoteType.REJECT, 
                       "Besoin de plus de sources", 0.6)
    
    await asyncio.sleep(0.2)
    
    status = manager.get_proposal_status(proposal_id)
    passed = status["status"] == ConsensusStatus.APPROVED
    
    print_result(
        "2 APPROVE + 1 REJECT → APPROVED",
        passed,
        f"Status: {status['status'].value}, Votes: {status['votes']}"
    )
    return passed


async def test_basic_rejection():
    """Test 2: Rejet avec majorité 2/3."""
    print_header("Test 2: Rejet (2/3 rejette)")
    
    manager = ConsensusManager(timeout_ms=5000, total_providers=3)
    
    proposal_id = await manager.propose(
        generate_decision_hash("action_risquée", {"topic": "test"}),
        {
            "action": "Exécuter action potentiellement dangereuse",
            "context": "Test de rejet"
        },
        DecisionType.CRITICAL
    )
    
    # 2 REJECT + 1 APPROVE = REJECTED (2/3 quorum)
    manager.submit_vote(proposal_id, "Claude", VoteType.REJECT, 
                       "Action trop risquée", 0.95)
    manager.submit_vote(proposal_id, "GPT-4", VoteType.REJECT, 
                       "Sources non vérifiées", 0.88)
    manager.submit_vote(proposal_id, "Gemini", VoteType.APPROVE, 
                       "Semble OK", 0.5)
    
    await asyncio.sleep(0.2)
    
    status = manager.get_proposal_status(proposal_id)
    passed = status["status"] == ConsensusStatus.REJECTED
    
    print_result(
        "2 REJECT + 1 APPROVE → REJECTED",
        passed,
        f"Status: {status['status'].value}, Votes: {status['votes']}"
    )
    return passed


async def test_no_consensus():
    """Test 3: Pas de consensus (votes divisés)."""
    print_header("Test 3: Pas de consensus (votes divisés)")
    
    manager = ConsensusManager(timeout_ms=5000, total_providers=3)
    
    proposal_id = await manager.propose(
        generate_decision_hash("decision_incertaine", {"topic": "test"}),
        {
            "action": "Décision avec incertitude",
            "context": "Test de non-consensus"
        },
        DecisionType.CRITICAL
    )
    
    # 1 APPROVE + 1 REJECT + 1 ABSTAIN = NO_CONSENSUS
    manager.submit_vote(proposal_id, "Claude", VoteType.APPROVE, 
                       "Je suis pour", 0.6)
    manager.submit_vote(proposal_id, "GPT-4", VoteType.REJECT, 
                       "Je suis contre", 0.6)
    manager.submit_vote(proposal_id, "Gemini", VoteType.ABSTAIN, 
                       "Je ne peux pas décider", 0.3)
    
    await asyncio.sleep(0.2)
    
    status = manager.get_proposal_status(proposal_id)
    passed = status["status"] == ConsensusStatus.NO_CONSENSUS
    
    print_result(
        "1 APPROVE + 1 REJECT + 1 ABSTAIN → NO_CONSENSUS",
        passed,
        f"Status: {status['status'].value}, Votes: {status['votes']}"
    )
    return passed


async def test_infra_failure():
    """Test 4: Échec infrastructure (tous indisponibles)."""
    print_header("Test 4: Échec infrastructure (3 UNAVAILABLE)")
    
    manager = ConsensusManager(timeout_ms=5000, total_providers=3)
    
    proposal_id = await manager.propose(
        generate_decision_hash("test_infra", {"topic": "test"}),
        {
            "action": "Test avec arbitres indisponibles",
            "context": "Test d'échec infra"
        },
        DecisionType.CRITICAL
    )
    
    # 3 unavailable = INFRA_FAILURE (pas de vrais votes)
    manager.submit_vote(
        proposal_id,
        "Claude",
        None,
        "Timeout",
        0.0,
        available=False,
        availability_reason="timeout",
    )
    manager.submit_vote(
        proposal_id,
        "GPT-4",
        None,
        "Connection error",
        0.0,
        available=False,
        availability_reason="error",
    )
    manager.submit_vote(
        proposal_id,
        "Gemini",
        None,
        "Rate limited",
        0.0,
        available=False,
        availability_reason="rate_limited",
    )
    
    await asyncio.sleep(0.2)
    
    status = manager.get_proposal_status(proposal_id)
    passed = status["status"] == ConsensusStatus.INFRA_FAILURE
    
    print_result(
        "3 UNAVAILABLE → INFRA_FAILURE",
        passed,
        f"Status: {status['status'].value}, Votes: {status['votes']}"
    )
    return passed


async def test_timeout():
    """Test 5: Timeout (fail-closed)."""
    print_header("Test 5: Timeout (fail-closed)")
    
    # Manager avec timeout très court
    manager = ConsensusManager(timeout_ms=200, total_providers=3)
    
    proposal_id = await manager.propose(
        generate_decision_hash("test_timeout", {"topic": "test"}),
        {
            "action": "Test de timeout",
            "context": "Aucun vote soumis"
        },
        DecisionType.CRITICAL
    )
    
    # Ne pas soumettre de votes, attendre timeout
    await asyncio.sleep(0.4)
    
    status = manager.get_proposal_status(proposal_id)
    passed = status["status"] == ConsensusStatus.INFRA_FAILURE
    
    print_result(
        "Aucun vote + timeout → INFRA_FAILURE",
        passed,
        f"Status: {status['status'].value}"
    )
    return passed


async def test_partial_availability():
    """Test 6: Disponibilité partielle (2 APPROVE + 1 UNAVAILABLE)."""
    print_header("Test 6: Disponibilité partielle")
    
    manager = ConsensusManager(timeout_ms=5000, total_providers=3)
    
    proposal_id = await manager.propose(
        generate_decision_hash("test_partial", {"topic": "test"}),
        {
            "action": "Décision avec un arbitre indisponible",
            "context": "Test partiel"
        },
        DecisionType.CRITICAL
    )
    
    # 2 APPROVE + 1 unavailable = APPROVED (2 votes effectifs suffisent)
    manager.submit_vote(proposal_id, "Claude", VoteType.APPROVE, 
                       "Validé", 0.9)
    manager.submit_vote(proposal_id, "GPT-4", VoteType.APPROVE, 
                       "OK", 0.85)
    manager.submit_vote(
        proposal_id,
        "Gemini",
        None,
        "Timeout",
        0.0,
        available=False,
        availability_reason="timeout",
    )
    
    await asyncio.sleep(0.2)
    
    status = manager.get_proposal_status(proposal_id)
    passed = status["status"] == ConsensusStatus.APPROVED
    
    print_result(
        "2 APPROVE + 1 unavailable → APPROVED",
        passed,
        f"Status: {status['status'].value}, Votes: {status['votes']}"
    )
    return passed


def test_vote_count_calculation():
    """Test 7: Calcul des votes effectifs."""
    print_header("Test 7: Calcul VoteCount.effective_votes")
    
    count = VoteCount(
        approvals=2,
        rejections=1,
        abstentions=1,
        unavailable=2,
        total=6
    )
    
    # effective_votes = approvals + rejections + abstentions (exclut UNAVAILABLE)
    expected_effective = 4  # 2 + 1 + 1
    passed = count.effective_votes == expected_effective
    
    print_result(
        f"effective_votes = {count.effective_votes} (attendu: {expected_effective})",
        passed,
        f"Approvals: {count.approvals}, Rejections: {count.rejections}, "
        f"Abstentions: {count.abstentions}, Unavailable: {count.unavailable}"
    )
    return passed


def test_critical_action_detection():
    """Test 8: Détection des actions critiques."""
    print_header("Test 8: Détection actions critiques")
    
    critical_tests = [
        ("delete_user_data", True),
        ("publish_conclusion", True),
        ("final_recommendation", True),
        ("system_config_update", True),
        ("get_user_profile", False),
        ("search_papers", False),
    ]
    
    all_passed = True
    for action, expected in critical_tests:
        result = is_critical_action(action)
        passed = result == expected
        all_passed = all_passed and passed
        emoji = "✓" if passed else "✗"
        print(f"    {emoji} is_critical_action('{action}') = {result} (attendu: {expected})")
    
    print_result("Détection actions critiques", all_passed)
    return all_passed


def test_vote_prompt_generation():
    """Test 9: Génération du prompt de vote."""
    print_header("Test 9: Génération prompt de vote")
    
    prompt = build_vote_prompt(
        "Valider la conclusion de recherche sur les biomarqueurs",
        {
            "domain": "médical",
            "sources": ["PubMed", "Nature"],
            "confidence": 0.85
        }
    )
    
    checks = [
        ("Action incluse", "biomarqueurs" in prompt),
        ("Contexte JSON", "domain" in prompt and "médical" in prompt),
        ("Instructions JSON", '"approve"' in prompt.lower()),
        ("Critères d'évaluation", "réversible" in prompt.lower() or "évaluation" in prompt.lower()),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print(f"    {emoji} {check_name}")
    
    print_result("Génération prompt", all_passed)
    return all_passed


async def test_events_emission():
    """Test 10: Émission des événements."""
    print_header("Test 10: Émission événements")
    
    manager = ConsensusManager(timeout_ms=5000, total_providers=3)
    
    events = []
    manager.on("proposal_created", lambda d: events.append(("created", d)))
    manager.on("vote_submitted", lambda d: events.append(("vote", d)))
    manager.on("consensus_reached", lambda d: events.append(("consensus", d)))
    
    proposal_id = await manager.propose(
        generate_decision_hash("test_events", {}),
        {"action": "test"},
        DecisionType.CRITICAL
    )
    
    manager.submit_vote(proposal_id, "Claude", VoteType.APPROVE, "OK", 0.9)
    manager.submit_vote(proposal_id, "GPT-4", VoteType.APPROVE, "OK", 0.9)
    manager.submit_vote(proposal_id, "Gemini", VoteType.REJECT, "Non", 0.5)
    
    await asyncio.sleep(0.2)
    
    event_types = [e[0] for e in events]
    checks = [
        ("Événement 'created'", "created" in event_types),
        ("Événement 'vote'", "vote" in event_types),
        ("Événement 'consensus'", "consensus" in event_types),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print(f"    {emoji} {check_name}")
    
    print_result("Émission événements", all_passed)
    return all_passed


async def main():
    """Exécute tous les tests."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                    🧪 TEST DU PIPELINE DE CONSENSUS 🧪                       ║")
    print("║                                                                              ║")
    print("║  Validation du système de consensus multi-IA pour décisions critiques.       ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    results = []
    
    # Tests async
    results.append(await test_basic_approval())
    results.append(await test_basic_rejection())
    results.append(await test_no_consensus())
    results.append(await test_infra_failure())
    results.append(await test_timeout())
    results.append(await test_partial_availability())
    results.append(await test_events_emission())
    
    # Tests sync
    results.append(test_vote_count_calculation())
    results.append(test_critical_action_detection())
    results.append(test_vote_prompt_generation())
    
    # Résumé
    print_header("RÉSUMÉ")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Tests réussis: {passed}/{total}")
    print(f"  Tests échoués: {total - passed}/{total}")
    
    if passed == total:
        print("\n  ✅ TOUS LES TESTS SONT PASSÉS !")
        print("  Le pipeline de consensus fonctionne correctement.\n")
        return 0
    else:
        print("\n  ❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("  Vérifiez la configuration et les logs.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
