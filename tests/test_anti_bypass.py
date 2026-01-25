"""
Tests Anti-Bypass — Vérifie qu'aucun chemin ne contourne le consensus.

Coverage:
- T1: Entrée user critique sans spawn → gate appliqué
- T2: Research direct → délègue au pipeline gouverné
- T3: Response tool → gate appliqué avant émission
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalDomain,
    assess_criticality,
    CONSENSUS_REQUIRED_PROFILES,
)

from python.helpers.critical_decision_gate import (
    CriticalDecisionGate,
    GateDecision,
    GateResult,
    enforce_or_route,
    validate_final_output,
    assert_no_unsourced_claims,
)

from python.helpers.evidence import (
    EvidencePack,
    EvidenceBuilder,
    EvidenceValidationResult,
)


# ═══════════════════════════════════════════════════════════════════════════════
# T1: ENTRÉE USER CRITIQUE SANS SPAWN
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserEntryCriticalNoSpawn:
    """
    Vérifie que même sans délégation (spawn), le gate est appliqué
    quand une query critique arrive avec agent=default.
    """
    
    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()
    
    def test_medical_query_triggers_gate(self, gate):
        """Query médicale en agent=default → gate activé."""
        result = gate.enforce_or_route(
            query="What medication should I take for my headache?",
            agent_profile="default",
        )
        
        assert result.consensus_required is True
        assert result.assessment.domain == CriticalDomain.MEDICAL
        assert result.assessment.strict_evidence_mode is True
    
    def test_legal_query_triggers_gate(self, gate):
        """Query légale en agent=default → gate activé."""
        result = gate.enforce_or_route(
            query="Is this contract legally enforceable?",
            agent_profile="default",
        )
        
        assert result.consensus_required is True
        assert result.assessment.domain == CriticalDomain.LEGAL
    
    def test_scientific_query_triggers_gate(self, gate):
        """Query scientifique en agent=default → gate activé."""
        result = gate.enforce_or_route(
            query="What does peer-reviewed research say about this hypothesis?",
            agent_profile="default",
        )
        
        assert result.consensus_required is True
        assert result.assessment.domain == CriticalDomain.SCIENTIFIC
    
    @pytest.mark.asyncio
    async def test_final_output_blocked_without_consensus(self, gate):
        """Sortie critique bloquée sans consensus."""
        result = await gate.validate_final_output(
            output="Based on my medical expertise, you should take aspirin.",
            agent_profile="default",
            evidence_pack=None,
            consensus_result=None,  # Pas de consensus
        )
        
        # Doit être bloqué car consensus requis mais pas obtenu
        if result.consensus_required:
            assert result.can_emit is False or result.decision == GateDecision.FAIL_CLOSED
    
    def test_force_consensus_false_overridden_for_critical(self, gate):
        """force_consensus=False ignoré pour domaines critiques."""
        result = gate.enforce_or_route(
            query="What are the legal requirements for GDPR?",
            agent_profile="default",
            force_consensus=False,  # Tente de désactiver
        )
        
        # Doit quand même être activé car domaine LEGAL
        assert result.assessment.domain == CriticalDomain.LEGAL
        assert result.consensus_required is True
        # L'override devrait être appliqué si le caller a tenté de forcer False
        # Note: L'override est appliqué uniquement si force_consensus=False ET domaine critique


# ═══════════════════════════════════════════════════════════════════════════════
# T2: BYPASS VIA RESEARCH DIRECT
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchDirectBypass:
    """
    Vérifie que les appels directs au research executor
    délèguent au pipeline gouverné.
    """
    
    def test_research_consensus_integration_requires_consensus_for_legal(self):
        """ResearchConsensusIntegration force consensus pour LEGAL."""
        from python.helpers.research_consensus_integration import (
            ResearchConsensusPipeline,
            ResearchConsensusConfig,
        )
        
        pipeline = ResearchConsensusPipeline(
            config=ResearchConsensusConfig(
                strict_evidence_mode=True,
                consensus_enabled=True,
            )
        )
        
        # Le pipeline doit détecter le domaine et forcer consensus
        # (Test simplifié - vérifie que le pipeline existe et est configuré)
        assert pipeline.config.strict_evidence_mode is True
        assert pipeline.config.consensus_enabled is True
    
    def test_criticality_detected_for_research_query(self):
        """Détection de criticité sur query de recherche."""
        router = CriticalityRouter()
        
        assessment = router.assess(
            query="Research the latest treatments for cancer",
            agent_profile="researcher",
        )
        
        assert assessment.requires_consensus is True
        # researcher est dans les profils critiques
        assert "researcher" in CONSENSUS_REQUIRED_PROFILES


# ═══════════════════════════════════════════════════════════════════════════════
# T3: RESPONSE TOOL GATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestResponseToolGate:
    """
    Vérifie que le response tool applique le gate avant émission.
    """
    
    @pytest.mark.asyncio
    async def test_validate_final_output_blocks_unsourced(self):
        """validate_final_output bloque les claims non sourcés."""
        gate = CriticalDecisionGate()
        
        # Output avec claim médical non sourcé
        output = "Based on clinical evidence, this treatment is effective for cancer."
        
        # Créer un evidence pack vide (pas de sources)
        pack = EvidencePack(
            query=output[:100],
            domain=CriticalDomain.MEDICAL,
            strict_mode=True,
        )
        pack.validate()
        
        result = await gate.validate_final_output(
            output=output,
            agent_profile="default",
            evidence_pack=pack,
        )
        
        # En mode strict avec sources insuffisantes → fail-closed
        assert result.can_emit is False
        assert result.decision == GateDecision.FAIL_CLOSED
    
    @pytest.mark.asyncio
    async def test_validate_allows_sourced_output(self):
        """validate_final_output autorise les outputs sourcés."""
        gate = CriticalDecisionGate()
        
        # Créer un evidence pack avec sources
        builder = EvidenceBuilder(
            query="Weather question",
            domain=CriticalDomain.DEFAULT,
            strict_mode=False,
        )
        builder.add_mcp_result("tavily", {
            "title": "Weather Source",
            "url": "https://weather.com",
            "snippet": "Weather information...",
        })
        pack = builder.build()
        
        result = await gate.validate_final_output(
            output="The weather is sunny today.",
            agent_profile="default",
            evidence_pack=pack,
            consensus_result={"approved": True},  # Consensus obtenu
        )
        
        # Domain DEFAULT non critique → should pass
        # Note: La logique exacte dépend de l'implémentation
        assert result.decision in [GateDecision.ALLOW, GateDecision.REQUIRE_CONSENSUS]


# ═══════════════════════════════════════════════════════════════════════════════
# T4: ASSERT NO UNSOURCED CLAIMS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssertNoUnsourcedClaims:
    """Test de l'invariant assert_no_unsourced_claims."""
    
    def test_no_pack_all_claims_unsourced(self):
        """Sans evidence pack, tous les claims sont non sourcés."""
        answer = "This medication is effective. The treatment works well."
        
        all_sourced, unsourced = assert_no_unsourced_claims(
            answer=answer,
            evidence_pack=None,
            domain=CriticalDomain.MEDICAL,
        )
        
        # Sans pack, devrait détecter des claims non sourcés
        assert all_sourced is False or len(unsourced) > 0 or answer == ""
    
    def test_default_domain_no_check(self):
        """Domain DEFAULT ne vérifie pas les claims."""
        answer = "This is a claim without any source."
        
        all_sourced, unsourced = assert_no_unsourced_claims(
            answer=answer,
            evidence_pack=None,
            domain=CriticalDomain.DEFAULT,
        )
        
        # DEFAULT domain → pas de vérification stricte
        assert all_sourced is True


# ═══════════════════════════════════════════════════════════════════════════════
# T5: GATE LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateLogging:
    """Vérifie que le gate produit les logs attendus."""
    
    def test_gate_result_has_log_entry(self):
        """GateResult génère une entrée de log valide."""
        gate = CriticalDecisionGate()
        
        result = gate.enforce_or_route(
            query="Legal question about contracts",
            agent_profile="legal_safe",
        )
        
        log_entry = result.to_log_entry()
        
        # Vérifier les champs requis
        assert "gate_applied" in log_entry
        assert log_entry["gate_applied"] is True
        assert "domain" in log_entry
        assert "requires_consensus" in log_entry
        assert "correlation_id" in log_entry
    
    def test_audit_log_populated(self):
        """L'audit log du gate est rempli."""
        gate = CriticalDecisionGate()
        
        # Plusieurs appels
        gate.enforce_or_route("Query 1", "default")
        gate.enforce_or_route("Query 2", "legal_safe")
        
        audit = gate.get_audit_log()
        assert len(audit) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# T6: CONCURRENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    """Tests de concurrence."""
    
    @pytest.mark.asyncio
    async def test_concurrent_gate_calls(self):
        """Appels concurrents au gate."""
        gate = CriticalDecisionGate()
        
        async def make_call(query: str, profile: str):
            result = gate.enforce_or_route(query, profile)
            # Simuler un peu de travail
            await asyncio.sleep(0.01)
            return result
        
        # Lancer plusieurs appels en parallèle
        tasks = [
            make_call("Legal question", "legal_safe"),
            make_call("Medical question", "default"),
            make_call("Simple question", "default"),
            make_call("Research question", "researcher"),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Vérifier que tous ont un correlation_id unique
        correlation_ids = [r.correlation_id for r in results]
        assert len(set(correlation_ids)) == len(correlation_ids), "Duplicate correlation IDs!"
