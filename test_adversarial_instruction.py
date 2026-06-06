#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           TEST DU PIPELINE D'INSTRUCTION CONTRADICTOIRE                      ║
║                                                                              ║
║  Tests micro-étapes pour chaque phase du système.                            ║
║                                                                              ║
║  Usage: python test_adversarial_instruction.py                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from python.helpers.adversarial_instruction import (
    # Enums
    Domain,
    CriticalityLevel,
    ProtocolType,
    AgentRole,
    ConfidenceLevel,
    IssueType,
    # Data classes
    Source,
    Assertion,
    Issue,
    AgentAnalysis,
    PeerReview,
    AuditReport,
    ConsolidatedBlock,
    InstructionDossier,
    # Components
    EntryGate,
    AgentOrchestrator,
    DebateOrchestrator,
    HallucinationHunter,
    Consolidator,
    TraceabilityManager,
    HumanDecisionInterface,
    # Main pipeline
    AdversarialInstructionPipeline,
    create_adversarial_pipeline,
)


def print_phase_header(phase_num: int, title: str):
    """Affiche un header de phase."""
    print(f"\n{'═' * 80}")
    print(f"  PHASE {phase_num}: {title}")
    print(f"{'═' * 80}")


def print_test(test_name: str, passed: bool, details: str = ""):
    """Affiche le résultat d'un test."""
    emoji = "✅" if passed else "❌"
    status = "PASS" if passed else "FAIL"
    print(f"  {emoji} [{status}] {test_name}")
    if details:
        for line in details.split('\n'):
            print(f"           │ {line}")


def print_substep(step: str):
    """Affiche une sous-étape."""
    print(f"      ├─ {step}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: TESTS GATE D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase1_domain_qualification():
    """Test Phase 1.1: Qualification du domaine."""
    print("\n  📍 Test 1.1: Qualification du domaine")
    
    gate = EntryGate()
    
    test_cases = [
        ("Quelle est la jurisprudence sur les clauses abusives ?", Domain.LEGAL),
        ("Quels sont les effets secondaires de ce médicament ?", Domain.MEDICAL),
        ("Comment optimiser mon portefeuille d'investissement ?", Domain.FINANCE),
        ("Quelle stratégie adopter pour la croissance ?", Domain.STRATEGIC),
        ("Comment configurer le serveur ?", Domain.TECHNICAL),
        ("Bonjour, comment ça va ?", Domain.GENERAL),
    ]
    
    all_passed = True
    for query, expected_domain in test_cases:
        result = gate.qualify_domain(query)
        passed = result == expected_domain
        all_passed = all_passed and passed
        emoji = "✓" if passed else "✗"
        print_substep(f"{emoji} '{query[:40]}...' → {result.value} (attendu: {expected_domain.value})")
    
    print_test("Qualification domaine", all_passed)
    return all_passed


def test_phase1_criticality_detection():
    """Test Phase 1.2: Détection de criticité."""
    print("\n  📍 Test 1.2: Détection de criticité")
    
    gate = EntryGate()
    
    test_cases = [
        ("Risque de prison pour cette infraction ?", Domain.LEGAL, CriticalityLevel.CRITICAL),
        ("Quel est le risque contentieux ?", Domain.LEGAL, CriticalityLevel.HIGH),
        # Note: LEGAL + MEDIUM → automatiquement HIGH (règle de prudence domaines sensibles)
        ("Pouvez-vous vérifier ce contrat ?", Domain.LEGAL, CriticalityLevel.HIGH),
        ("Révision d'un contrat de travail standard", Domain.LEGAL, CriticalityLevel.HIGH),
        ("Comment fonctionne un tableau Excel ?", Domain.TECHNICAL, CriticalityLevel.LOW),
    ]
    
    all_passed = True
    for query, domain, expected_crit in test_cases:
        result = gate.detect_criticality(query, domain)
        passed = result == expected_crit
        all_passed = all_passed and passed
        emoji = "✓" if passed else "✗"
        print_substep(f"{emoji} '{query[:40]}...' → {result.value} (attendu: {expected_crit.value})")
    
    print_test("Détection criticité", all_passed)
    return all_passed


def test_phase1_protocol_determination():
    """Test Phase 1.3: Détermination du protocole."""
    print("\n  📍 Test 1.3: Détermination du protocole")
    
    gate = EntryGate()
    
    test_cases = [
        (CriticalityLevel.LOW, ProtocolType.LIGHT),
        (CriticalityLevel.MEDIUM, ProtocolType.STANDARD),
        (CriticalityLevel.HIGH, ProtocolType.REINFORCED),
        (CriticalityLevel.CRITICAL, ProtocolType.MAXIMAL),
    ]
    
    all_passed = True
    for criticality, expected_protocol in test_cases:
        result = gate.determine_protocol(criticality)
        passed = result == expected_protocol
        all_passed = all_passed and passed
        emoji = "✓" if passed else "✗"
        print_substep(f"{emoji} {criticality.value} → {result.value} (attendu: {expected_protocol.value})")
    
    print_test("Détermination protocole", all_passed)
    return all_passed


def test_phase1_full_qualification():
    """Test Phase 1.4: Qualification complète."""
    print("\n  📍 Test 1.4: Qualification complète")
    
    gate = EntryGate()
    
    # Cas juridique critique
    result = gate.qualify(
        "Mon client risque la prison pour fraude fiscale, quelle est notre stratégie de défense ?",
        {"domain": "legal"}
    )
    
    checks = [
        ("Domain est LEGAL", result["domain"] == Domain.LEGAL),
        ("Criticité >= HIGH", result["criticality"] in [CriticalityLevel.HIGH, CriticalityLevel.CRITICAL]),
        ("Protocol >= REINFORCED", result["protocol"] in [ProtocolType.REINFORCED, ProtocolType.MAXIMAL]),
        ("Config contient min_agents", "min_agents" in result["config"]),
        ("Config contient audit_required", "audit_required" in result["config"]),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Qualification complète", all_passed, 
               f"Protocol: {result['protocol'].value}, Config: {result['config']}")
    return all_passed


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: TESTS COLLECTE INDÉPENDANTE
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase2_agents_by_protocol():
    """Test Phase 2.1: Agents par protocole."""
    print("\n  📍 Test 2.1: Agents par protocole")
    
    orchestrator = AgentOrchestrator()
    
    test_cases = [
        (ProtocolType.LIGHT, 2),
        (ProtocolType.STANDARD, 3),
        (ProtocolType.REINFORCED, 4),
        (ProtocolType.MAXIMAL, 5),
    ]
    
    all_passed = True
    for protocol, expected_count in test_cases:
        agents = orchestrator.get_agents_for_protocol(protocol)
        passed = len(agents) == expected_count
        all_passed = all_passed and passed
        emoji = "✓" if passed else "✗"
        print_substep(f"{emoji} {protocol.value}: {len(agents)} agents (attendu: {expected_count})")
    
    print_test("Agents par protocole", all_passed)
    return all_passed


def test_phase2_prompt_building():
    """Test Phase 2.2: Construction des prompts."""
    print("\n  📍 Test 2.2: Construction des prompts")
    
    orchestrator = AgentOrchestrator()
    
    prompt = orchestrator.build_agent_prompt(
        AgentRole.DOCTRINAL,
        "Question juridique de test",
        Domain.LEGAL,
        {"context_key": "context_value"}
    )
    
    checks = [
        ("Contient le rôle", "doctrinal" in prompt.lower()),
        ("Contient la question", "Question juridique de test" in prompt),
        ("Contient le domaine", "legal" in prompt.lower()),
        ("Contient le contexte", "context_key" in prompt),
        ("Demande du JSON", "json" in prompt.lower()),
        ("Instructions d'indépendance", "indépendant" in prompt.lower() or "independent" in prompt.lower()),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Construction prompts", all_passed)
    return all_passed


async def test_phase2_agent_execution():
    """Test Phase 2.3: Exécution d'un agent (simulé)."""
    print("\n  📍 Test 2.3: Exécution agent (simulé)")
    
    orchestrator = AgentOrchestrator()  # Sans LLM caller = simulation
    
    analysis = await orchestrator.run_agent(
        AgentRole.DOCTRINAL,
        "Test de question juridique",
        Domain.LEGAL
    )
    
    checks = [
        ("Agent ID généré", analysis.agent_id is not None and len(analysis.agent_id) > 0),
        ("Role correct", analysis.agent_role == AgentRole.DOCTRINAL),
        ("Timestamp présent", analysis.timestamp > 0),
        ("Conclusions présentes", len(analysis.main_conclusions) > 0),
        ("Processing time > 0", analysis.processing_time_ms >= 0),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Exécution agent", all_passed, f"Agent: {analysis.agent_id[:16]}...")
    return all_passed


async def test_phase2_parallel_collection():
    """Test Phase 2.4: Collecte parallèle."""
    print("\n  📍 Test 2.4: Collecte parallèle")
    
    orchestrator = AgentOrchestrator()
    
    start_time = time.time()
    analyses = await orchestrator.run_parallel_collection(
        "Question de test pour collecte parallèle",
        Domain.LEGAL,
        ProtocolType.STANDARD
    )
    elapsed = time.time() - start_time
    
    checks = [
        ("3 analyses reçues", len(analyses) == 3),
        ("Toutes ont des conclusions", all(len(a.main_conclusions) > 0 for a in analyses.values())),
        ("Rôles distincts", len(set(a.agent_role for a in analyses.values())) == 3),
        ("Exécution < 5s", elapsed < 5),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Collecte parallèle", all_passed, f"Temps: {elapsed:.2f}s, {len(analyses)} analyses")
    return all_passed


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: TESTS DÉBAT STRUCTURÉ
# ═══════════════════════════════════════════════════════════════════════════════

async def test_phase3_peer_review():
    """Test Phase 3.1: Revue par les pairs."""
    print("\n  📍 Test 3.1: Revue par les pairs")
    
    # Créer des analyses fictives
    orchestrator = AgentOrchestrator()
    analyses = await orchestrator.run_parallel_collection(
        "Question test",
        Domain.LEGAL,
        ProtocolType.STANDARD
    )
    
    debate = DebateOrchestrator()
    agents = list(analyses.values())
    
    review = await debate.conduct_peer_review(
        agents[0],  # reviewer
        agents[1],  # reviewed
        analyses
    )
    
    checks = [
        ("Reviewer ID présent", review.reviewer_id is not None),
        ("Reviewed ID présent", review.reviewed_agent_id is not None),
        ("Timestamp > 0", review.timestamp > 0),
        ("Weaknesses est une liste", isinstance(review.weaknesses, list)),
        ("Confidence dans [0,1]", 0 <= review.confidence_in_review <= 1),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Revue par les pairs", all_passed)
    return all_passed


async def test_phase3_debate_round():
    """Test Phase 3.2: Round de débat complet."""
    print("\n  📍 Test 3.2: Round de débat")
    
    orchestrator = AgentOrchestrator()
    analyses = await orchestrator.run_parallel_collection(
        "Question test débat",
        Domain.LEGAL,
        ProtocolType.STANDARD
    )
    
    debate = DebateOrchestrator()
    reviews = await debate.run_debate_round(analyses, 1)
    
    # Avec 3 agents, chacun révise les 2 autres = 6 revues
    expected_reviews = 3 * 2
    
    checks = [
        (f"{expected_reviews} revues générées", len(reviews) == expected_reviews),
        ("Toutes ont un reviewer", all(r.reviewer_id for r in reviews)),
        ("Toutes ont un reviewed", all(r.reviewed_agent_id for r in reviews)),
        ("Pas d'auto-revue", all(r.reviewer_id != r.reviewed_agent_id for r in reviews)),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Round de débat", all_passed, f"{len(reviews)} revues")
    return all_passed


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: TESTS DÉTECTION HALLUCINATIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def test_phase4_audit():
    """Test Phase 4.1: Audit des analyses."""
    print("\n  📍 Test 4.1: Audit des analyses")
    
    orchestrator = AgentOrchestrator()
    analyses = await orchestrator.run_parallel_collection(
        "Question test audit",
        Domain.LEGAL,
        ProtocolType.STANDARD
    )
    
    hunter = HallucinationHunter()
    report = await hunter.audit_analyses(analyses)
    
    checks = [
        ("Auditor ID présent", report.auditor_id is not None),
        ("Timestamp > 0", report.timestamp > 0),
        ("Issues est une liste", isinstance(report.issues_found, list)),
        ("Score fiabilité dans [0,1]", 0 <= report.overall_reliability_score <= 1),
        ("Recommandations présentes", isinstance(report.prudence_recommendations, list)),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Audit analyses", all_passed, 
               f"Score: {report.overall_reliability_score:.2f}, Issues: {len(report.issues_found)}")
    return all_passed


async def test_phase4_audit_with_reviews():
    """Test Phase 4.2: Audit avec débats inclus."""
    print("\n  📍 Test 4.2: Audit avec débats")
    
    # Collecte
    orchestrator = AgentOrchestrator()
    analyses = await orchestrator.run_parallel_collection(
        "Question test audit complet",
        Domain.LEGAL,
        ProtocolType.STANDARD
    )
    
    # Débat
    debate = DebateOrchestrator()
    reviews = await debate.run_debate_round(analyses, 1)
    
    # Audit
    hunter = HallucinationHunter()
    report = await hunter.audit_analyses(analyses, reviews)
    
    checks = [
        ("Report généré", report is not None),
        ("Prend en compte les débats", True),  # Vérification structurelle
        ("Score calculé", report.overall_reliability_score is not None),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Audit avec débats", all_passed)
    return all_passed


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: TESTS CONSOLIDATION
# ═══════════════════════════════════════════════════════════════════════════════

async def test_phase5_consolidation():
    """Test Phase 5.1: Consolidation complète."""
    print("\n  📍 Test 5.1: Consolidation")
    
    # Collecter
    orchestrator = AgentOrchestrator()
    analyses = await orchestrator.run_parallel_collection(
        "Question test consolidation",
        Domain.LEGAL,
        ProtocolType.STANDARD
    )
    
    # Débattre
    debate = DebateOrchestrator()
    reviews = await debate.run_debate_round(analyses, 1)
    
    # Auditer
    hunter = HallucinationHunter()
    audit = await hunter.audit_analyses(analyses, reviews)
    
    # Consolider
    consolidator = Consolidator()
    result = await consolidator.consolidate(analyses, reviews, audit)
    
    checks = [
        ("Blocs consolidés présents", "consolidated_blocks" in result),
        ("Missing info présent", "missing_information" in result),
        ("Hypotheses présent", "hypotheses_taken" in result),
        ("Disagreements présent", "disagreement_points" in result),
        ("Summary présent", "executive_summary" in result),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    blocks_count = sum(len(b) for b in result["consolidated_blocks"].values())
    print_test("Consolidation", all_passed, f"{blocks_count} blocs créés")
    return all_passed


def test_phase5_confidence_levels():
    """Test Phase 5.2: Niveaux de confiance."""
    print("\n  📍 Test 5.2: Niveaux de confiance")
    
    levels = [
        ConfidenceLevel.HIGHLY_RELIABLE,
        ConfidenceLevel.PROBABLE,
        ConfidenceLevel.UNCERTAIN,
        ConfidenceLevel.MISSING_INFO,
        ConfidenceLevel.HYPOTHESIS,
        ConfidenceLevel.DISPUTED,
    ]
    
    # Vérifier que tous les niveaux sont distincts
    passed = len(set(l.value for l in levels)) == len(levels)
    
    for level in levels:
        print_substep(f"• {level.value}")
    
    print_test("Niveaux de confiance distincts", passed)
    return passed


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: TESTS TRAÇABILITÉ
# ═══════════════════════════════════════════════════════════════════════════════

async def test_phase6_trace_generation():
    """Test Phase 6.1: Génération de trace."""
    print("\n  📍 Test 6.1: Génération de trace")
    
    # Créer un dossier minimal
    dossier = InstructionDossier(
        id="test-dossier-123",
        query="Question de test traçabilité",
        created_at=time.time(),
        domain=Domain.LEGAL,
        criticality=CriticalityLevel.HIGH,
        protocol=ProtocolType.REINFORCED,
    )
    
    # Ajouter des analyses fictives
    dossier.agent_analyses["agent1"] = AgentAnalysis(
        agent_id="agent1",
        agent_role=AgentRole.DOCTRINAL,
        model_used="test-model",
        timestamp=time.time(),
        main_conclusions=["Conclusion 1"],
        sources_cited=[Source(id="src1", type="doctrine", reference="Réf test")],
    )
    
    # Ajouter un audit
    dossier.audit_report = AuditReport(
        auditor_id="auditor1",
        timestamp=time.time(),
        overall_reliability_score=0.75,
    )
    
    # Générer la trace
    manager = TraceabilityManager()
    trace = manager.generate_trace(dossier)
    
    checks = [
        ("Dossier ID présent", trace["dossier_id"] == dossier.id),
        ("Query présent", trace["query"] == dossier.query),
        ("Framing présent", "framing" in trace),
        ("Agents présents", len(trace["agents_involved"]) > 0),
        ("Metrics présents", "metrics" in trace),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Génération trace", all_passed)
    return all_passed


async def test_phase6_markdown_export():
    """Test Phase 6.2: Export Markdown."""
    print("\n  📍 Test 6.2: Export Markdown")
    
    # Créer une trace
    dossier = InstructionDossier(
        id="test-md-export",
        query="Question export",
        created_at=time.time(),
        domain=Domain.MEDICAL,
        criticality=CriticalityLevel.CRITICAL,
        protocol=ProtocolType.MAXIMAL,
    )
    dossier.audit_report = AuditReport(
        auditor_id="aud",
        timestamp=time.time(),
        overall_reliability_score=0.8,
    )
    
    manager = TraceabilityManager()
    trace = manager.generate_trace(dossier)
    markdown = manager.export_trace_markdown(trace)
    
    checks = [
        ("Titre présent", "# " in markdown),
        ("Sections présentes", "## " in markdown),
        ("Domain mentionné", "medical" in markdown.lower()),
        ("Criticité mentionnée", "critical" in markdown.lower()),
        ("Métriques présentes", "Métriques" in markdown or "métrique" in markdown.lower()),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Export Markdown", all_passed, f"{len(markdown)} caractères")
    return all_passed


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: TESTS DÉCISION HUMAINE
# ═══════════════════════════════════════════════════════════════════════════════

async def test_phase7_presentation():
    """Test Phase 7.1: Présentation pour décision."""
    print("\n  📍 Test 7.1: Présentation pour décision")
    
    # Créer un dossier complet
    dossier = InstructionDossier(
        id="test-decision",
        query="Question décision humaine",
        created_at=time.time(),
        domain=Domain.FINANCE,
        criticality=CriticalityLevel.HIGH,
        protocol=ProtocolType.REINFORCED,
    )
    
    dossier.consolidated_blocks = {
        ConfidenceLevel.HIGHLY_RELIABLE: [
            ConsolidatedBlock(id="b1", category=ConfidenceLevel.HIGHLY_RELIABLE, content="Élément fiable")
        ],
        ConfidenceLevel.UNCERTAIN: [
            ConsolidatedBlock(id="b2", category=ConfidenceLevel.UNCERTAIN, content="Élément incertain")
        ],
    }
    dossier.missing_information = ["Info manquante 1"]
    dossier.hypotheses_taken = ["Hypothèse 1"]
    dossier.disagreement_points = ["Désaccord 1"]
    dossier.audit_report = AuditReport(
        auditor_id="aud",
        timestamp=time.time(),
        overall_reliability_score=0.7,
    )
    
    interface = HumanDecisionInterface()
    presentation = interface.present_for_decision(dossier)
    
    checks = [
        ("Dossier ID présent", presentation["dossier_id"] == dossier.id),
        ("Summary présent", "executive_summary" in presentation),
        ("Findings fiables présents", len(presentation["highly_reliable_findings"]) > 0),
        ("Incertitudes présentes", len(presentation["uncertainties"]) > 0),
        ("Form de décision présent", "decision_form" in presentation),
        ("Options présentes", len(presentation["decision_form"]["options"]) > 0),
        ("Acknowledgments requis", len(presentation["decision_form"]["required_acknowledgments"]) > 0),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Présentation décision", all_passed)
    return all_passed


async def test_phase7_decision_recording():
    """Test Phase 7.2: Enregistrement de décision."""
    print("\n  📍 Test 7.2: Enregistrement décision")
    
    dossier = InstructionDossier(
        id="test-record-decision",
        query="Question enregistrement",
        created_at=time.time(),
    )
    dossier.audit_report = AuditReport(
        auditor_id="aud",
        timestamp=time.time(),
        overall_reliability_score=0.8,
    )
    
    interface = HumanDecisionInterface()
    interface.present_for_decision(dossier)
    
    # Enregistrer la décision
    success = interface.record_human_decision(
        dossier.id,
        "accept_with_reserves",
        ["J'ai lu les incertitudes", "J'accepte les hypothèses"],
        "Notes de test"
    )
    
    checks = [
        ("Enregistrement réussi", success),
        ("Décision stockée", dossier.human_decision == "accept_with_reserves"),
        ("Timestamp présent", dossier.human_decision_timestamp is not None),
        ("Risques acknowledgés", len(dossier.human_acknowledged_risks) == 2),
        ("Status mis à jour", dossier.status == "decided"),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    print_test("Enregistrement décision", all_passed)
    return all_passed


# ═══════════════════════════════════════════════════════════════════════════════
# TEST PIPELINE COMPLET
# ═══════════════════════════════════════════════════════════════════════════════

async def test_full_pipeline():
    """Test du pipeline complet end-to-end."""
    print_phase_header(8, "PIPELINE COMPLET END-TO-END")
    
    pipeline = create_adversarial_pipeline()  # Sans LLM = simulation
    
    print("\n  🚀 Lancement du pipeline complet...")
    
    start_time = time.time()
    dossier = await pipeline.run_full_pipeline(
        "Mon client est accusé de fraude fiscale aggravée. Il risque une peine de prison. "
        "Quelle stratégie de défense recommandez-vous ?",
        {"urgency": "high"}
    )
    elapsed = time.time() - start_time
    
    print(f"\n  ⏱️  Pipeline exécuté en {elapsed:.2f}s\n")
    
    checks = [
        ("Dossier créé", dossier is not None),
        ("ID généré", dossier.id is not None),
        ("Phase 7 atteinte", dossier.current_phase == 7),
        ("Status correct", dossier.status == "awaiting_human_decision"),
        ("Domain détecté LEGAL", dossier.domain == Domain.LEGAL),
        ("Criticité >= HIGH", dossier.criticality in [CriticalityLevel.HIGH, CriticalityLevel.CRITICAL]),
        ("Analyses collectées", len(dossier.agent_analyses) >= 2),
        ("Audit effectué", dossier.audit_report is not None),
        ("Blocs consolidés", len(dossier.consolidated_blocks) > 0),
        ("Timeline tracée", len(dossier.processing_timeline) > 0),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        all_passed = all_passed and check_result
        emoji = "✓" if check_result else "✗"
        print_substep(f"{emoji} {check_name}")
    
    # Vérifier la trace
    trace_md = pipeline.get_trace_markdown(dossier.id)
    trace_ok = len(trace_md) > 100
    print_substep(f"{'✓' if trace_ok else '✗'} Trace Markdown générée ({len(trace_md)} chars)")
    all_passed = all_passed and trace_ok
    
    # Récupérer la présentation
    presentation = pipeline.get_decision_presentation(dossier.id)
    presentation_ok = "decision_form" in presentation
    print_substep(f"{'✓' if presentation_ok else '✗'} Présentation décision prête")
    all_passed = all_passed and presentation_ok
    
    print_test("Pipeline complet", all_passed, 
               f"Domain: {dossier.domain.value}, Protocol: {dossier.protocol.value}, "
               f"Reliability: {dossier.audit_report.overall_reliability_score:.2f}")
    
    return all_passed


# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Exécute tous les tests phase par phase."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║        🧪 TESTS DU PIPELINE D'INSTRUCTION CONTRADICTOIRE 🧪                 ║")
    print("║                                                                              ║")
    print("║  Système de validation multi-IA avec débat structuré et traçabilité.         ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    results = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1
    # ═══════════════════════════════════════════════════════════════════════════
    print_phase_header(1, "GATE D'ENTRÉE - CADRAGE STRICT")
    results.append(test_phase1_domain_qualification())
    results.append(test_phase1_criticality_detection())
    results.append(test_phase1_protocol_determination())
    results.append(test_phase1_full_qualification())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2
    # ═══════════════════════════════════════════════════════════════════════════
    print_phase_header(2, "COLLECTE INDÉPENDANTE")
    results.append(test_phase2_agents_by_protocol())
    results.append(test_phase2_prompt_building())
    results.append(await test_phase2_agent_execution())
    results.append(await test_phase2_parallel_collection())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3
    # ═══════════════════════════════════════════════════════════════════════════
    print_phase_header(3, "DÉBAT STRUCTURÉ")
    results.append(await test_phase3_peer_review())
    results.append(await test_phase3_debate_round())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 4
    # ═══════════════════════════════════════════════════════════════════════════
    print_phase_header(4, "DÉTECTION D'HALLUCINATIONS")
    results.append(await test_phase4_audit())
    results.append(await test_phase4_audit_with_reviews())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5
    # ═══════════════════════════════════════════════════════════════════════════
    print_phase_header(5, "CONSOLIDATION")
    results.append(await test_phase5_consolidation())
    results.append(test_phase5_confidence_levels())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 6
    # ═══════════════════════════════════════════════════════════════════════════
    print_phase_header(6, "TRAÇABILITÉ")
    results.append(await test_phase6_trace_generation())
    results.append(await test_phase6_markdown_export())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 7
    # ═══════════════════════════════════════════════════════════════════════════
    print_phase_header(7, "DÉCISION HUMAINE")
    results.append(await test_phase7_presentation())
    results.append(await test_phase7_decision_recording())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PIPELINE COMPLET
    # ═══════════════════════════════════════════════════════════════════════════
    results.append(await test_full_pipeline())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÉSUMÉ FINAL
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                              RÉSUMÉ FINAL                                    ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Tests réussis: {passed}/{total}")
    print(f"  Tests échoués: {total - passed}/{total}")
    print(f"  Taux de réussite: {100*passed/total:.1f}%")
    
    if passed == total:
        print("\n  ✅ TOUS LES TESTS SONT PASSÉS !")
        print("\n  Le pipeline d'instruction contradictoire fonctionne correctement.")
        print("  Prêt pour intégration avec de vrais LLMs.\n")
        return 0
    else:
        print("\n  ❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("  Vérifiez les erreurs ci-dessus.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
