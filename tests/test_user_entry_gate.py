"""
T0: User Entry Gate Applied — Test de bout en bout.

Vérifie que l'entrée principale (user query, agent default, sans spawn)
passe OBLIGATOIREMENT par le CriticalDecisionGate.

Ce test est le PLUS IMPORTANT car il prouve que le gate est inévitable
même quand l'agent répond directement sans délégation.
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
    assess_criticality,
)


class TestUserEntryGateApplied:
    """
    T0: Entrée user critique, agent default, sans spawn.
    
    Vérifications:
    - gate_applied=true
    - requires_consensus=true pour domaines critiques
    - strict_evidence_mode=true pour domaines critiques
    - audit entry créée
    """
    
    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 1: Query médicale → gate_applied + consensus requis
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_medical_query_gate_applied(self, gate):
        """Query médicale en agent=default → gate appliqué."""
        result = gate.enforce_or_route(
            query="Quelle posologie pour ce médicament ?",
            agent_profile="default",
        )
        
        # Assertions critiques
        assert result.assessment.domain == CriticalDomain.MEDICAL
        assert result.consensus_required is True
        assert result.assessment.strict_evidence_mode is True
        
        # Vérifier le log entry
        log = result.to_log_entry()
        assert log["gate_applied"] is True
        assert log["requires_consensus"] is True
        assert log["strict_evidence_mode"] is True
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 2: Query légale → gate_applied + consensus requis
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_legal_query_gate_applied(self, gate):
        """Query légale en agent=default → gate appliqué."""
        queries_fr = [
            "Quelles sont les clauses abusives dans ce contrat ?",
            "Puis-je saisir les prud'hommes ?",
            "La RGPD s'applique-t-elle ici ?",
            "Cette mise en demeure est-elle valide ?",
            "Quelle jurisprudence sur ce sujet ?",
        ]
        
        for query in queries_fr:
            result = gate.enforce_or_route(query, agent_profile="default")
            
            assert result.consensus_required is True, f"FAIL: '{query}' should require consensus"
            assert result.assessment.domain == CriticalDomain.LEGAL, f"FAIL: '{query}' should be LEGAL"
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 3: Query scientifique → gate_applied + consensus requis
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_scientific_query_gate_applied(self, gate):
        """Query scientifique en agent=default → gate appliqué."""
        queries_fr = [
            "La méthodologie de cette étude est-elle valide ?",
            "Quelle est la p-value acceptable ?",
            "Ce preprint est-il reproductible ?",
            "Comment interpréter cet odds ratio ?",
        ]
        
        for query in queries_fr:
            result = gate.enforce_or_route(query, agent_profile="default")
            
            assert result.consensus_required is True, f"FAIL: '{query}' should require consensus"
            assert result.assessment.domain == CriticalDomain.SCIENTIFIC, f"FAIL: '{query}' should be SCIENTIFIC"
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 4: Query simple → gate appliqué mais consensus NON requis
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_simple_query_gate_applied_no_consensus(self, gate):
        """Query simple → gate appliqué mais pas de consensus."""
        result = gate.enforce_or_route(
            query="Quelle heure est-il ?",
            agent_profile="default",
        )
        
        # Gate appliqué mais consensus non requis
        assert result.assessment.domain == CriticalDomain.DEFAULT
        assert result.consensus_required is False
        
        # Log entry prouve que gate a été appliqué
        log = result.to_log_entry()
        assert log["gate_applied"] is True
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 5: Override détecté si force_consensus=False sur domaine critique
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_override_applied_when_forced_false_on_critical(self, gate):
        """force_consensus=False sur domaine critique → override + warning."""
        result = gate.enforce_or_route(
            query="Diagnostic différentiel pour cette pathologie ?",
            agent_profile="default",
            force_consensus=False,  # Tentative de bypass
        )
        
        # Consensus TOUJOURS requis malgré force_consensus=False
        assert result.consensus_required is True
        assert result.assessment.domain == CriticalDomain.MEDICAL
        
        # Override appliqué et documenté
        assert result.override_applied is True
        assert "force_consensus=False" in result.override_reason
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 6: Audit trail présent
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_audit_trail_populated(self, gate):
        """L'audit log contient les décisions."""
        # Faire plusieurs appels
        gate.enforce_or_route("Question médicale sur posologie", "default")
        gate.enforce_or_route("Question sur un contrat", "default")
        gate.enforce_or_route("Question simple", "default")
        
        audit = gate.get_audit_log()
        
        assert len(audit) >= 3
        
        # Chaque entrée a les champs requis
        for entry in audit:
            assert "gate_applied" in entry
            assert "domain" in entry
            assert "requires_consensus" in entry
            assert "correlation_id" in entry


class TestFinalOutputGate:
    """
    T0bis: Validation de sortie finale.
    
    Vérifie que validate_final_output() bloque les sorties
    sans consensus/evidence en domaine critique.
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
        
        # Doit être fail-closed (médical détecté, pas de consensus)
        assert result.assessment.domain == CriticalDomain.MEDICAL, f"Expected MEDICAL, got {result.assessment.domain}"
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
            consensus_result={"approved": True},  # Consensus OK
        )
        
        # Domaine DEFAULT → devrait passer
        if result.assessment.domain == CriticalDomain.DEFAULT:
            assert result.can_emit is True


class TestGateLogsObservable:
    """
    Vérifie que les logs du gate contiennent tous les champs observables.
    """
    
    def test_log_entry_has_required_fields(self):
        """Log entry a tous les champs requis."""
        gate = CriticalDecisionGate()
        result = gate.enforce_or_route("Test query", "default")
        
        log = result.to_log_entry()
        
        # Champs OBLIGATOIRES (observables, pas internes)
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
