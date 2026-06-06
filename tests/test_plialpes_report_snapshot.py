"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            TESTS — Plialpes Report Snapshot                                  ║
║                                                                              ║
║  Test de non-régression pour le rapport Plialpes Evidence-native.            ║
║                                                                              ║
║  Vérifie que:                                                                ║
║  1. Le rapport généré contient les sections obligatoires                     ║
║  2. Les points UNVERIFIED sont explicitement marqués (pas inventés)          ║
║  3. La structure respecte le template Evidence-native                        ║
║  4. Le score Korev-ness est >= 8/10                                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.reporting.evidence_native import (
    EvidenceNativeReport,
    ReportValidator,
    GenericReportTransformer,
    DecisionGovernance,
    ClientContext,
    Scope,
    Hypothesis,
    Risk,
    Decision,
    Alternative,
    Action,
    VerificationCommand,
    ArchitectureComponent,
    FailoverScenario,
    Limit,
    FailClosedPoint,
    UnverifiedPoint,
    Criticality,
    ValidationMode,
    GovernanceStatus,
    ConfidenceBadge,
    ImpactLevel,
    Probability,
)


# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def plialpes_report():
    """
    Rapport Plialpes Architecture SI — Version Evidence-native.
    
    Ce rapport transforme le livrable générique "Architecture Cible SI ETI multi-sites"
    en version Evidence-native avec:
    - Traçabilité risques → décisions
    - Alternatives explicites
    - Points UNVERIFIED marqués
    - Decision Governance
    """
    report = EvidenceNativeReport(
        title="Architecture Cible SI ETI Multi-Sites — Plialpes",
        version="1.0.0-evidence",
        governance=DecisionGovernance(
            criticality=Criticality.HIGH,
            validation_mode=ValidationMode.CONSENSUS,
            status=GovernanceStatus.APPROVED,
            quorum="2/3 votes effectifs",
            arbiters=["GPT-4", "Claude-3", "Gemini-Pro"],
            missing_info=[],
        ),
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    
    report.executive_summary_conclusions = [
        "L'infrastructure actuelle présente des risques de disponibilité significatifs (SPOF multiples)",
        "La conformité NIS2 impose des actions prioritaires sur la segmentation réseau et le PRA",
        "Un investissement sur 90 jours permettra d'atteindre un niveau de sécurité acceptable",
    ]
    
    report.executive_summary_recommendations = [
        ("Segmentation VLAN IT/OT avec firewall interzone", "R-001", "", ConfidenceBadge.VERIFIED),
        ("Lien FTTO redondant (actif/passif)", "R-002", "", ConfidenceBadge.VERIFIED),
        ("VPN IPsec site-à-site avec failover", "R-003", "", ConfidenceBadge.PARTIAL),
        ("SOC externalisé 24/7 avec SIEM", "R-004", "", ConfidenceBadge.UNVERIFIED),
        ("Backup WORM immuable hors site", "R-005", "", ConfidenceBadge.PARTIAL),
    ]
    
    # CONTEXTE & PÉRIMÈTRE
    # ─────────────────────────────────────────────────────────────────────────
    
    report.client_context = ClientContext(
        name="Plialpes Industries",
        sector="Industrie manufacturière (plasturgie)",
        sites=["Siège Annecy (IT)", "Usine Rumilly (OT)", "Entrepôt Aix-les-Bains"],
        headcount="250 employés",
        compliance=["NIS2", "ISO27001 (en cours)", "RGPD"],
    )
    
    report.scope = Scope(
        included=[
            "Infrastructure réseau (LAN/WAN/DMZ)",
            "Sécurité périmétrique (firewall, VPN, IDS)",
            "Plan de reprise d'activité (PRA)",
            "Supervision et monitoring",
            "Conformité NIS2 (périmètre technique)",
        ],
        excluded=[
            "Applications métier (ERP, MES)",
            "Développement logiciel",
            "Formation utilisateurs (hors technique)",
            "Conformité RGPD (périmètre organisationnel)",
        ],
    )
    
    # HYPOTHÈSES
    # ─────────────────────────────────────────────────────────────────────────
    
    report.hypotheses = [
        Hypothesis(
            id="H-001",
            statement="Les informations d'inventaire fournies sont complètes et à jour",
            impact_if_false="Recommandations potentiellement inadaptées ou sous-dimensionnées",
            verifiable="PARTIAL",
        ),
        Hypothesis(
            id="H-002",
            statement="Le budget prévu (300-400k€) est confirmé et disponible",
            impact_if_false="Priorisation à revoir, phases à décaler",
            verifiable="NO",
        ),
        Hypothesis(
            id="H-003",
            statement="Les équipes IT (3 ETP) seront disponibles selon le planning",
            impact_if_false="Retards sur les phases de déploiement",
            verifiable="NO",
        ),
        Hypothesis(
            id="H-004",
            statement="Aucune contrainte de production bloquante pour les maintenances",
            impact_if_false="Fenêtres de déploiement réduites, délais allongés",
            verifiable="PARTIAL",
        ),
    ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # REGISTRE DES RISQUES
    # ─────────────────────────────────────────────────────────────────────────
    
    report.risks = [
        Risk(
            id="R-001",
            description="Propagation d'attaque IT vers OT (ransomware)",
            impact=ImpactLevel.CRITICAL,
            probability=Probability.LIKELY,
            existing_controls="Aucune segmentation IT/OT",
            proposed_controls="VLAN + firewall interzone + monitoring",
        ),
        Risk(
            id="R-002",
            description="Indisponibilité WAN (lien unique SDSL)",
            impact=ImpactLevel.HIGH,
            probability=Probability.POSSIBLE,
            existing_controls="Lien SDSL unique 20 Mbps",
            proposed_controls="FTTO + backup 4G failover",
        ),
        Risk(
            id="R-003",
            description="Compromission VPN (accès distants non sécurisés)",
            impact=ImpactLevel.HIGH,
            probability=Probability.LIKELY,
            existing_controls="VPN PPTP obsolète",
            proposed_controls="VPN IPsec + MFA + ACL par rôle",
        ),
        Risk(
            id="R-004",
            description="Détection tardive d'intrusion (pas de SOC)",
            impact=ImpactLevel.HIGH,
            probability=Probability.LIKELY,
            existing_controls="Antivirus postes + logs non centralisés",
            proposed_controls="SIEM + SOC externalisé 24/7",
        ),
        Risk(
            id="R-005",
            description="Perte de données par ransomware (backup atteignable)",
            impact=ImpactLevel.CRITICAL,
            probability=Probability.POSSIBLE,
            existing_controls="Backup NAS local sur le même réseau",
            proposed_controls="Backup WORM immuable + réplication hors site",
        ),
        Risk(
            id="R-006",
            description="Non-conformité NIS2 (sanctions)",
            impact=ImpactLevel.HIGH,
            probability=Probability.CERTAIN,
            existing_controls="Aucune gouvernance cybersécurité formalisée",
            proposed_controls="PSSI + PRA + audit annuel + notification incidents",
        ),
    ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # DÉCISIONS D'ARCHITECTURE
    # ─────────────────────────────────────────────────────────────────────────
    
    report.decisions = [
        Decision(
            id="D-001",
            description="Segmentation VLAN avec firewall Fortinet interzone",
            justification="Isolation IT/OT obligatoire pour NIS2, réduction surface d'attaque",
            risks_covered=["R-001", "R-006"],
            tradeoffs="Complexité de gestion vs sécurité accrue",
            badge=ConfidenceBadge.VERIFIED,
            alternatives=[
                Alternative(
                    name="Segmentation VLAN + Fortinet",
                    advantages="Standard industrie, support local, intégration SD-WAN",
                    disadvantages="Coût licence annuel (~15k€/an)",
                    is_selected=True,
                ),
                Alternative(
                    name="Segmentation VLAN + pfSense",
                    advantages="Open source, coût réduit",
                    disadvantages="Support limité, pas de certification industrielle",
                    rejection_reason="Manque de support pour environnement OT critique",
                ),
                Alternative(
                    name="Flat network (statu quo)",
                    advantages="Simplicité, pas d'effort",
                    disadvantages="Non conforme NIS2, risque propagation maximal",
                    rejection_reason="Non-conformité réglementaire, risque inacceptable",
                ),
            ],
        ),
        Decision(
            id="D-002",
            description="Lien FTTO 100 Mbps + backup 4G failover",
            justification="RTO < 4h exige redondance WAN, SDSL insuffisant",
            risks_covered=["R-002"],
            tradeoffs="Coût mensuel additionnel (~500€/mois) vs disponibilité garantie",
            badge=ConfidenceBadge.VERIFIED,
            alternatives=[
                Alternative(
                    name="FTTO + 4G failover",
                    advantages="Basculement automatique, SLA 99.9%",
                    disadvantages="Coût mensuel (~500€/mois)",
                    is_selected=True,
                ),
                Alternative(
                    name="Double lien FTTO",
                    advantages="Débit symétrique, haute disponibilité",
                    disadvantages="Coût élevé (~1200€/mois), délai installation",
                    rejection_reason="Budget dépassé, overkill pour le besoin actuel",
                ),
                Alternative(
                    name="SDSL unique (statu quo)",
                    advantages="Pas de changement",
                    disadvantages="SPOF, débit insuffisant, pas de SLA",
                    rejection_reason="RTO non atteignable, risque business inacceptable",
                ),
            ],
        ),
        Decision(
            id="D-003",
            description="VPN IPsec site-à-site avec MFA obligatoire",
            justification="VPN PPTP obsolète et vulnérable, MFA exigé par NIS2",
            risks_covered=["R-003", "R-006"],
            tradeoffs="Complexité utilisateur vs sécurité accès distants",
            badge=ConfidenceBadge.PARTIAL,
            alternatives=[
                Alternative(
                    name="VPN IPsec + MFA TOTP",
                    advantages="Standard, compatible tous OS, MFA intégré",
                    disadvantages="Configuration initiale complexe",
                    is_selected=True,
                ),
                Alternative(
                    name="SD-WAN avec VPN intégré",
                    advantages="Gestion centralisée, QoS intégrée",
                    disadvantages="Coût licence élevé, vendor lock-in",
                    rejection_reason="Budget Phase 1 insuffisant, à réévaluer Phase 3",
                ),
                Alternative(
                    name="VPN SSL (OpenVPN)",
                    advantages="Simple, multiplateforme",
                    disadvantages="Performance moindre, pas de MFA natif",
                    rejection_reason="MFA non intégré nativement, complexité addon",
                ),
            ],
        ),
        Decision(
            id="D-004",
            description="SOC externalisé 24/7 avec SIEM managé",
            justification="Équipe interne insuffisante pour monitoring 24/7, NIS2 exige détection",
            risks_covered=["R-004", "R-006"],
            tradeoffs="Coût externalisé (~3k€/mois) vs embauche analyste SOC",
            badge=ConfidenceBadge.UNVERIFIED,
            alternatives=[
                Alternative(
                    name="SOC externalisé (MSSP)",
                    advantages="24/7, expertise mutualisée, mise en place rapide",
                    disadvantages="Coût mensuel (~3k€/mois), dépendance fournisseur",
                    is_selected=True,
                ),
                Alternative(
                    name="SOC interne",
                    advantages="Contrôle total, connaissance métier",
                    disadvantages="Coût embauche (~80k€/an), temps recrutement",
                    rejection_reason="Délai incompatible NIS2, budget dépassé",
                ),
                Alternative(
                    name="Monitoring basique (Zabbix seul)",
                    advantages="Open source, déjà en place",
                    disadvantages="Pas de corrélation sécurité, pas d'analyste",
                    rejection_reason="Non conforme NIS2, détection insuffisante",
                ),
            ],
        ),
        Decision(
            id="D-005",
            description="Backup WORM immuable avec réplication cloud",
            justification="Backup actuel atteignable par ransomware, immuabilité requise",
            risks_covered=["R-005"],
            tradeoffs="Coût stockage immuable vs protection ransomware",
            badge=ConfidenceBadge.PARTIAL,
            alternatives=[
                Alternative(
                    name="WORM cloud (Wasabi/Backblaze)",
                    advantages="Immuable, scalable, coût prévisible (~200€/mois)",
                    disadvantages="Dépendance internet pour restore",
                    is_selected=True,
                ),
                Alternative(
                    name="WORM appliance locale",
                    advantages="Restore rapide, pas de dépendance cloud",
                    disadvantages="CAPEX élevé (~30k€), capacité limitée",
                    rejection_reason="Budget initial trop élevé, scalabilité limitée",
                ),
                Alternative(
                    name="NAS local (statu quo)",
                    advantages="Existant, pas de coût additionnel",
                    disadvantages="Atteignable par ransomware, pas d'immuabilité",
                    rejection_reason="Risque critique de perte totale, inacceptable",
                ),
            ],
        ),
    ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # ARCHITECTURE CIBLE
    # ─────────────────────────────────────────────────────────────────────────
    
    report.architecture_diagram = """
┌─────────────────────────────────────────────────────────────────────────┐
│                            INTERNET                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │     FTTO + 4G Failover        │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │      FIREWALL FORTINET        │
                    │      (Next-Gen UTM)           │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
   ┌────┴────┐                 ┌────┴────┐                ┌────┴────┐
   │  DMZ    │                 │ VLAN IT │                │ VLAN OT │
   │ VLAN 10 │                 │ VLAN 20 │                │ VLAN 30 │
   └────┬────┘                 └────┬────┘                └────┬────┘
        │                           │                           │
   ┌────┴────┐                 ┌────┴────┐                ┌────┴────┐
   │ Reverse │                 │ Servers │                │ Automates│
   │ Proxy   │                 │ AD/File │                │ SCADA    │
   │ WAF     │                 │ ERP     │                │ PLC      │
   └─────────┘                 └─────────┘                └─────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │                    SITE SECONDAIRE (PRA)                     │
     │  ┌─────────┐    ┌─────────┐    ┌─────────┐                   │
     │  │ Backup  │◄───│ VPN     │◄───│ Replica │                   │
     │  │ WORM    │    │ IPsec   │    │ AD      │                   │
     │  └─────────┘    └─────────┘    └─────────┘                   │
     └──────────────────────────────────────────────────────────────┘
"""
    
    report.architecture_components = [
        ArchitectureComponent("DMZ", "Reverse Proxy / WAF", Criticality.HIGH, False, True, "Point d'entrée web"),
        ArchitectureComponent("IT", "Active Directory", Criticality.HIGH, True, True, "SPOF authentification"),
        ArchitectureComponent("IT", "Serveur fichiers", Criticality.MEDIUM, False, True, "Données utilisateurs"),
        ArchitectureComponent("IT", "ERP", Criticality.HIGH, True, True, "SPOF métier"),
        ArchitectureComponent("OT", "SCADA", Criticality.HIGH, True, False, "Contrôle production"),
        ArchitectureComponent("OT", "Automates PLC", Criticality.HIGH, False, False, "Redondance native"),
        ArchitectureComponent("WAN", "Firewall Fortinet", Criticality.HIGH, True, True, "SPOF sécurité périmétrique"),
    ]
    
    report.failover_scenarios = [
        FailoverScenario("Perte lien principal", "FTTO", "4G Failover", "< 30s", "0"),
        FailoverScenario("Panne AD primaire", "AD principal", "AD secondaire", "< 5min", "15min"),
        FailoverScenario("Sinistre site principal", "Site Annecy", "Site PRA", "< 4h", "24h"),
    ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # PLAN 30/60/90
    # ─────────────────────────────────────────────────────────────────────────
    
    report.phase_1_actions = [
        Action("Audit inventaire et cartographie réseau", "IT + Prestataire", "-", "Cartographie complète", ConfidenceBadge.VERIFIED),
        Action("Déploiement firewall Fortinet + segmentation VLAN", "IT", "Audit", "Firewall opérationnel", ConfidenceBadge.VERIFIED),
        Action("Migration VPN PPTP → IPsec + MFA", "IT", "Firewall", "VPN sécurisé actif", ConfidenceBadge.PARTIAL),
        Action("Activation lien FTTO + failover 4G", "Opérateur", "Firewall", "WAN redondant", ConfidenceBadge.VERIFIED),
    ]
    
    report.phase_2_actions = [
        Action("Déploiement SIEM + intégration SOC externalisé", "IT + MSSP", "Firewall", "SOC opérationnel", ConfidenceBadge.UNVERIFIED),
        Action("Configuration backup WORM + tests restore", "IT", "Inventaire", "Backup immuable validé", ConfidenceBadge.PARTIAL),
        Action("Rédaction PSSI + procédures incidents", "RSSI", "SOC", "PSSI v1 validée", ConfidenceBadge.UNVERIFIED),
    ]
    
    report.phase_3_actions = [
        Action("Tests PRA site secondaire", "IT", "Backup", "PRA testé et documenté", ConfidenceBadge.UNVERIFIED),
        Action("Formation équipes IT et utilisateurs clés", "RH + IT", "PSSI", "100% équipes formées", ConfidenceBadge.UNVERIFIED),
        Action("Audit conformité NIS2 externe", "Auditeur externe", "Tout", "Rapport conformité", ConfidenceBadge.UNVERIFIED),
    ]
    
    # PREUVES & VÉRIFICATION
    # ─────────────────────────────────────────────────────────────────────────
    
    report.verification_commands = [
        VerificationCommand("Audit KOREV complet", "make audit-verify", "[PASS] Audit verification complète", ConfidenceBadge.VERIFIED),
        VerificationCommand("Consensus PRISM", "python -m pytest tests/test_prism_tally_quorum.py -v", "Tous tests PASS", ConfidenceBadge.VERIFIED),
        VerificationCommand("Routeur déterministe", "python -m pytest tests/test_router_determinism.py -v", "Tous tests PASS", ConfidenceBadge.VERIFIED),
        VerificationCommand("Contrat médical", "python -m pytest tests/test_medical_agent_hardening.py -v", "Tous tests PASS", ConfidenceBadge.PARTIAL),
    ]
    
    report.unverified_points = [
        UnverifiedPoint("Audit persistant long terme", "Volume Docker configuré mais code d'écriture non trouvé", ImpactLevel.MEDIUM, "Vérifier implémentation persistence"),
        UnverifiedPoint("Suivi coûts/tokens", "Aucun code de tracking trouvé dans le repo", ImpactLevel.LOW, "Implémenter cost tracking si requis"),
        UnverifiedPoint("Redaction PII automatique", "Uniquement dans les prompts, pas de code runtime", ImpactLevel.MEDIUM, "Implémenter redaction si données sensibles"),
        UnverifiedPoint("Efficacité réelle du SOC externalisé", "Dépend du choix du MSSP", ImpactLevel.HIGH, "POC avec 2-3 MSSP avant engagement"),
    ]
    
    # LIMITES & FAIL_CLOSED
    # ─────────────────────────────────────────────────────────────────────────
    
    report.limits = [
        Limit(
            "Analyse basée sur inventaire fourni (non audité)",
            "Équipements non déclarés non couverts",
            "Audit technique complémentaire recommandé",
        ),
        Limit(
            "Budgets estimatifs (pas de devis formels)",
            "Écart possible +/- 20%",
            "Demander devis avant engagement",
        ),
        Limit(
            "Disponibilité équipes non confirmée",
            "Planning à risque",
            "Validation RH avant lancement",
        ),
    ]
    
    report.fail_closed_points = []  # Pas de FAIL_CLOSED car statut APPROVED
    
    # ─────────────────────────────────────────────────────────────────────────
    # GLOSSAIRE SPÉCIFIQUE
    # ─────────────────────────────────────────────────────────────────────────
    
    report.glossary = {
        "FTTO": "Fiber To The Office — liaison fibre dédiée entreprise",
        "VLAN": "Virtual Local Area Network — segmentation logique du réseau",
        "OT": "Operational Technology — systèmes industriels (SCADA, PLC)",
        "MSSP": "Managed Security Service Provider — SOC externalisé",
        "WORM": "Write Once Read Many — stockage immuable",
        "NIS2": "Directive européenne sur la sécurité des réseaux et systèmes d'information",
        "UTM": "Unified Threat Management — firewall multifonction",
    }
    
    return report


@pytest.fixture
def validator():
    """Instance du validateur."""
    return ReportValidator()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — STRUCTURE SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlialpesSections:
    """Tests de présence des sections obligatoires."""
    
    def test_decision_governance_present(self, plialpes_report):
        """Le bloc Decision Governance est présent et complet."""
        content = plialpes_report.generate()
        assert "## Decision Governance" in content
        assert "Criticité" in content
        assert "`HIGH`" in content
        assert "CONSENSUS" in content
        assert "2/3 votes effectifs" in content
    
    def test_all_risks_documented(self, plialpes_report):
        """Tous les risques sont documentés avec ID."""
        content = plialpes_report.generate()
        for risk in plialpes_report.risks:
            assert f"| {risk.id}" in content, f"Risque {risk.id} manquant"
    
    def test_all_decisions_documented(self, plialpes_report):
        """Toutes les décisions sont documentées avec ID."""
        content = plialpes_report.generate()
        for decision in plialpes_report.decisions:
            assert f"| {decision.id}" in content, f"Décision {decision.id} manquante"
    
    def test_all_decisions_have_alternatives(self, plialpes_report):
        """Toutes les décisions ont des alternatives documentées."""
        content = plialpes_report.generate()
        for decision in plialpes_report.decisions:
            assert len(decision.alternatives) >= 2, \
                f"Décision {decision.id} n'a pas assez d'alternatives"
    
    def test_architecture_diagram_present(self, plialpes_report):
        """Le schéma d'architecture est présent."""
        content = plialpes_report.generate()
        assert "INTERNET" in content
        assert "FIREWALL" in content
        assert "VLAN" in content


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — UNVERIFIED POINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnverifiedHandling:
    """Tests pour la gestion des points UNVERIFIED."""
    
    def test_known_unverified_marked(self, plialpes_report):
        """Les points connus comme UNVERIFIED sont marqués."""
        content = plialpes_report.generate()
        
        # Ces points sont UNVERIFIED selon l'audit KOREV Evidence
        assert "Audit persistant" in content
        assert "Suivi coûts/tokens" in content or "cost" in content.lower()
    
    def test_soc_marked_unverified(self, plialpes_report):
        """La décision SOC est marquée UNVERIFIED (dépend du choix MSSP)."""
        soc_decision = next(d for d in plialpes_report.decisions if "SOC" in d.description)
        assert soc_decision.badge == ConfidenceBadge.UNVERIFIED
    
    def test_phase3_mostly_unverified(self, plialpes_report):
        """La phase 3 est majoritairement UNVERIFIED (actions futures)."""
        unverified_count = sum(
            1 for a in plialpes_report.phase_3_actions 
            if a.badge == ConfidenceBadge.UNVERIFIED
        )
        assert unverified_count >= len(plialpes_report.phase_3_actions) // 2
    
    def test_no_false_verified_claims(self, plialpes_report):
        """Aucune affirmation non prouvable n'est marquée VERIFIED."""
        # Les points suivants ne peuvent pas être VERIFIED à ce stade
        unverifiable_topics = ["SOC", "PRA testé", "Formation", "Audit NIS2"]
        
        for decision in plialpes_report.decisions:
            if any(topic in decision.description for topic in unverifiable_topics):
                assert decision.badge != ConfidenceBadge.VERIFIED, \
                    f"Décision '{decision.description}' ne devrait pas être VERIFIED"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — KOREV-NESS SCORE
# ═══════════════════════════════════════════════════════════════════════════════

class TestKorevnessScore:
    """Tests pour le score Korev-ness."""
    
    def test_minimum_score_achieved(self, plialpes_report, validator):
        """Le rapport atteint le score minimum de 8/10."""
        content = plialpes_report.generate()
        result = validator.validate(content)
        assert result.score >= 8, f"Score {result.score}/10 < 8 requis"
    
    def test_no_critical_issues(self, plialpes_report, validator):
        """Le rapport n'a pas d'issues critiques."""
        content = plialpes_report.generate()
        result = validator.validate(content)
        # Issues critiques = sections obligatoires manquantes
        critical_issues = [i for i in result.issues if "ABSENT" in i]
        assert len(critical_issues) == 0, f"Issues critiques: {critical_issues}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — DIFFÉRENCIATION VS GÉNÉRIQUE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDifferentiation:
    """Tests pour la différenciation Evidence-native vs générique."""
    
    def test_risks_linked_to_decisions(self, plialpes_report):
        """Chaque décision couvre au moins un risque."""
        for decision in plialpes_report.decisions:
            assert len(decision.risks_covered) >= 1, \
                f"Décision {decision.id} ne couvre aucun risque"
    
    def test_alternatives_have_rejection_reasons(self, plialpes_report):
        """Les alternatives non retenues ont une raison de rejet."""
        for decision in plialpes_report.decisions:
            for alt in decision.alternatives:
                if not alt.is_selected:
                    assert alt.rejection_reason, \
                        f"Alternative '{alt.name}' sans raison de rejet"
    
    def test_hypotheses_documented(self, plialpes_report):
        """Les hypothèses sont documentées avec impact."""
        assert len(plialpes_report.hypotheses) >= 3
        for h in plialpes_report.hypotheses:
            assert h.impact_if_false, f"Hypothèse {h.id} sans impact documenté"
    
    def test_verification_commands_present(self, plialpes_report):
        """Des commandes de vérification sont fournies."""
        assert len(plialpes_report.verification_commands) >= 1
        commands = [v.command for v in plialpes_report.verification_commands]
        assert any("pytest" in c or "make" in c for c in commands)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — SNAPSHOT OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotOutput:
    """Tests snapshot pour le contenu généré."""
    
    def test_output_not_empty(self, plialpes_report):
        """Le rapport généré n'est pas vide."""
        content = plialpes_report.generate()
        assert len(content) > 5000, "Rapport trop court"
    
    def test_output_is_valid_markdown(self, plialpes_report):
        """Le rapport est du Markdown valide."""
        content = plialpes_report.generate()
        # Vérifier la structure Markdown basique
        assert content.startswith("#")
        assert "##" in content
        assert "|" in content  # Tables
    
    def test_client_name_in_output(self, plialpes_report):
        """Le nom du client apparaît dans le rapport."""
        content = plialpes_report.generate()
        assert "Plialpes" in content
    
    def test_correlation_id_present(self, plialpes_report):
        """Un correlation ID est présent pour la traçabilité."""
        content = plialpes_report.generate()
        assert "Correlation ID" in content
        # Vérifier le format UUID
        import re
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        assert re.search(uuid_pattern, content), "Correlation ID non valide"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — SAVE & LOAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestSaveLoad:
    """Tests pour la sauvegarde et le chargement."""
    
    def test_save_creates_file(self, plialpes_report, tmp_path):
        """La sauvegarde crée un fichier."""
        output_path = tmp_path / "test_report.md"
        plialpes_report.save(str(output_path))
        assert output_path.exists()
    
    def test_saved_content_matches(self, plialpes_report, tmp_path):
        """Le contenu sauvegardé correspond au généré (hors timestamps)."""
        import re
        
        output_path = tmp_path / "test_report.md"
        plialpes_report.save(str(output_path))
        
        saved_content = output_path.read_text(encoding="utf-8")
        generated_content = plialpes_report.generate()
        
        # Remove dynamic timestamps for comparison
        timestamp_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}"
        saved_normalized = re.sub(timestamp_pattern, "TIMESTAMP", saved_content)
        generated_normalized = re.sub(timestamp_pattern, "TIMESTAMP", generated_content)
        
        assert saved_normalized == generated_normalized
    
    def test_saved_file_validates(self, plialpes_report, validator, tmp_path):
        """Le fichier sauvegardé passe la validation."""
        output_path = tmp_path / "test_report.md"
        plialpes_report.save(str(output_path))
        
        result = validator.validate_file(str(output_path))
        assert result.score >= 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
