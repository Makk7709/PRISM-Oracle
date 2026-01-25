"""
Tests pour vérifier que les votes simulés sont INTERDITS en production.

T4: CONSENSUS_SIMULATION=true en production → HARD FAIL
"""

import os
import pytest
from unittest.mock import patch

from python.helpers.consensus_arbiter import (
    SimulationError,
    load_consensus_config,
    verify_no_simulation_in_production,
    ConsensusConfig,
)


# ═══════════════════════════════════════════════════════════════════════════════
# T4: VOTES SIMULÉS INTERDITS EN PROD
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoSimulationInProduction:
    """Vérifie que CONSENSUS_SIMULATION=true est interdit en production."""
    
    def test_simulation_allowed_in_dev(self):
        """Simulation autorisée en development."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "true",
        }):
            # Ne doit PAS lever d'exception
            config = load_consensus_config()
            assert config.simulation_enabled is True
    
    def test_simulation_forbidden_in_production(self):
        """CONSENSUS_SIMULATION=true en production → SimulationError."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "production",
            "CONSENSUS_SIMULATION": "true",
        }):
            with pytest.raises(SimulationError) as exc_info:
                load_consensus_config()
            
            assert "FORBIDDEN" in str(exc_info.value)
            assert "production" in str(exc_info.value).lower()
    
    def test_verify_function_raises_in_production(self):
        """verify_no_simulation_in_production() lève une erreur en prod."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "production",
            "CONSENSUS_SIMULATION": "true",
        }):
            with pytest.raises(SimulationError):
                verify_no_simulation_in_production()
    
    def test_simulation_disabled_by_default(self):
        """Simulation désactivée par défaut."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "production",
            "CONSENSUS_SIMULATION": "false",
        }, clear=True):
            config = load_consensus_config()
            assert config.simulation_enabled is False
    
    def test_default_env_is_production(self):
        """Sans EVIDENCE_ENV, on assume production."""
        with patch.dict(os.environ, {
            "CONSENSUS_SIMULATION": "true",
        }, clear=True):
            # EVIDENCE_ENV absent → default = production
            with pytest.raises(SimulationError):
                load_consensus_config()
    
    def test_simulation_false_works_in_production(self):
        """CONSENSUS_SIMULATION=false fonctionne en production."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "production",
            "CONSENSUS_SIMULATION": "false",
        }):
            # Ne doit pas lever d'exception
            config = load_consensus_config()
            assert config.simulation_enabled is False
    
    def test_simulation_in_test_env(self):
        """Simulation autorisée en test."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "test",
            "CONSENSUS_SIMULATION": "true",
        }):
            # test != production → autorisé
            config = load_consensus_config()
            assert config.simulation_enabled is True


class TestSimulationErrorMessage:
    """Vérifie que le message d'erreur est clair."""
    
    def test_error_message_is_descriptive(self):
        """Le message d'erreur explique le problème."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "production",
            "CONSENSUS_SIMULATION": "true",
        }):
            try:
                load_consensus_config()
                assert False, "Should have raised"
            except SimulationError as e:
                msg = str(e)
                # Doit contenir des instructions claires
                assert "CONSENSUS_SIMULATION" in msg
                assert "FORBIDDEN" in msg or "forbidden" in msg.lower()
                assert "production" in msg.lower()


class TestArbiterConfigValidation:
    """Tests de la configuration des arbitres."""
    
    def test_default_arbiters_configured(self):
        """3 arbitres par défaut."""
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_SIMULATION": "false",
        }):
            config = load_consensus_config()
            assert len(config.arbiters) >= 3
    
    def test_custom_arbiters_from_env(self):
        """Arbitres personnalisés via env."""
        custom_arbiters = '[{"provider":"custom","model":"test-model"}]'
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_ARBITERS": custom_arbiters,
        }):
            config = load_consensus_config()
            assert any(a.provider == "custom" for a in config.arbiters)
    
    def test_local_arbiters_for_offline(self):
        """Arbitres locaux pour mode offline."""
        local_arbiters = '[{"provider":"local","model":"llama"}]'
        with patch.dict(os.environ, {
            "EVIDENCE_ENV": "development",
            "CONSENSUS_LOCAL_ARBITERS": local_arbiters,
            "OFFLINE_MODE": "true",
        }):
            config = load_consensus_config()
            assert len(config.local_arbiters) > 0
            assert config.offline_mode is True
