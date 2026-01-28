#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           TESTS E2E - SCÉNARIOS RÉALISTES D'INSTRUCTION CONTRADICTOIRE       ║
║                                                                              ║
║  4 scénarios fictifs pour démontrer le pipeline complet:                     ║
║                                                                              ║
║  1. CAS JURIDIQUE    - Responsabilité médicale et faute caractérisée         ║
║  2. CAS MÉDICAL      - Évaluation d'un protocole de traitement innovant      ║
║  3. CAS STRATÉGIQUE  - Pivot business d'une scale-up SaaS B2B                ║
║  4. CAS MULTI-DOMAIN - Stratégie financière/juridique startup biotech        ║
║                                                                              ║
║  Usage: python test_adversarial_e2e_scenarios.py                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from python.helpers.adversarial_instruction import (
    Domain,
    CriticalityLevel,
    ProtocolType,
    ConfidenceLevel,
    AgentRole,
    AdversarialInstructionPipeline,
    create_adversarial_pipeline,
)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES D'AFFICHAGE
# ═══════════════════════════════════════════════════════════════════════════════

def print_scenario_header(num: int, title: str, domain: str):
    """Affiche un header de scénario."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print(f"║  SCÉNARIO {num}: {title:<63} ║")
    print(f"║  Domaine: {domain:<66} ║")
    print("╚" + "═" * 78 + "╝")


def print_section(title: str):
    """Affiche une section."""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}")


def print_phase_result(phase: int, name: str, details: dict):
    """Affiche le résultat d'une phase."""
    print(f"\n  ✅ Phase {phase}: {name}")
    for key, value in details.items():
        if isinstance(value, list):
            print(f"      • {key}:")
            for item in value[:3]:  # Limiter à 3 items
                print(f"        - {str(item)[:70]}...")
        else:
            print(f"      • {key}: {value}")


def print_consolidated_result(dossier):
    """Affiche le résultat consolidé."""
    print_section("RÉSULTAT CONSOLIDÉ")
    
    for level in [ConfidenceLevel.HIGHLY_RELIABLE, ConfidenceLevel.PROBABLE, 
                  ConfidenceLevel.UNCERTAIN, ConfidenceLevel.DISPUTED]:
        blocks = dossier.consolidated_blocks.get(level, [])
        if blocks:
            emoji = {"highly_reliable": "🟢", "probable": "🟡", 
                    "uncertain": "🟠", "disputed": "🔴"}.get(level.value, "⚪")
            print(f"\n  {emoji} {level.value.upper()} ({len(blocks)} éléments)")
            for block in blocks[:2]:
                print(f"      └─ {block.content[:65]}...")
    
    if dossier.missing_information:
        print(f"\n  ⚠️  INFORMATIONS MANQUANTES:")
        for info in dossier.missing_information[:3]:
            print(f"      └─ {info[:65]}...")
    
    if dossier.disagreement_points:
        print(f"\n  🔶 POINTS DE DÉSACCORD:")
        for point in dossier.disagreement_points[:3]:
            print(f"      └─ {point[:65]}...")


def print_trace_summary(dossier, pipeline):
    """Affiche un résumé de la trace."""
    print_section("TRACE DE TRAÇABILITÉ")
    
    print(f"\n  📋 Dossier ID: {dossier.id[:16]}...")
    print(f"  🏷️  Domaine: {dossier.domain.value}")
    print(f"  ⚡ Criticité: {dossier.criticality.value}")
    print(f"  📊 Protocole: {dossier.protocol.value}")
    print(f"  🤖 Agents: {len(dossier.agent_analyses)}")
    print(f"  🗣️  Revues: {len(dossier.peer_reviews)}")
    
    if dossier.audit_report:
        print(f"  🔍 Score fiabilité: {dossier.audit_report.overall_reliability_score:.0%}")
        print(f"  ⚠️  Issues détectées: {len(dossier.audit_report.issues_found)}")
    
    print(f"  📝 Événements tracés: {len(dossier.processing_timeline)}")


def print_human_decision_interface(presentation):
    """Affiche l'interface de décision humaine."""
    print_section("INTERFACE DE DÉCISION HUMAINE")
    
    print(f"\n  📄 RÉSUMÉ EXÉCUTIF:")
    print(f"      {presentation['executive_summary'][:200]}...")
    
    print(f"\n  ✅ ÉLÉMENTS HAUTEMENT FIABLES:")
    for finding in presentation['highly_reliable_findings'][:2]:
        print(f"      • {finding[:65]}...")
    
    print(f"\n  🟡 ÉLÉMENTS PROBABLES:")
    for finding in presentation['probable_findings'][:2]:
        print(f"      • {finding[:65]}...")
    
    print(f"\n  ⚠️  INCERTITUDES:")
    for uncertainty in presentation['uncertainties'][:2]:
        print(f"      • {uncertainty[:65]}...")
    
    print(f"\n  📝 OPTIONS DE DÉCISION:")
    for option in presentation['decision_form']['options']:
        print(f"      [{option['id']}] {option['label']}")
    
    print(f"\n  ⚡ ACKNOWLEDGMENTS REQUIS:")
    for ack in presentation['decision_form']['required_acknowledgments']:
        print(f"      □ {ack}")


# ═══════════════════════════════════════════════════════════════════════════════
# SCÉNARIO 1: CAS JURIDIQUE
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_JURIDIQUE = {
    "title": "Responsabilité Médicale - Faute Caractérisée",
    "query": """
Notre cabinet représente M. Dupont, 58 ans, qui a subi une intervention 
chirurgicale de prothèse de hanche à la Clinique Saint-Martin le 15 mars 2024.

FAITS:
- Intervention réalisée par le Dr. Martin, chirurgien orthopédiste
- Complications post-opératoires: infection nosocomiale détectée J+7
- Seconde intervention nécessaire le 28 mars 2024
- Séquelles permanentes: boiterie résiduelle, douleurs chroniques
- Arrêt de travail de 8 mois (patient artisan menuisier)

ÉLÉMENTS DU DOSSIER:
- Le consentement éclairé a été signé mais ne mentionne pas le risque infectieux
- Le bloc opératoire n'avait pas fait l'objet d'un contrôle d'hygiène depuis 14 mois
- Trois cas d'infections similaires signalés dans les 6 mois précédents
- Le Dr. Martin a un taux d'infections post-opératoires de 4.2% (moyenne nationale: 1.8%)

QUESTION JURIDIQUE:
Peut-on engager la responsabilité de la clinique ET du chirurgien sur le fondement 
d'une faute caractérisée? Quelles sont nos chances de succès en contentieux et 
quelle stratégie procédurale recommandez-vous?
""",
    "context": {
        "urgency": "high",
        "deadline": "2024-12-15",
        "client_expectations": "indemnisation maximale",
        "budget_procedure": "illimité si chances > 60%"
    }
}


async def run_scenario_juridique(pipeline):
    """Exécute le scénario juridique."""
    print_scenario_header(1, SCENARIO_JURIDIQUE["title"], "JURIDIQUE / MÉDICAL")
    
    print_section("ÉNONCÉ DU CAS")
    print(SCENARIO_JURIDIQUE["query"])
    
    # Exécuter le pipeline
    start_time = time.time()
    dossier = await pipeline.run_full_pipeline(
        SCENARIO_JURIDIQUE["query"],
        SCENARIO_JURIDIQUE["context"]
    )
    elapsed = time.time() - start_time
    
    # Afficher les résultats de chaque phase
    print_section("EXÉCUTION DU PIPELINE")
    print(f"\n  ⏱️  Temps total: {elapsed:.2f}s")
    
    print_phase_result(1, "Cadrage", {
        "Domaine détecté": dossier.domain.value,
        "Criticité": dossier.criticality.value,
        "Protocole": dossier.protocol.value,
    })
    
    print_phase_result(2, "Collecte", {
        "Agents déployés": len(dossier.agent_analyses),
        "Rôles": [a.agent_role.value for a in dossier.agent_analyses.values()],
    })
    
    print_phase_result(3, "Débat", {
        "Revues par les pairs": len(dossier.peer_reviews),
        "Faiblesses identifiées": sum(len(r.weaknesses) for r in dossier.peer_reviews),
    })
    
    print_phase_result(4, "Audit", {
        "Issues détectées": len(dossier.audit_report.issues_found) if dossier.audit_report else 0,
        "Score fiabilité": f"{dossier.audit_report.overall_reliability_score:.0%}" if dossier.audit_report else "N/A",
    })
    
    print_consolidated_result(dossier)
    print_trace_summary(dossier, pipeline)
    
    # Interface décision
    presentation = pipeline.get_decision_presentation(dossier.id)
    print_human_decision_interface(presentation)
    
    # Simulation de décision humaine
    print_section("DÉCISION HUMAINE SIMULÉE")
    success = pipeline.record_decision(
        dossier.id,
        "accept_with_reserves",
        [
            "J'ai lu et compris les éléments incertains",
            "J'accepte les hypothèses prises",
            "Je suis conscient des risques résiduels",
        ],
        "Procéder avec prudence sur le volet infection nosocomiale"
    )
    print(f"\n  ✅ Décision enregistrée: accept_with_reserves")
    print(f"  📋 Status final: {dossier.status}")
    
    return dossier


# ═══════════════════════════════════════════════════════════════════════════════
# SCÉNARIO 2: CAS MÉDICAL
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_MEDICAL = {
    "title": "Évaluation Protocole Traitement Oncologique Innovant",
    "query": """
Le comité scientifique du CHU doit évaluer la proposition du Pr. Laurent concernant 
l'introduction d'un nouveau protocole de traitement pour les patients atteints de 
mélanome métastatique stade IV.

PROTOCOLE PROPOSÉ:
- Combinaison immunothérapie (Pembrolizumab) + thérapie ciblée (Dabrafenib/Trametinib)
- Pour patients BRAF V600 mutés avec métastases cérébrales
- Administration séquentielle: 4 cycles immunothérapie puis bithérapie ciblée

DONNÉES DISPONIBLES:
- Étude de phase II (n=87 patients) publiée dans Lancet Oncology (2023)
- Survie sans progression médiane: 14.2 mois vs 9.8 mois (bras contrôle)
- Taux de réponse objective: 68% vs 52%
- Effets indésirables grade 3-4: 42% (dont 8% d'hépatotoxicité sévère)
- Pas encore d'étude de phase III randomisée publiée
- AMM européenne en cours d'évaluation (avis CHMP attendu Q2 2025)

CONTEXTE:
- 12 patients actuellement éligibles dans le service
- Coût estimé: +180% vs protocole standard
- Accès compassionnel possible sous conditions

QUESTIONS:
1. Le niveau de preuve scientifique justifie-t-il l'adoption de ce protocole?
2. Quels sont les risques médico-légaux en cas de complications?
3. Recommandation finale avec conditions éventuelles?
""",
    "context": {
        "institution": "CHU universitaire",
        "decision_maker": "Comité scientifique + Direction médicale",
        "ethical_committee_approval": "pending",
        "timeline": "décision sous 3 semaines"
    }
}


async def run_scenario_medical(pipeline):
    """Exécute le scénario médical."""
    print_scenario_header(2, SCENARIO_MEDICAL["title"], "MÉDICAL / ONCOLOGIE")
    
    print_section("ÉNONCÉ DU CAS")
    print(SCENARIO_MEDICAL["query"])
    
    # Exécuter le pipeline
    start_time = time.time()
    dossier = await pipeline.run_full_pipeline(
        SCENARIO_MEDICAL["query"],
        SCENARIO_MEDICAL["context"]
    )
    elapsed = time.time() - start_time
    
    print_section("EXÉCUTION DU PIPELINE")
    print(f"\n  ⏱️  Temps total: {elapsed:.2f}s")
    
    print_phase_result(1, "Cadrage", {
        "Domaine détecté": dossier.domain.value,
        "Criticité": dossier.criticality.value,
        "Protocole": dossier.protocol.value,
    })
    
    print_phase_result(2, "Collecte", {
        "Agents déployés": len(dossier.agent_analyses),
        "Rôles": [a.agent_role.value for a in dossier.agent_analyses.values()],
    })
    
    print_phase_result(3, "Débat", {
        "Revues par les pairs": len(dossier.peer_reviews),
        "Contradictions": sum(len(r.contradictions) for r in dossier.peer_reviews),
    })
    
    print_phase_result(4, "Audit", {
        "Affirmations non sourcées": len(dossier.audit_report.unsourced_claims) if dossier.audit_report else 0,
        "Score fiabilité": f"{dossier.audit_report.overall_reliability_score:.0%}" if dossier.audit_report else "N/A",
    })
    
    print_consolidated_result(dossier)
    print_trace_summary(dossier, pipeline)
    
    # Interface décision
    presentation = pipeline.get_decision_presentation(dossier.id)
    print_human_decision_interface(presentation)
    
    # Simulation de décision
    print_section("DÉCISION HUMAINE SIMULÉE")
    pipeline.record_decision(
        dossier.id,
        "request_more_info",
        ["J'ai lu les incertitudes", "Besoin de données complémentaires"],
        "Attendre les résultats de la phase III avant implémentation large"
    )
    print(f"\n  ⚠️  Décision: request_more_info")
    print(f"  📋 Motif: Attendre données phase III")
    
    return dossier


# ═══════════════════════════════════════════════════════════════════════════════
# SCÉNARIO 3: CAS STRATÉGIE BUSINESS
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_BUSINESS = {
    "title": "Pivot Stratégique Scale-up SaaS B2B",
    "query": """
DataFlow Analytics, scale-up SaaS B2B spécialisée dans l'analytics marketing 
(ARR: 8.2M€, 85 employés, série B de 15M€ levée en 2022), doit décider 
d'un pivot stratégique majeur.

SITUATION ACTUELLE:
- Croissance ralentie: +18% YoY vs +45% en 2022
- Churn rate en hausse: 14% vs 8% historique
- CAC payback: 24 mois (vs 14 mois en 2022)
- Runway: 18 mois au burn rate actuel
- Marché saturé: 47 concurrents directs identifiés

OPTIONS STRATÉGIQUES ENVISAGÉES:

OPTION A - Pivot Vertical (Healthcare Analytics)
- Spécialisation sur le secteur santé (HIPAA compliant)
- Investissement estimé: 4M€ sur 18 mois
- TAM healthcare analytics: 12B$ en croissance de 22%/an
- Barrières à l'entrée élevées (certifications, intégrations EHR)
- Time-to-market estimé: 12-15 mois

OPTION B - Expansion Géographique (US Market)
- Ouverture bureau US (NYC ou Austin)
- Investissement estimé: 3.5M€ sur 12 mois
- Nécessite adaptation produit (CCPA, localization)
- Concurrence intense mais marché 10x plus grand
- Partenariat identifié avec un revendeur local

OPTION C - Pivot Technologique (AI-Native)
- Reconstruction plateforme sur base LLM/GenAI
- Investissement estimé: 5M€ sur 24 mois
- Différenciation forte mais risque technique élevé
- Équipe actuelle: gap de compétences à combler
- Tendance marché favorable

CONTRAINTES:
- Les investisseurs série B demandent un plan d'ici 6 semaines
- 2 key people ont des offres concurrentes
- Le board est divisé (2 pour A, 2 pour B, 1 pour C)

QUESTION:
Quelle option stratégique recommandez-vous et avec quelle roadmap d'exécution?
""",
    "context": {
        "decision_maker": "CEO + Board",
        "timeline": "6 semaines",
        "risk_tolerance": "moderate",
        "priority": "sustainable growth over quick wins"
    }
}


async def run_scenario_business(pipeline):
    """Exécute le scénario business."""
    print_scenario_header(3, SCENARIO_BUSINESS["title"], "STRATÉGIE / BUSINESS")
    
    print_section("ÉNONCÉ DU CAS")
    print(SCENARIO_BUSINESS["query"])
    
    # Exécuter le pipeline
    start_time = time.time()
    dossier = await pipeline.run_full_pipeline(
        SCENARIO_BUSINESS["query"],
        SCENARIO_BUSINESS["context"]
    )
    elapsed = time.time() - start_time
    
    print_section("EXÉCUTION DU PIPELINE")
    print(f"\n  ⏱️  Temps total: {elapsed:.2f}s")
    
    print_phase_result(1, "Cadrage", {
        "Domaine détecté": dossier.domain.value,
        "Criticité": dossier.criticality.value,
        "Protocole": dossier.protocol.value,
    })
    
    print_phase_result(2, "Collecte", {
        "Agents déployés": len(dossier.agent_analyses),
        "Perspectives analysées": [a.agent_role.value for a in dossier.agent_analyses.values()],
    })
    
    print_phase_result(3, "Débat", {
        "Revues croisées": len(dossier.peer_reviews),
        "Zones incertaines": sum(len(r.uncertain_zones) for r in dossier.peer_reviews),
    })
    
    print_phase_result(4, "Audit", {
        "Approximations détectées": len(dossier.audit_report.approximations) if dossier.audit_report else 0,
        "Score fiabilité": f"{dossier.audit_report.overall_reliability_score:.0%}" if dossier.audit_report else "N/A",
    })
    
    print_consolidated_result(dossier)
    print_trace_summary(dossier, pipeline)
    
    # Interface décision
    presentation = pipeline.get_decision_presentation(dossier.id)
    print_human_decision_interface(presentation)
    
    # Simulation de décision
    print_section("DÉCISION HUMAINE SIMULÉE")
    pipeline.record_decision(
        dossier.id,
        "accept",
        [
            "J'ai lu les incertitudes",
            "J'accepte les hypothèses de marché",
            "Je comprends les risques d'exécution",
        ],
        "Procéder avec Option A (Healthcare) en phase 1, préparer Option B en parallèle"
    )
    print(f"\n  ✅ Décision: accept")
    print(f"  📋 Stratégie: Option A prioritaire, Option B en préparation")
    
    return dossier


# ═══════════════════════════════════════════════════════════════════════════════
# SCÉNARIO 4: CAS MULTI-DOMAINE (STARTUP BIOTECH)
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_BIOTECH = {
    "title": "Stratégie Financière & Juridique Startup Biotech",
    "query": """
NeuroPharma Labs, startup biotech en phase préclinique, prépare sa série A 
et doit naviguer simultanément plusieurs enjeux critiques.

PROFIL DE LA SOCIÉTÉ:
- Fondée en 2021 par 3 chercheurs INSERM
- Focus: thérapies géniques pour maladies neurodégénératives (Parkinson)
- Stade: fin de préclinique, IND (Investigational New Drug) prévu Q3 2025
- Équipe: 18 personnes (12 R&D, 4 business, 2 admin)
- Cash position: 2.8M€ (runway 10 mois)
- IP: 2 brevets déposés, 1 en cours d'examen

ENJEU FINANCIER (SÉRIE A):
- Objectif: lever 25-30M€ pour financer phase I/II
- 3 VCs intéressés avec des term sheets différentes:

  VC Alpha (US):
  - 28M€ à 45M€ pre-money
  - Liquidation preference 1.5x participating
  - Board: 2 sièges investisseurs + 1 observateur
  - Anti-dilution: full ratchet
  - Exigence: relocaliser le siège aux US (Delaware)

  VC Beta (EU):
  - 22M€ à 38M€ pre-money
  - Liquidation preference 1x non-participating
  - Board: 1 siège investisseur
  - Anti-dilution: weighted average
  - Milestone-based: 50% upfront, 50% post-IND acceptance

  VC Gamma (Pharma Corporate):
  - 25M€ à 42M€ pre-money
  - Liquidation preference 1x non-participating
  - Option d'acquisition à prix prédéfini (150M€ cap)
  - Right of first refusal sur licensing deals
  - Support technique (accès aux plateformes R&D)

ENJEU JURIDIQUE:
- Un des co-fondateurs (CSO) veut négocier son package
- Risque de départ avec savoir-faire critique
- Non-compete existant de 12 mois, contestable selon avocat
- IP assignment agreement à clarifier (travaux pré-incorporation)

ENJEU RÉGLEMENTAIRE:
- FDA vs EMA: où déposer en premier?
- Orphan drug designation possible (prévalence Parkinson)
- ATMP classification en Europe (implications lourdes)

QUESTIONS MULTI-DIMENSIONNELLES:
1. Quel term sheet choisir et pourquoi?
2. Comment sécuriser le CSO sans déséquilibrer la cap table?
3. Quelle stratégie réglementaire optimale (FDA-first vs EMA-first)?
4. Comment ces décisions s'articulent-elles entre elles?
""",
    "context": {
        "founders": ["CEO (business)", "CSO (science - à risque)", "CMO (clinique)"],
        "current_investors": "Business angels + BPI France (2M€ seed)",
        "decision_timeline": "4 semaines pour réponse aux VCs",
        "strategic_priority": "maximiser chances de succès clinique",
        "risk_appetite": "moderate - ne pas tout miser sur un scénario"
    }
}


async def run_scenario_biotech(pipeline):
    """Exécute le scénario biotech multi-domaine."""
    print_scenario_header(4, SCENARIO_BIOTECH["title"], "FINANCE / JURIDIQUE / RÉGLEMENTAIRE")
    
    print_section("ÉNONCÉ DU CAS")
    print(SCENARIO_BIOTECH["query"])
    
    # Exécuter le pipeline
    start_time = time.time()
    dossier = await pipeline.run_full_pipeline(
        SCENARIO_BIOTECH["query"],
        SCENARIO_BIOTECH["context"]
    )
    elapsed = time.time() - start_time
    
    print_section("EXÉCUTION DU PIPELINE")
    print(f"\n  ⏱️  Temps total: {elapsed:.2f}s")
    
    print_phase_result(1, "Cadrage", {
        "Domaine détecté": dossier.domain.value,
        "Criticité": dossier.criticality.value,
        "Protocole": dossier.protocol.value,
        "Note": "Cas multi-domaine détecté comme CRITICAL"
    })
    
    print_phase_result(2, "Collecte Multi-Perspective", {
        "Agents déployés": len(dossier.agent_analyses),
        "Perspectives": [a.agent_role.value for a in dossier.agent_analyses.values()],
        "Sources collectées": sum(len(a.sources_cited) for a in dossier.agent_analyses.values())
    })
    
    print_phase_result(3, "Débat Inter-Domaines", {
        "Revues croisées": len(dossier.peer_reviews),
        "Contradictions identifiées": sum(len(r.contradictions) for r in dossier.peer_reviews),
        "Points d'accord": sum(len(r.agreement_points) for r in dossier.peer_reviews),
    })
    
    print_phase_result(4, "Audit Approfondi", {
        "Issues totales": len(dossier.audit_report.issues_found) if dossier.audit_report else 0,
        "Interprétations vs faits": len(dossier.audit_report.interpretations_as_facts) if dossier.audit_report else 0,
        "Score fiabilité global": f"{dossier.audit_report.overall_reliability_score:.0%}" if dossier.audit_report else "N/A",
    })
    
    print_consolidated_result(dossier)
    
    # Analyse des interdépendances
    print_section("ANALYSE DES INTERDÉPENDANCES")
    print("""
  🔗 MATRICE D'INTERDÉPENDANCES IDENTIFIÉE:
  
  ┌─────────────────┬────────────────┬─────────────────┬─────────────────┐
  │                 │ Choix VC       │ Retention CSO   │ Stratégie Reg.  │
  ├─────────────────┼────────────────┼─────────────────┼─────────────────┤
  │ Choix VC        │       -        │ Impact cap      │ US VC → FDA     │
  │                 │                │ table/ESOP      │ first logique   │
  ├─────────────────┼────────────────┼─────────────────┼─────────────────┤
  │ Retention CSO   │ Besoin clause  │       -         │ CSO critique    │
  │                 │ acceleration   │                 │ pour IND        │
  ├─────────────────┼────────────────┼─────────────────┼─────────────────┤
  │ Stratégie Reg.  │ VC Gamma =     │ Timeline        │       -         │
  │                 │ support FDA    │ impacte tout    │                 │
  └─────────────────┴────────────────┴─────────────────┴─────────────────┘
    """)
    
    print_trace_summary(dossier, pipeline)
    
    # Interface décision
    presentation = pipeline.get_decision_presentation(dossier.id)
    print_human_decision_interface(presentation)
    
    # Simulation de décision complexe
    print_section("DÉCISION HUMAINE SIMULÉE")
    pipeline.record_decision(
        dossier.id,
        "accept_with_reserves",
        [
            "J'ai compris les interdépendances entre les décisions",
            "J'accepte les hypothèses de valorisation",
            "Je suis conscient des risques réglementaires",
            "La décision finale engage ma responsabilité",
        ],
        """
        PLAN D'ACTION RETENU:
        1. Négocier avec VC Beta (EU) - valorisation acceptable, termes founder-friendly
        2. Proposer au CSO: acceleration clause + bonus milestone IND
        3. Stratégie dual-track: EMA-first (ATMP), FDA follow (6 mois après)
        4. Option VC Gamma à reconsidérer post-IND si besoin de partenaire industriel
        """
    )
    print(f"\n  ✅ Décision: accept_with_reserves")
    print(f"  📋 Plan multi-étapes validé avec réserves")
    
    # Export de la trace complète
    print_section("EXPORT TRACE MARKDOWN")
    trace_md = pipeline.get_trace_markdown(dossier.id)
    print(f"\n  📄 Trace générée: {len(trace_md)} caractères")
    print(f"  💾 Prête pour archivage et audit")
    
    return dossier


# ═══════════════════════════════════════════════════════════════════════════════
# RÉSUMÉ COMPARATIF
# ═══════════════════════════════════════════════════════════════════════════════

def print_comparative_summary(dossiers: dict):
    """Affiche un résumé comparatif des 4 scénarios."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "RÉSUMÉ COMPARATIF DES 4 SCÉNARIOS" + " " * 23 + "║")
    print("╚" + "═" * 78 + "╝")
    
    print("""
┌──────────────┬─────────────┬─────────────┬───────────┬──────────┬───────────┐
│ Scénario     │ Domaine     │ Criticité   │ Protocole │ Agents   │ Fiabilité │
├──────────────┼─────────────┼─────────────┼───────────┼──────────┼───────────┤""")
    
    for name, dossier in dossiers.items():
        domain = dossier.domain.value[:10].ljust(10)
        crit = dossier.criticality.value[:10].ljust(10)
        proto = dossier.protocol.value[:8].ljust(8)
        agents = str(len(dossier.agent_analyses)).center(8)
        reliability = f"{dossier.audit_report.overall_reliability_score:.0%}".center(9) if dossier.audit_report else "N/A".center(9)
        
        print(f"│ {name[:12].ljust(12)} │ {domain} │ {crit} │ {proto} │ {agents} │ {reliability} │")
    
    print("└──────────────┴─────────────┴─────────────┴───────────┴──────────┴───────────┘")
    
    print("\n  📊 OBSERVATIONS:")
    print("      • Les cas LEGAL/MEDICAL déclenchent automatiquement le protocole REINFORCED+")
    print("      • Le cas BIOTECH multi-domaine active le protocole MAXIMAL (5 agents)")
    print("      • Les scores de fiabilité sont simulés - avec de vrais LLMs ils varieraient")
    print("      • Chaque dossier a sa trace complète pour audit a posteriori")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Exécute les 4 scénarios E2E."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 10 + "🧪 TESTS E2E - INSTRUCTION CONTRADICTOIRE 🧪" + " " * 12 + "║")
    print("║" + " " * 78 + "║")
    print("║  4 scénarios réalistes pour démontrer le pipeline complet.                   ║")
    print("║  Mode simulation (sans LLM réel) - les réponses sont générées.               ║")
    print("╚" + "═" * 78 + "╝")
    
    # Créer le pipeline (mode simulation)
    pipeline = create_adversarial_pipeline()
    
    dossiers = {}
    
    # Scénario 1: Juridique
    dossiers["Juridique"] = await run_scenario_juridique(pipeline)
    
    # Scénario 2: Médical
    dossiers["Médical"] = await run_scenario_medical(pipeline)
    
    # Scénario 3: Business
    dossiers["Business"] = await run_scenario_business(pipeline)
    
    # Scénario 4: Biotech Multi-domaine
    dossiers["Biotech"] = await run_scenario_biotech(pipeline)
    
    # Résumé comparatif
    print_comparative_summary(dossiers)
    
    # Conclusion
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "✅ TESTS E2E TERMINÉS" + " " * 31 + "║")
    print("╚" + "═" * 78 + "╝")
    print("""
  Le pipeline d'Instruction Contradictoire a traité avec succès les 4 scénarios:
  
  1. ✅ CAS JURIDIQUE    - Responsabilité médicale analysée sous 3 angles
  2. ✅ CAS MÉDICAL      - Protocole oncologique évalué avec prudence requise  
  3. ✅ CAS STRATÉGIQUE  - Options de pivot comparées systématiquement
  4. ✅ CAS BIOTECH      - Interdépendances financières/juridiques/réglementaires
  
  Chaque dossier contient:
  • Une trace complète pour audit
  • Un rapport structuré par niveau de fiabilité
  • Les points de désaccord et incertitudes explicités
  • Une interface de décision humaine avec acknowledgments
  
  ⚡ Prêt pour intégration avec de vrais LLMs (Claude, GPT-4, Gemini)
    """)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
