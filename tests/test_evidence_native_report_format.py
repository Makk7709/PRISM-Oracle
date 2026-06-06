"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            TESTS — Evidence Native Report Format Compliance                  ║
║                                                                              ║
║  Vérifie que les rapports Evidence-native respectent le format défini.       ║
║                                                                              ║
║  Critères testés:                                                            ║
║  1. Sections obligatoires présentes                                          ║
║  2. Tables "Risques" et "Décisions" non vides                                ║
║  3. Alternatives écartées documentées                                        ║
║  4. Bloc "Decision Governance" présent                                       ║
║  5. Badges UNVERIFIED appliqués                                              ║
║  6. Règle FAIL_CLOSED respectée                                              ║
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
def minimal_report():
    """Rapport Evidence-native minimal mais valide."""
    report = EvidenceNativeReport(
        title="Test Report — Evidence-Native Minimal",
        governance=DecisionGovernance(
            criticality=Criticality.MEDIUM,
            validation_mode=ValidationMode.SINGLE,
            status=GovernanceStatus.APPROVED,
        ),
    )
    
    # Executive summary
    report.executive_summary_conclusions = [
        "Conclusion 1: Système sécurisé",
        "Conclusion 2: Conformité partielle",
        "Conclusion 3: Plan d'action requis",
    ]
    report.executive_summary_recommendations = [
        ("Implémenter MFA", "R-001", "", ConfidenceBadge.VERIFIED),
        ("Audit trimestriel", "R-002", "", ConfidenceBadge.PARTIAL),
        ("Formation équipes", "R-003", "", ConfidenceBadge.UNVERIFIED),
    ]
    
    # Context
    report.client_context = ClientContext(
        name="Test Client",
        sector="Industrie",
        sites=["Site A", "Site B"],
        headcount="100",
        compliance=["ISO27001", "NIS2"],
    )
    
    report.scope = Scope(
        included=["Infrastructure réseau", "Serveurs"],
        excluded=["Applications métier"],
    )
    
    # Hypotheses
    report.hypotheses = [
        Hypothesis(id="H-001", statement="Informations client exactes", impact_if_false="Recommandations inadaptées", verifiable="PARTIAL"),
        Hypothesis(id="H-002", statement="Périmètre stable", impact_if_false="Budget à réévaluer", verifiable="NO"),
        Hypothesis(id="H-003", statement="Ressources disponibles", impact_if_false="Retards", verifiable="NO"),
    ]
    
    # Risks
    report.risks = [
        Risk(id="R-001", description="Accès non autorisé", impact=ImpactLevel.HIGH, probability=Probability.POSSIBLE, existing_controls="Firewall", proposed_controls="MFA"),
        Risk(id="R-002", description="Perte de données", impact=ImpactLevel.CRITICAL, probability=Probability.UNLIKELY, existing_controls="Backup quotidien", proposed_controls="Backup immuable"),
        Risk(id="R-003", description="Indisponibilité", impact=ImpactLevel.MEDIUM, probability=Probability.LIKELY, existing_controls="Monitoring basique", proposed_controls="HA cluster"),
    ]
    
    # Decisions
    report.decisions = [
        Decision(
            id="D-001",
            description="Implémenter authentification MFA",
            justification="Réduction risque accès non autorisé",
            risks_covered=["R-001"],
            tradeoffs="Complexité UX vs sécurité",
            badge=ConfidenceBadge.VERIFIED,
            alternatives=[
                Alternative("MFA TOTP", "Standard, large support", "Nécessite smartphone", is_selected=True),
                Alternative("MFA SMS", "Simple", "Moins sécurisé (SIM swap)", rejection_reason="Vulnérable aux attaques SIM swap"),
                Alternative("Statu quo", "Aucun effort", "Risque non mitigé", rejection_reason="Risque inacceptable"),
            ],
        ),
        Decision(
            id="D-002",
            description="Backup immuable WORM",
            justification="Protection contre ransomware",
            risks_covered=["R-002"],
            tradeoffs="Coût stockage vs protection",
            badge=ConfidenceBadge.PARTIAL,
            alternatives=[
                Alternative("WORM cloud", "Immuable, scalable", "Coût mensuel", is_selected=True),
                Alternative("WORM local", "Pas de dépendance cloud", "Capacité limitée", rejection_reason="Scalabilité insuffisante"),
            ],
        ),
    ]
    
    # Plan 30/60/90
    report.phase_1_actions = [
        Action("Audit des accès", "RSSI", "-", "Rapport audit", ConfidenceBadge.VERIFIED),
        Action("POC MFA", "IT", "Audit", "POC fonctionnel", ConfidenceBadge.PARTIAL),
    ]
    report.phase_2_actions = [
        Action("Déploiement MFA", "IT", "POC", "MFA actif", ConfidenceBadge.UNVERIFIED),
    ]
    report.phase_3_actions = [
        Action("Formation", "RH/IT", "MFA actif", "100% formés", ConfidenceBadge.UNVERIFIED),
    ]
    
    # Verification
    report.verification_commands = [
        VerificationCommand("Audit KOREV", "make audit-verify", "[PASS]", ConfidenceBadge.VERIFIED),
        VerificationCommand("Tests consensus", "pytest tests/test_prism*.py", "PASS", ConfidenceBadge.VERIFIED),
    ]
    
    # Limits
    report.limits = [
        Limit("Analyse basée sur données fournies", "Peut être incomplet", "Revue périodique"),
    ]
    
    return report


@pytest.fixture
def high_criticality_report():
    """Rapport avec criticité HIGH pour tester FAIL_CLOSED."""
    report = EvidenceNativeReport(
        title="Test Report — HIGH Criticality",
        governance=DecisionGovernance(
            criticality=Criticality.HIGH,
            validation_mode=ValidationMode.CONSENSUS,
            status=GovernanceStatus.PENDING,
            missing_info=["Preuve d'audit persistant"],
        ),
    )
    
    # Ajouter les sections minimales
    report.executive_summary_conclusions = ["Test conclusion"]
    report.hypotheses = [Hypothesis(id="H-001", statement="Test", impact_if_false="Test", verifiable="NO")]
    report.risks = [Risk(id="R-001", description="Test", impact=ImpactLevel.HIGH, probability=Probability.LIKELY)]
    report.decisions = [
        Decision(id="D-001", description="Test", justification="Test", badge=ConfidenceBadge.UNVERIFIED)
    ]
    
    # Points FAIL_CLOSED
    report.fail_closed_points = [
        FailClosedPoint("FC-001", "Audit persistant", "Non démontré", "Preuve de persistance"),
    ]
    
    # Points non vérifiés
    report.unverified_points = [
        UnverifiedPoint("Audit persistant", "Code non trouvé", ImpactLevel.HIGH, "Implémenter ou prouver"),
    ]
    
    return report


@pytest.fixture
def validator():
    """Instance du validateur."""
    return ReportValidator()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — STRUCTURE OBLIGATOIRE
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequiredSections:
    """Tests pour les sections obligatoires."""
    
    def test_decision_governance_present(self, minimal_report, validator):
        """Le bloc Decision Governance doit être présent."""
        content = minimal_report.generate()
        assert "## Decision Governance" in content
        assert "Criticité" in content
        assert "Quorum" in content
    
    def test_executive_summary_present(self, minimal_report, validator):
        """Le résumé exécutif doit être présent."""
        content = minimal_report.generate()
        assert "## A. Executive Summary" in content
        assert "Conclusions principales" in content
        assert "Recommandations prioritaires" in content
    
    def test_context_scope_present(self, minimal_report, validator):
        """La section Contexte & Périmètre doit être présente."""
        content = minimal_report.generate()
        assert "## B. Contexte & Périmètre" in content
        assert "#### IN" in content
        assert "#### OUT" in content
    
    def test_hypotheses_present(self, minimal_report, validator):
        """La section Hypothèses doit être présente."""
        content = minimal_report.generate()
        assert "## C. Hypothèses" in content
        assert "| H-001" in content
    
    def test_risks_present(self, minimal_report, validator):
        """Le registre des risques doit être présent et non vide."""
        content = minimal_report.generate()
        assert "## D. Registre des Risques" in content
        assert "| R-001" in content
        assert "| R-002" in content
    
    def test_decisions_present(self, minimal_report, validator):
        """Les décisions d'architecture doivent être présentes."""
        content = minimal_report.generate()
        assert "## E. Décisions d'Architecture" in content
        assert "| D-001" in content
    
    def test_alternatives_present(self, minimal_report, validator):
        """Les alternatives écartées doivent être présentes."""
        content = minimal_report.generate()
        assert "### Alternatives écartées" in content
        assert "| Alternative |" in content
    
    def test_architecture_present(self, minimal_report, validator):
        """La section Architecture Cible doit être présente."""
        content = minimal_report.generate()
        assert "## F. Architecture Cible" in content
    
    def test_implementation_plan_present(self, minimal_report, validator):
        """Le plan de mise en œuvre doit être présent."""
        content = minimal_report.generate()
        assert "## G. Plan de Mise en Œuvre" in content
        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "Phase 3" in content
    
    def test_verification_present(self, minimal_report, validator):
        """La section Preuves & Vérification doit être présente."""
        content = minimal_report.generate()
        assert "## H. Preuves & Vérification" in content
    
    def test_limits_present(self, minimal_report, validator):
        """La section Limites & FAIL_CLOSED doit être présente."""
        content = minimal_report.generate()
        assert "## I. Limites & FAIL_CLOSED" in content
    
    def test_annexes_present(self, minimal_report, validator):
        """Les annexes doivent être présentes."""
        content = minimal_report.generate()
        assert "## J. Annexes" in content
        assert "### Glossaire" in content


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — TABLES NON VIDES
# ═══════════════════════════════════════════════════════════════════════════════

class TestNonEmptyTables:
    """Tests pour les tables non vides."""
    
    def test_risks_table_not_empty(self, minimal_report):
        """La table des risques ne doit pas être vide."""
        content = minimal_report.generate()
        # Vérifier qu'il y a au moins un risque avec ID R-XXX
        import re
        risk_ids = re.findall(r"\| R-\d{3}", content)
        assert len(risk_ids) >= 1, "Registre des risques vide"
    
    def test_decisions_table_not_empty(self, minimal_report):
        """La table des décisions ne doit pas être vide."""
        content = minimal_report.generate()
        import re
        decision_ids = re.findall(r"\| D-\d{3}", content)
        assert len(decision_ids) >= 1, "Table des décisions vide"
    
    def test_hypotheses_table_not_empty(self, minimal_report):
        """La table des hypothèses ne doit pas être vide."""
        content = minimal_report.generate()
        import re
        hypothesis_ids = re.findall(r"\| H-\d{3}", content)
        assert len(hypothesis_ids) >= 1, "Table des hypothèses vide"
    
    def test_alternatives_exist(self, minimal_report):
        """Au moins une décision doit avoir des alternatives documentées."""
        content = minimal_report.generate()
        import re
        alternatives_tables = re.findall(r"\| Alternative \| Avantages", content)
        assert len(alternatives_tables) >= 1, "Aucune alternative documentée"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — BADGES DE CONFIANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfidenceBadges:
    """Tests pour les badges de confiance."""
    
    def test_badges_present(self, minimal_report):
        """Les badges VERIFIED/PARTIAL/UNVERIFIED doivent être présents."""
        content = minimal_report.generate()
        assert "`VERIFIED`" in content or "VERIFIED" in content
        assert "`PARTIAL`" in content or "PARTIAL" in content
        assert "`UNVERIFIED`" in content or "UNVERIFIED" in content
    
    def test_badge_definition_in_annexes(self, minimal_report):
        """Les badges doivent être définis dans les annexes."""
        content = minimal_report.generate()
        assert "## Badges de confiance" in content
        assert "Preuves code/tests/logs reproductibles" in content
    
    def test_recommendations_have_badges(self, minimal_report):
        """Les recommandations doivent avoir des badges."""
        content = minimal_report.generate()
        # Vérifier que la table des recommandations contient des badges
        import re
        badge_pattern = r"\| P\d \|[^|]+\|[^|]+\| `(VERIFIED|PARTIAL|UNVERIFIED)`"
        badges = re.findall(badge_pattern, content)
        assert len(badges) >= 1, "Recommandations sans badges"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailClosed:
    """Tests pour la règle FAIL_CLOSED."""
    
    def test_fail_closed_rule_documented(self, minimal_report):
        """La règle FAIL_CLOSED doit être documentée."""
        content = minimal_report.generate()
        assert "FAIL_CLOSED" in content
        assert "Règle FAIL_CLOSED" in content
    
    def test_high_criticality_has_fail_closed_section(self, high_criticality_report):
        """Un rapport HIGH doit avoir une section FAIL_CLOSED si points UNVERIFIED."""
        content = high_criticality_report.generate()
        assert "### Points FAIL_CLOSED" in content
    
    def test_high_criticality_lists_missing_info(self, high_criticality_report):
        """Un rapport HIGH doit lister les informations manquantes."""
        content = high_criticality_report.generate()
        assert "Information manquante" in content or "Informations manquantes" in content
    
    def test_unverified_points_documented(self, high_criticality_report):
        """Les points UNVERIFIED doivent être explicitement documentés."""
        content = high_criticality_report.generate()
        assert "Audit persistant" in content
        assert "Non démontré" in content or "non trouvé" in content.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidator:
    """Tests pour le validateur de rapport."""
    
    def test_valid_report_passes(self, minimal_report, validator):
        """Un rapport valide doit passer la validation."""
        content = minimal_report.generate()
        result = validator.validate(content)
        assert result.score >= 8, f"Score insuffisant: {result.score}/10"
    
    def test_empty_report_fails(self, validator):
        """Un rapport vide doit échouer."""
        result = validator.validate("")
        assert result.is_valid is False
        assert result.score < 5
    
    def test_missing_governance_fails(self, validator):
        """Un rapport sans Decision Governance doit perdre des points."""
        content = "# Rapport\n\nContenu sans gouvernance"
        result = validator.validate(content)
        assert "Decision Governance" in str(result.issues)
    
    def test_score_calculation(self, minimal_report, validator):
        """Le score doit être calculé correctement."""
        content = minimal_report.generate()
        result = validator.validate(content)
        assert result.max_score == 10
        assert 0 <= result.score <= result.max_score


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — TRANSFORMER
# ═══════════════════════════════════════════════════════════════════════════════

class TestTransformer:
    """Tests pour le transformateur de rapport."""
    
    def test_transform_generic_report(self):
        """Le transformateur doit convertir un rapport générique."""
        generic_content = """# Architecture SI Client

## Recommandations

- Implémenter un firewall nouvelle génération
- Mettre en place un SOC externalisé
- Déployer une solution de backup immuable

## Conclusion

Le système nécessite des améliorations.
"""
        transformer = GenericReportTransformer()
        report = transformer.transform(
            generic_content,
            client_context={
                "name": "Test Client",
                "sector": "Industrie",
                "sites": ["Paris"],
                "scope_in": ["Réseau"],
                "scope_out": ["Apps"],
            },
        )
        
        content = report.generate()
        
        # Vérifier que les recommandations ont été extraites
        assert len(report.decisions) >= 1
        
        # Vérifier que les sections obligatoires sont présentes
        assert "## Decision Governance" in content
        assert "## D. Registre des Risques" in content
    
    def test_transform_adds_hypotheses(self):
        """Le transformateur doit ajouter des hypothèses par défaut."""
        transformer = GenericReportTransformer()
        report = transformer.transform(
            "# Test\n\nContenu minimal",
            client_context={"name": "Test"},
        )
        
        assert len(report.hypotheses) >= 3
    
    def test_transform_adds_verification_commands(self):
        """Le transformateur doit ajouter les commandes de vérification standard."""
        transformer = GenericReportTransformer()
        report = transformer.transform(
            "# Test\n\nContenu minimal",
            client_context={"name": "Test"},
        )
        
        assert len(report.verification_commands) >= 1
        commands = [v.command for v in report.verification_commands]
        assert "make audit-verify" in commands
    
    def test_transform_respects_nis2_mode(self):
        """Le mode NIS2 doit augmenter la criticité."""
        transformer = GenericReportTransformer()
        report = transformer.transform(
            "# Test\n\nContenu minimal",
            client_context={"name": "Test"},
            preferences={"nis2_mode": True},
        )
        
        assert report.governance.criticality == Criticality.HIGH
        assert report.governance.validation_mode == ValidationMode.CONSENSUS


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — KOREV-NESS SCORE
# ═══════════════════════════════════════════════════════════════════════════════

class TestKorevnessScore:
    """Tests pour le score Korev-ness."""
    
    def test_full_report_scores_high(self, minimal_report, validator):
        """Un rapport complet doit avoir un score >= 8."""
        content = minimal_report.generate()
        result = validator.validate(content)
        assert result.score >= 8, f"Score {result.score}/10 insuffisant pour rapport complet"
    
    def test_score_reflects_missing_elements(self, validator):
        """Le score doit refléter les éléments manquants."""
        # Rapport avec seulement gouvernance et risques
        partial_content = """# Rapport Partiel

## Decision Governance

| Attribut | Valeur |
|----------|--------|
| **Criticité** | `MEDIUM` |
| **Quorum** | 2/3 |

## D. Registre des Risques

| ID | Risque |
|----|--------|
| R-001 | Test |
"""
        result = validator.validate(partial_content)
        assert result.score < 8, "Score trop élevé pour rapport incomplet"
        assert len(result.issues) > 0 or len(result.warnings) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS — RÈGLES UNVERIFIED
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnverifiedRules:
    """Tests pour les règles UNVERIFIED."""
    
    def test_known_unverified_items_marked(self):
        """Les éléments connus comme UNVERIFIED doivent être marqués."""
        transformer = GenericReportTransformer()
        report = transformer.transform(
            "# Test\n\nContenu minimal",
            client_context={"name": "Test"},
        )
        
        # Vérifier que les points UNVERIFIED connus sont présents
        unverified_descriptions = [u.point for u in report.unverified_points]
        
        # Ces éléments sont référencés dans l'audit comme UNVERIFIED
        expected_unverified = [
            "Audit persistant long terme",
            "Suivi coûts/tokens",
            "Redaction PII automatique",
        ]
        
        for expected in expected_unverified:
            assert any(expected in desc for desc in unverified_descriptions), \
                f"Point UNVERIFIED manquant: {expected}"
    
    def test_unverified_triggers_fail_closed_in_high(self):
        """En criticité HIGH, UNVERIFIED doit déclencher FAIL_CLOSED."""
        transformer = GenericReportTransformer()
        report = transformer.transform(
            "# Test\n\nContenu minimal",
            client_context={"name": "Test"},
            preferences={"nis2_mode": True},  # HIGH criticality
        )
        
        # Vérifier qu'il y a des points FAIL_CLOSED
        assert len(report.fail_closed_points) > 0, "Pas de points FAIL_CLOSED en criticité HIGH"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
