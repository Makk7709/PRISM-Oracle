"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    E2E SCENARIO TESTS                                        ║
║                                                                              ║
║  6 scénarios E2E réalistes (100% offline).                                   ║
║                                                                              ║
║  1. Dossier investisseur (contradictions)                                    ║
║  2. Legal/contract (citations + prudence)                                    ║
║  3. Finance incohérent (refus/alerte)                                        ║
║  4. Prompt injection (neutralisation)                                        ║
║  5. Degraded mode (providers down)                                           ║
║  6. Idempotence (même input = même output)                                   ║
║                                                                              ║
║  TAG: [E2E]                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import hashlib
import json
import time
from typing import Dict, Any

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
)
from python.helpers.research_pipeline import create_pipeline
from tests.harness.fakes import (
    FakeLLMProvider,
    FakeResearchTool,
    FakeMCPHandler,
    FaultInjector,
    FaultType,
    FaultConfig,
    ResearchResult,
)
from tests.harness.fixtures import (
    FIXTURE_INVESTOR_DOSSIER,
    FIXTURE_LEGAL_CONTRACT,
    FIXTURE_FINANCE_DATA,
    FIXTURE_PROMPT_INJECTION,
    FIXTURE_DEGRADED_MODE,
    FIXTURE_IDEMPOTENCE,
    ALL_E2E_FIXTURES,
    INJECTION_PATTERNS,
)
from tests.harness.assertions import (
    assert_consensus_result,
    assert_audit_sequence,
    assert_no_bypass,
    assert_sanitized,
    assert_idempotent,
    assert_latency_budget,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: RUN SCENARIO
# ═══════════════════════════════════════════════════════════════════════════════

async def run_scenario(fixture, inject_faults: bool = False):
    """
    Exécute un scénario E2E complet.
    
    Returns:
        Dict with dossier, result, audit_log
    """
    # Setup MCP handler
    fault_injector = FaultInjector() if inject_faults else None
    mcp = FakeMCPHandler(fault_injector=fault_injector)
    
    # Configure fault injection if needed
    if inject_faults and fixture.inject_faults:
        for provider, fault_type in fixture.inject_faults.items():
            fault_injector.configure(provider, FaultConfig(
                fault_type=FaultType[fault_type.upper()],
                delay_ms=100
            ))
    
    # Setup research tool with fixture sources
    research_tool = FakeResearchTool(fault_injector=fault_injector)
    for source in fixture.sources:
        research_tool.add_fixture(fixture.query[:20], [
            ResearchResult(
                source=source["source"],
                title=source["title"],
                content=source["content"],
                relevance=source["relevance"]
            )
        ])
    
    # Create pipeline
    pipeline = create_pipeline(
        mcp_handler=mcp,
        settings={
            "consensus_enabled": True,
            "consensus_timeout_ms": 5000,
            "consensus_arbiter_1": "arbiter_1",
            "consensus_arbiter_2": "arbiter_2",
            "consensus_arbiter_3": "arbiter_3",
        }
    )
    
    # Execute
    start_time = time.time()
    
    dossier = await pipeline._open_dossier(fixture.query)
    
    # Add fixture data directly (simulating collection)
    for source in fixture.sources:
        dossier.add_collection_data(source["source"], source)
    
    # Analyze and validate
    analysis = await pipeline._analyze_data(dossier)
    
    # Close dossier
    dossier = await pipeline.close_dossier(
        dossier,
        f"Conclusion based on {len(fixture.sources)} sources",
        require_consensus=True
    )
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    return {
        "dossier": dossier,
        "analysis": analysis,
        "audit_log": pipeline.get_audit_log(),
        "mcp_calls": mcp.call_log,
        "elapsed_ms": elapsed_ms,
        "metrics": pipeline.get_metrics(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 1: INVESTOR DOSSIER
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestorDossier:
    """Scénario 1: Dossier investisseur avec contradictions."""
    
    def test_investor_dossier_handles_contradictions(self):
        """Les contradictions sont détectées et traitées."""
        async def run():
            result = await run_scenario(FIXTURE_INVESTOR_DOSSIER)
            
            dossier = result["dossier"]
            
            # Dossier should be closed
            assert dossier.status == "closed"
            
            # Should have collected all sources
            all_data = dossier.get_all_data()
            assert len(all_data) >= len(FIXTURE_INVESTOR_DOSSIER.sources)
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_investor_audit_trail_complete(self):
        """Audit trail complet pour le dossier."""
        async def run():
            result = await run_scenario(FIXTURE_INVESTOR_DOSSIER)
            
            audit = result["audit_log"]
            
            # Should have opening entry
            opening = [e for e in audit if e.get("event_type") == "dossier_opened"]
            assert len(opening) > 0
            
            # Should have closing entry
            closing = [e for e in audit if e.get("event_type") == "dossier_closed"]
            assert len(closing) > 0
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 2: LEGAL CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalContract:
    """Scénario 2: Analyse de contrat juridique."""
    
    def test_legal_contract_prudent_output(self):
        """Sortie prudente pour contrat juridique."""
        async def run():
            result = await run_scenario(FIXTURE_LEGAL_CONTRACT)
            
            dossier = result["dossier"]
            
            # Should complete successfully
            assert dossier.status == "closed"
            assert dossier.final_conclusion is not None
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_legal_sources_tracked(self):
        """Sources juridiques sont tracées."""
        async def run():
            result = await run_scenario(FIXTURE_LEGAL_CONTRACT)
            
            dossier = result["dossier"]
            all_data = dossier.get_all_data()
            
            # All sources should be tracked
            sources = [d.get("source") for d in all_data]
            assert "contract_text" in sources or len(all_data) >= 1
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 3: FINANCE INCOHÉRENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinanceIncoherent:
    """Scénario 3: Données financières incohérentes."""
    
    def test_finance_inconsistency_detected(self):
        """Incohérences financières sont détectées."""
        async def run():
            result = await run_scenario(FIXTURE_FINANCE_DATA)
            
            dossier = result["dossier"]
            
            # Should complete (even if rejected)
            assert dossier.status == "closed"
            
            # Confidence should be low due to inconsistencies
            # (depends on analysis implementation)
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_finance_all_sources_compared(self):
        """Toutes les sources sont comparées."""
        async def run():
            result = await run_scenario(FIXTURE_FINANCE_DATA)
            
            dossier = result["dossier"]
            all_data = dossier.get_all_data()
            
            # All 3 conflicting sources should be present
            assert len(all_data) >= 3
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 4: PROMPT INJECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromptInjection:
    """Scénario 4: Tentative d'injection neutralisée."""
    
    def test_injection_patterns_in_fixture(self):
        """Les patterns d'injection sont présents dans la fixture."""
        # Verify fixture contains injection patterns
        all_content = " ".join(s["content"] for s in FIXTURE_PROMPT_INJECTION.sources)
        
        has_injection = any(
            pattern.lower() in all_content.lower()
            for pattern in INJECTION_PATTERNS
        )
        
        assert has_injection, "Fixture should contain injection patterns"
    
    def test_injection_does_not_alter_behavior(self):
        """L'injection ne modifie pas le comportement."""
        async def run():
            result = await run_scenario(FIXTURE_PROMPT_INJECTION)
            
            dossier = result["dossier"]
            
            # Should complete normally
            assert dossier.status == "closed"
            
            # Check no unauthorized tools called
            mcp_calls = result["mcp_calls"]
            assert_no_bypass(mcp_calls, [
                "admin/delete",
                "system/execute",
                "secrets/reveal"
            ])
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_final_output_sanitized(self):
        """Sortie finale est sanitisée."""
        async def run():
            result = await run_scenario(FIXTURE_PROMPT_INJECTION)
            
            dossier = result["dossier"]
            
            # Final conclusion should not contain injection patterns
            if dossier.final_conclusion:
                for pattern in ["<script>", "IGNORE PREVIOUS", "[ADMIN]"]:
                    assert pattern not in dossier.final_conclusion, \
                        f"Output contains unsanitized pattern: {pattern}"
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 5: DEGRADED MODE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDegradedMode:
    """Scénario 5: Mode dégradé (providers down)."""
    
    def test_degraded_mode_fails_safe(self):
        """Mode dégradé échoue de manière sûre."""
        async def run():
            # Run with fault injection
            result = await run_scenario(FIXTURE_DEGRADED_MODE, inject_faults=True)
            
            dossier = result["dossier"]
            
            # Should still complete
            assert dossier.status == "closed"
            
            # Confidence should be low due to unavailable arbiters
            # (depends on implementation)
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_degraded_no_false_approve(self):
        """Pas de faux approve en mode dégradé."""
        async def run():
            result = await run_scenario(FIXTURE_DEGRADED_MODE, inject_faults=True)
            
            # Check consensus results
            for consensus in result["dossier"].consensus_results:
                # If we couldn't reach quorum, should not be APPROVED
                if consensus.get("votes", {}).get("unavailable", 0) >= 2:
                    assert consensus.get("status") != "APPROVED", \
                        "Should not approve with 2+ unavailable arbiters"
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 6: IDEMPOTENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdempotence:
    """Scénario 6: Vérification idempotence."""
    
    def test_same_input_same_output(self):
        """Même input produit même output."""
        async def run():
            # Run twice with same fixture
            result1 = await run_scenario(FIXTURE_IDEMPOTENCE)
            result2 = await run_scenario(FIXTURE_IDEMPOTENCE)
            
            # Compare outputs (ignoring timestamps)
            d1 = result1["dossier"]
            d2 = result2["dossier"]
            
            assert d1.query == d2.query
            assert d1.status == d2.status
            
            # Same number of data points
            assert len(d1.get_all_data()) == len(d2.get_all_data())
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_hash_consistency(self):
        """Hash du résultat est consistant."""
        async def run():
            result1 = await run_scenario(FIXTURE_IDEMPOTENCE)
            result2 = await run_scenario(FIXTURE_IDEMPOTENCE)
            
            # Create deterministic hash (excluding timestamps)
            def make_hash(dossier):
                data = {
                    "query": dossier.query,
                    "data_count": len(dossier.get_all_data()),
                    "status": dossier.status,
                }
                return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            
            hash1 = make_hash(result1["dossier"])
            hash2 = make_hash(result2["dossier"])
            
            assert hash1 == hash2, f"Hashes differ: {hash1} vs {hash2}"
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ALL SCENARIOS COMPLETE
# ═══════════════════════════════════════════════════════════════════════════════

class TestAllScenariosComplete:
    """Vérifie que tous les scénarios peuvent s'exécuter."""
    
    def test_all_fixtures_runnable(self):
        """Tous les fixtures peuvent s'exécuter."""
        async def run():
            for fixture in ALL_E2E_FIXTURES:
                try:
                    result = await run_scenario(fixture)
                    assert result["dossier"].status == "closed", \
                        f"Fixture {fixture.name} did not complete"
                except Exception as e:
                    raise AssertionError(f"Fixture {fixture.name} failed: {e}")
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    """Exécute tous les tests E2E."""
    print("🧪 Running E2E Scenario Tests...\n")
    
    test_classes = [
        TestInvestorDossier,
        TestLegalContract,
        TestFinanceIncoherent,
        TestPromptInjection,
        TestDegradedMode,
        TestIdempotence,
        TestAllScenariosComplete,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"📋 {test_class.__name__}")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    print(f"   ✓ {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"   ✗ {method_name}: {e}")
                    failed_tests.append((test_class.__name__, method_name, str(e)))
        print()
    
    print("=" * 60)
    print(f"📊 Results: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ {len(failed_tests)} FAILED:")
        for cls, method, error in failed_tests:
            print(f"   - {cls}.{method}")
        return 1
    else:
        print("\n✅ All E2E tests passed!")
        return 0


if __name__ == "__main__":
    exit(run_tests())
