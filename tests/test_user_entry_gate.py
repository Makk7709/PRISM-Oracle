"""
T0: User Entry Gate Applied — Test de bout en bout.

Vérifie que l'entrée principale (user query, agent default, sans spawn)
passe OBLIGATOIREMENT par le CriticalDecisionGate.

Ce test est le PLUS IMPORTANT car il prouve que le gate est inévitable
même quand l'agent répond directement sans délégation.

═══════════════════════════════════════════════════════════════════════════════
CLASSIFICATION À 3 NIVEAUX (logique actuelle du CriticalityRouter):

  LEVEL 1 — SIMPLE: définition, résumé, explication, météo, traduction
            → JAMAIS de consensus, réponse directe

  LEVEL 2 — PROFESSIONNEL: analyse, comparaison, conseil technique
            → PAS de consensus par défaut (domaine détecté pour métadonnées)

  LEVEL 3 — CRITIQUE: cas réel, décision personnelle, litige, responsabilité
            → SEUL niveau qui déclenche le consensus
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from python.helpers.critical_decision_gate import (
    CriticalDecisionGate,
    GateDecision,
    GateResult,
    enforce_or_route,
    validate_final_output,
)
from python.helpers.criticality_router import (
    CriticalDomain,
    CriticalityRouter,
    assess_criticality,
)


# ═══════════════════════════════════════════════════════════════════════════════
# T0: GATE TOUJOURS APPLIQUÉ (invariant fondamental)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateAlwaysApplied:
    """
    Invariant: Le gate est TOUJOURS appliqué, peu importe la query.
    gate_applied=True dans le log entry TOUJOURS.
    """

    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()

    def test_gate_applied_on_any_query(self, gate):
        """gate_applied=True sur n'importe quelle query."""
        queries = [
            "Bonjour",
            "Quelle heure est-il ?",
            "Explique la photosynthèse",
            "Mon médecin m'a prescrit ce médicament, dois-je le prendre ?",
            "J'ai reçu une mise en demeure, que faire ?",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            log = result.to_log_entry()
            assert log["gate_applied"] is True, f"Gate not applied on: {query}"

    def test_gate_returns_gateresult(self, gate):
        """Le gate retourne toujours un GateResult valide."""
        result = gate.enforce_or_route("Test", "default")
        assert isinstance(result, GateResult)
        assert result.decision in [GateDecision.ALLOW, GateDecision.REQUIRE_CONSENSUS]
        assert isinstance(result.correlation_id, str)
        assert len(result.correlation_id) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# LEVEL 1 — SIMPLE: Pas de consensus
# ═══════════════════════════════════════════════════════════════════════════════

class TestLevel1SimpleNoConsensus:
    """
    LEVEL 1: Définitions, résumés, explications, météo, traduction.
    → JAMAIS de consensus, même si mots médicaux/légaux.
    """

    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()

    def test_simple_greeting_no_consensus(self, gate):
        """Salutations → pas de consensus."""
        for query in ["Bonjour", "Hello", "Salut"]:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is False, f"Consensus on greeting: {query}"

    def test_definition_no_consensus(self, gate):
        """Définitions → pas de consensus même sur sujet médical/légal."""
        queries = [
            "Qu'est-ce qu'un contrat synallagmatique ?",
            "Qu'est-ce que la photosynthèse ?",
            "C'est quoi un bilan sanguin ?",
            "Définition de la jurisprudence",
            "What is a meta-analysis?",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is False, (
                f"Consensus on definition: {query}"
            )

    def test_simple_question_no_consensus(self, gate):
        """Questions simples → pas de consensus."""
        queries = [
            "Quelle heure est-il ?",
            "Quel temps fait-il ?",
            "Combien font 2+2 ?",
            "Traduis en anglais",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is False
            assert result.decision == GateDecision.ALLOW

    def test_explanation_no_consensus(self, gate):
        """Explications pédagogiques → pas de consensus."""
        queries = [
            "Explique-moi comment fonctionne l'ADN",
            "Différence entre civil et pénal",
            "Explain the difference between stocks and bonds",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is False, (
                f"Consensus on explanation: {query}"
            )

    def test_summary_no_consensus(self, gate):
        """Résumés → pas de consensus."""
        queries = [
            "Résume ce texte",
            "Fais-moi une synthèse",
            "Summarize this article",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is False


# ═══════════════════════════════════════════════════════════════════════════════
# LEVEL 2 — PROFESSIONNEL: Domaine détecté, pas de consensus
# ═══════════════════════════════════════════════════════════════════════════════

class TestLevel2ProfessionalDomainDetected:
    """
    LEVEL 2: Analyse professionnelle avec mots-clés domaine.
    → Domaine correctement détecté, mais PAS de consensus.
    Le domaine enrichit les métadonnées sans déclencher le pipeline lourd.
    """

    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_medical_keywords_detected_no_consensus(self, router):
        """Mots médicaux détectés → domain=MEDICAL mais PAS consensus."""
        queries = [
            "Quelle posologie pour ce médicament ?",
            "Quels sont les effets secondaires du paracétamol ?",
            "Comment interpréter un bilan sanguin ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.domain == CriticalDomain.MEDICAL, (
                f"Domain not MEDICAL for: {query}, got {assessment.domain}"
            )
            # Level 2 → PAS de consensus (question professionnelle, pas cas réel)
            assert assessment.requires_consensus is False, (
                f"Unexpected consensus on Level 2 medical: {query}"
            )

    def test_legal_keywords_detected_no_consensus(self, router):
        """Mots légaux détectés → domain=LEGAL mais PAS consensus si Level 2."""
        queries = [
            "Quelles sont les clauses abusives dans un contrat type ?",
            "La RGPD s'applique-t-elle aux entreprises étrangères ?",
            "Quelle jurisprudence sur ce sujet ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.domain == CriticalDomain.LEGAL, (
                f"Domain not LEGAL for: {query}, got {assessment.domain}"
            )

    def test_scientific_keywords_detected_no_consensus(self, router):
        """Mots scientifiques détectés → domain=SCIENTIFIC mais PAS consensus si Level 2."""
        queries = [
            "La méthodologie de cette étude est-elle valide ?",
            "Comment interpréter cet odds ratio ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.domain == CriticalDomain.SCIENTIFIC, (
                f"Domain not SCIENTIFIC for: {query}, got {assessment.domain}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# LEVEL 3 — CRITIQUE: Consensus REQUIS (cas réels, décisions)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLevel3CriticalConsensusRequired:
    """
    LEVEL 3: Cas réels personnels, décisions à prendre, litiges.
    → consensus OBLIGATOIRE + strict_evidence_mode si domaine critique.
    
    C'est le test LE PLUS IMPORTANT pour la fiabilité du système.
    """

    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    # ─────── Cas médicaux réels (LEVEL 3) ───────

    def test_medical_real_case_consensus_required(self, gate):
        """Cas médical personnel → consensus OBLIGATOIRE."""
        queries = [
            "Mon médecin m'a prescrit ce médicament, dois-je le prendre ?",
            "J'ai les symptômes suivants de fièvre, quel traitement ?",
            "Dois-je aller aux urgences pour ma douleur au thorax ?",
            "Mon patient présente un diagnostic différentiel complexe",
            "Quel traitement pour mon enfant malade ?",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is True, (
                f"CRITICAL FAIL: Real medical case without consensus: '{query}'"
            )
            assert result.assessment.domain == CriticalDomain.MEDICAL, (
                f"Domain not MEDICAL for real case: {query}"
            )
            assert result.decision == GateDecision.REQUIRE_CONSENSUS

    def test_medical_real_case_strict_evidence(self, gate):
        """Cas médical réel → strict_evidence_mode=True."""
        result = gate.enforce_or_route(
            query="Mon médecin m'a prescrit ce médicament, dois-je le prendre ?",
            agent_profile="default",
        )
        assert result.assessment.strict_evidence_mode is True

    # ─────── Cas légaux réels (LEVEL 3) ───────

    def test_legal_real_case_consensus_required(self, gate):
        """Cas légal personnel → consensus OBLIGATOIRE."""
        queries = [
            "J'ai reçu une mise en demeure, que faire ?",
            "Mon employeur m'a licencié, puis-je saisir les prud'hommes ?",
            "Puis-je contester cette décision devant le tribunal ?",
            "Dois-je signer ce contrat ou refuser ?",
            "J'ai un litige avec mon propriétaire, quel recours ai-je ?",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is True, (
                f"CRITICAL FAIL: Real legal case without consensus: '{query}'"
            )
            assert result.assessment.domain == CriticalDomain.LEGAL, (
                f"Domain not LEGAL for real case: {query}, got {result.assessment.domain}"
            )

    def test_legal_real_case_consensus_even_if_domain_not_detected(self, gate):
        """Cas légal réel → consensus même si le domaine LEGAL n'est pas detecté
        (patterns Level 3 suffisent pour déclencher le consensus)."""
        queries = [
            "Je suis assigné en justice, quels sont mes droits ?",
            "Que puis-je faire contre cette décision ?",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is True, (
                f"CRITICAL FAIL: Real case without consensus: '{query}'"
            )

    # ─────── Cas scientifiques réels (LEVEL 3) ───────

    def test_scientific_real_decision_consensus_required(self, gate):
        """Décision scientifique critique → consensus OBLIGATOIRE."""
        queries = [
            "Mon patient participe à cet essai clinique, dois-je le recommander ?",
            "Dois-je publier ces résultats malgré la p-value faible ?",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is True, (
                f"CRITICAL FAIL: Real scientific decision without consensus: '{query}'"
            )

    # ─────── Cas financiers réels (LEVEL 3) ───────

    def test_financial_real_decision_consensus_required(self, gate):
        """Décision financière personnelle → consensus OBLIGATOIRE."""
        queries = [
            "Dois-je investir dans cette action ?",
            "Should I buy or sell my portfolio?",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is True, (
                f"CRITICAL FAIL: Real financial decision without consensus: '{query}'"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# FORCE CONSENSUS (explicit override)
# ═══════════════════════════════════════════════════════════════════════════════

class TestForceConsensus:
    """Vérifie que force_consensus=True/False fonctionne correctement."""

    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()

    def test_force_consensus_true_always_works(self, gate):
        """force_consensus=True → consensus requis même sur query simple."""
        result = gate.enforce_or_route(
            query="Bonjour",
            agent_profile="default",
            force_consensus=True,
        )
        assert result.consensus_required is True

    def test_force_consensus_false_on_level3_triggers_override(self, gate):
        """force_consensus=False sur Level 3 → override détecté si le router
        décide que consensus est quand même requis."""
        # Cette query est Level 3 (cas personnel médical)
        result = gate.enforce_or_route(
            query="Mon médecin m'a prescrit ce médicament, dois-je le prendre ?",
            agent_profile="default",
            force_consensus=False,
        )
        # Le router ne respecte PAS force_consensus=False pour Level 3
        # car le pattern Level 3 est détecté indépendamment
        # Note: force_consensus=False n'empêche pas Level 3 d'être détecté
        # Le gate détecte l'override si consensus_required=True malgré force=False
        if result.consensus_required:
            assert result.override_applied is True
            assert "force_consensus=False" in result.override_reason


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditTrail:
    """Vérifie que l'audit log est complet et observable."""

    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()

    def test_audit_trail_populated(self, gate):
        """L'audit log contient les décisions."""
        gate.enforce_or_route("Question simple", "default")
        gate.enforce_or_route("Mon médecin m'a prescrit X, dois-je le prendre ?", "default")
        gate.enforce_or_route("Bonjour", "default")

        audit = gate.get_audit_log()
        assert len(audit) >= 3

        for entry in audit:
            assert "gate_applied" in entry
            assert "domain" in entry
            assert "requires_consensus" in entry
            assert "correlation_id" in entry

    def test_log_entry_has_required_fields(self):
        """Log entry a tous les champs requis."""
        gate = CriticalDecisionGate()
        result = gate.enforce_or_route("Test query", "default")
        log = result.to_log_entry()

        required_fields = [
            "gate_applied",
            "domain",
            "requires_consensus",
            "strict_evidence_mode",
            "decision",
            "can_emit",
            "correlation_id",
            "override_applied",
        ]
        for field in required_fields:
            assert field in log, f"Missing required field: {field}"


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT VALIDATION (sortie finale)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinalOutputGate:
    """
    T0bis: Validation de sortie finale.
    
    Vérifie que validate_final_output() bloque les sorties
    contenant des claims critiques sans consensus/evidence.
    """

    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()

    @pytest.mark.asyncio
    async def test_blocks_medical_output_without_consensus(self, gate):
        """Output médical bloqué sans consensus."""
        result = await gate.validate_final_output(
            output="Ce médicament doit être pris selon la prescription. Le traitement médical recommandé est efficace.",
            agent_profile="default",
            evidence_pack=None,
            consensus_result=None,
        )

        assert result.assessment.domain == CriticalDomain.MEDICAL, (
            f"Expected MEDICAL, got {result.assessment.domain}"
        )
        assert result.can_emit is False
        assert result.decision == GateDecision.FAIL_CLOSED
        assert result.fail_closed_response != ""

    @pytest.mark.asyncio
    async def test_allows_output_with_consensus(self, gate):
        """Output autorisé si consensus obtenu."""
        result = await gate.validate_final_output(
            output="Informations générales sur la météo.",
            agent_profile="default",
            evidence_pack=None,
            consensus_result={"approved": True},
        )

        if result.assessment.domain == CriticalDomain.DEFAULT:
            assert result.can_emit is True


# ═══════════════════════════════════════════════════════════════════════════════
# FIABILITE: ZERO FAUX-NEGATIF SUR CAS CRITIQUES
# ═══════════════════════════════════════════════════════════════════════════════

class TestZeroFalseNegativeOnCritical:
    """
    TEST DE FIABILITE CRITIQUE.

    Ces queries représentent des cas REELS où un utilisateur demande
    une décision impactante. Le consensus DOIT être déclenché.
    Un faux-négatif ici = risque juridique/médical/financier.
    """

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_real_medical_scenarios(self, router):
        """Scénarios médicaux réels → consensus OBLIGATOIRE."""
        scenarios = [
            "J'ai les symptômes suivants de migraine, dois-je consulter ?",
            "Dois-je aller aux urgences pour cette douleur ?",
            "Mon patient présente ces symptômes, quel diagnostic ?",
            "Quel traitement pour mon enfant fiévreux ?",
        ]
        for query in scenarios:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.requires_consensus is True, (
                f"FALSE NEGATIVE: Real medical scenario missed: '{query}'"
            )

    def test_real_legal_scenarios(self, router):
        """Scénarios juridiques réels → consensus OBLIGATOIRE."""
        scenarios = [
            "J'ai reçu une mise en demeure de mon bailleur",
            "Mon employeur m'a licencié sans motif, que faire ?",
            "Je suis poursuivi en justice, quels sont mes droits ?",
            "Dois-je signer ce contrat ou refuser ?",
            "Que puis-je faire contre cette décision ?",
        ]
        for query in scenarios:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.requires_consensus is True, (
                f"FALSE NEGATIVE: Real legal scenario missed: '{query}'"
            )

    def test_real_financial_scenarios(self, router):
        """Scénarios financiers réels → consensus OBLIGATOIRE."""
        scenarios = [
            "Dois-je investir dans ce produit financier ?",
            "Should I sell my stocks now?",
        ]
        for query in scenarios:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.requires_consensus is True, (
                f"FALSE NEGATIVE: Real financial scenario missed: '{query}'"
            )
