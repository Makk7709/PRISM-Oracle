#!/usr/bin/env python3
"""
Test du consensus PRISM avec données réelles.

Ce test vérifie que le système de consensus peut réellement :
1. Contacter les arbitres LLM configurés
2. Obtenir des votes réels
3. Atteindre un consensus

ATTENTION: Ce test nécessite des API keys valides et consommera des tokens.

Usage:
    # Mode simulation (par défaut en développement)
    python -m pytest tests/test_consensus_real.py -v
    
    # Mode réel (nécessite API keys)
    CONSENSUS_SIMULATION=false EVIDENCE_ENV=development python -m pytest tests/test_consensus_real.py::TestRealConsensus -v
"""

import asyncio
import os
import pytest
import json
from typing import Dict, Any

# Configuration pour le test
os.environ.setdefault("EVIDENCE_ENV", "development")


class TestConsensusAudit:
    """Audit complet du système de consensus."""
    
    def test_config_loading(self):
        """Teste le chargement de la configuration consensus."""
        from python.helpers.consensus_arbiter import load_consensus_config
        
        config = load_consensus_config()
        
        # Audit: afficher la configuration
        print("\n=== CONSENSUS CONFIG AUDIT ===")
        print(f"  simulation_enabled: {config.simulation_enabled}")
        print(f"  arbiters_count: {len(config.arbiters)}")
        print(f"  offline_mode: {config.offline_mode}")
        print(f"  global_timeout_ms: {config.global_timeout_ms}")
        print(f"  quorum_ratio: {config.quorum_ratio}")
        
        for i, arbiter in enumerate(config.arbiters):
            print(f"  arbiter[{i}]: {arbiter.provider}/{arbiter.model} (priority={arbiter.priority})")
        
        # Vérifications
        assert config is not None, "Config should load"
        assert len(config.arbiters) > 0, "Should have at least one arbiter configured"
    
    def test_simulation_mode_auto_detection(self):
        """Vérifie que le mode simulation est auto-détecté correctement."""
        from python.helpers.consensus_arbiter import load_consensus_config
        
        # En mode développement, simulation devrait être activée par défaut
        config = load_consensus_config()
        
        print("\n=== SIMULATION MODE AUDIT ===")
        print(f"  EVIDENCE_ENV: {os.environ.get('EVIDENCE_ENV', 'NOT SET')}")
        print(f"  CONSENSUS_SIMULATION: {os.environ.get('CONSENSUS_SIMULATION', 'NOT SET')}")
        print(f"  simulation_enabled: {config.simulation_enabled}")
        
        env = os.environ.get("EVIDENCE_ENV", "development").lower()
        explicit = os.environ.get("CONSENSUS_SIMULATION")
        
        if explicit is None and env == "development":
            assert config.simulation_enabled, "Simulation should be ON in development by default"
        elif explicit is None and env == "production":
            assert not config.simulation_enabled, "Simulation should be OFF in production by default"
    
    @pytest.mark.asyncio
    async def test_consensus_simulation_flow(self):
        """Teste le flux complet du consensus en mode simulation."""
        from python.helpers.consensus_arbiter import (
            ConsensusOrchestrator,
            load_consensus_config,
            ConsensusStatus,
        )
        from python.helpers.consensus_manager import DecisionType
        
        config = load_consensus_config()
        orchestrator = ConsensusOrchestrator(config)
        
        print("\n=== CONSENSUS SIMULATION TEST ===")
        print(f"  simulation_enabled: {config.simulation_enabled}")
        
        # Test action et contexte
        action = "Analyser la responsabilité du transporteur selon L.132-8"
        context = "Question juridique complexe nécessitant consensus"
        
        # Exécuter le consensus
        result = await orchestrator.seek_consensus(
            action=action,
            context=context,
            decision_type=DecisionType.CRITICAL,
            correlation_id="test-consensus-001",
        )
        
        print(f"\n  === RESULT ===")
        print(f"  approved: {result.approved}")
        print(f"  status: {result.status}")
        print(f"  vote_count: {result.vote_count}")
        print(f"  decision_time_ms: {result.decision_time_ms}")
        print(f"  votes:")
        for provider, vote in result.votes.items():
            print(f"    {provider}: {vote.vote.value} ({vote.reasoning[:50]}...)")
        
        if config.simulation_enabled:
            assert result.approved, "Simulation should always approve"
            assert result.status == ConsensusStatus.APPROVED
            assert result.vote_count.total == 3, "Simulation should have 3 votes"
            assert result.vote_count.approvals == 3, "All simulation votes should approve"
        
        return result


class TestRealConsensus:
    """
    Tests avec appels RÉELS aux LLMs.
    
    ATTENTION: Ces tests consomment des tokens et nécessitent des API keys.
    """
    
    @pytest.fixture(autouse=True)
    def check_api_keys(self):
        """Vérifie que les API keys sont disponibles."""
        # Skip si simulation est activée
        if os.environ.get("CONSENSUS_SIMULATION", "").lower() == "true":
            pytest.skip("Skipping real consensus test - simulation mode enabled")
        
        # Vérifier les API keys
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        google_key = os.environ.get("GOOGLE_API_KEY", "")
        
        if not any([openai_key, anthropic_key, google_key]):
            pytest.skip("No API keys found - skipping real consensus test")
    
    @pytest.mark.asyncio
    async def test_real_arbiter_call(self):
        """
        Teste un appel RÉEL à un arbitre LLM.
        
        Ce test:
        1. Contacte un vrai LLM arbitre
        2. Soumet une question juridique
        3. Obtient un vote réel
        """
        # Forcer mode non-simulation pour ce test
        old_sim = os.environ.get("CONSENSUS_SIMULATION")
        os.environ["CONSENSUS_SIMULATION"] = "false"
        
        try:
            from python.helpers.consensus_arbiter import (
                ConsensusOrchestrator,
                load_consensus_config,
                reset_consensus_orchestrator,
            )
            from python.helpers.consensus_manager import DecisionType
            
            # Reset pour recharger la config sans simulation
            reset_consensus_orchestrator()
            
            config = load_consensus_config()
            
            print("\n=== REAL CONSENSUS TEST ===")
            print(f"  simulation_enabled: {config.simulation_enabled}")
            print(f"  arbiters: {[f'{a.provider}/{a.model}' for a in config.arbiters]}")
            
            if config.simulation_enabled:
                pytest.skip("Config still has simulation enabled")
            
            orchestrator = ConsensusOrchestrator(config)
            
            # Question juridique réelle
            action = """
            Analyser la responsabilité du transporteur exécutant selon l'article L.132-8 
            du Code de commerce français. Le donneur d'ordre affirme avoir déjà payé 
            le commissionnaire. Le transporteur réclame un paiement direct.
            """
            context = """
            Question de droit français - transport de marchandises.
            Enjeu: Déterminer si le donneur d'ordre peut opposer le paiement au 
            commissionnaire pour refuser le paiement au transporteur.
            """
            
            # Exécuter le consensus RÉEL
            result = await orchestrator.seek_consensus(
                action=action,
                context=context,
                decision_type=DecisionType.CRITICAL,
                correlation_id="test-real-consensus-001",
            )
            
            print(f"\n  === REAL RESULT ===")
            print(f"  approved: {result.approved}")
            print(f"  status: {result.status}")
            print(f"  vote_count: total={result.vote_count.total}, "
                  f"approvals={result.vote_count.approvals}, "
                  f"rejections={result.vote_count.rejections}, "
                  f"unavailable={result.vote_count.unavailable}")
            print(f"  decision_time_ms: {result.decision_time_ms}")
            
            print(f"\n  === VOTES ===")
            for provider, vote in result.votes.items():
                print(f"  [{provider}]")
                print(f"    vote: {vote.vote.value}")
                print(f"    confidence: {vote.confidence}")
                print(f"    reasoning: {vote.reasoning[:200]}...")
            
            # Assertions pour test réel
            assert result.vote_count.total > 0, "Should have at least one vote"
            assert result.decision_time_ms > 0, "Should have taken some time"
            
            return result
            
        finally:
            # Restaurer l'environnement
            if old_sim is not None:
                os.environ["CONSENSUS_SIMULATION"] = old_sim
            else:
                os.environ.pop("CONSENSUS_SIMULATION", None)


class TestLegalOrchestratorConsensus:
    """Tests du consensus spécifique au pipeline juridique."""
    
    def test_legal_consensus_config(self):
        """Teste la configuration du consensus juridique."""
        from python.helpers.legal_orchestrator import is_consensus_simulation_enabled
        
        print("\n=== LEGAL CONSENSUS CONFIG ===")
        print(f"  EVIDENCE_ENV: {os.environ.get('EVIDENCE_ENV', 'NOT SET')}")
        print(f"  LEGAL_CONSENSUS_SIMULATION: {os.environ.get('LEGAL_CONSENSUS_SIMULATION', 'NOT SET')}")
        print(f"  simulation_enabled: {is_consensus_simulation_enabled()}")
        
        env = os.environ.get("EVIDENCE_ENV", "development").lower()
        explicit = os.environ.get("LEGAL_CONSENSUS_SIMULATION")
        
        if explicit is None and env == "development":
            assert is_consensus_simulation_enabled(), "Legal simulation should be ON in development"
    
    @pytest.mark.asyncio
    async def test_legal_pipeline_with_consensus(self):
        """Teste le pipeline juridique complet avec consensus."""
        try:
            from python.helpers.legal_pipeline import (
                run_legal_pipeline,
                is_legal_pipeline_enabled,
                LegalOutput,
            )
        except ImportError as e:
            pytest.skip(f"Legal pipeline not available: {e}")
        
        if not is_legal_pipeline_enabled():
            pytest.skip("Legal pipeline not enabled")
        
        print("\n=== LEGAL PIPELINE WITH CONSENSUS ===")
        
        query = """
        En tant que donneur d'ordre, puis-je refuser de payer le transporteur 
        exécutant qui me réclame un paiement direct sur le fondement de 
        l'article L.132-8 du Code de commerce, si j'ai déjà intégralement 
        payé le commissionnaire de transport ?
        """
        
        output = await run_legal_pipeline(
            query=query,
            correlation_id="test-legal-consensus-001",
        )
        
        print(f"  mode: {output.mode}")
        print(f"  consensus_status: {output.consensus_status}")
        print(f"  confidence: {output.confidence}")
        print(f"  risk_tier: {output.risk_tier}")
        print(f"  answer_preview: {output.answer[:200]}...")
        
        assert isinstance(output, LegalOutput), "Should return LegalOutput"
        assert output.mode is not None, "Should have a mode"


if __name__ == "__main__":
    # Exécuter les tests d'audit
    pytest.main([__file__, "-v", "-s"])
