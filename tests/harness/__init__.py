"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TEST HARNESS - PRISM + EVIDENCE                             ║
║                                                                              ║
║  Harness de test déterministe pour PRISM Consensus et Evidence.                ║
║  100% offline, seeds fixes, latences contrôlées, fautes injectables.         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from .fakes import (
    FakeLLMProvider,
    FakeResearchTool,
    FakeMemoryStore,
    FakeMCPHandler,
    FaultInjector,
    TestClock,
    CorrelationContext,
)

from .fixtures import (
    FIXTURE_INVESTOR_DOSSIER,
    FIXTURE_LEGAL_CONTRACT,
    FIXTURE_FINANCE_DATA,
    FIXTURE_PROMPT_INJECTION,
    FIXTURE_DEGRADED_MODE,
    FIXTURE_IDEMPOTENCE,
)

from .assertions import (
    assert_contract_valid,
    assert_vote_schema,
    assert_consensus_result,
    assert_audit_entry,
    assert_no_bypass,
    assert_sanitized,
)

__all__ = [
    "FakeLLMProvider",
    "FakeResearchTool",
    "FakeMemoryStore",
    "FakeMCPHandler",
    "FaultInjector",
    "TestClock",
    "CorrelationContext",
    "FIXTURE_INVESTOR_DOSSIER",
    "FIXTURE_LEGAL_CONTRACT",
    "FIXTURE_FINANCE_DATA",
    "FIXTURE_PROMPT_INJECTION",
    "FIXTURE_DEGRADED_MODE",
    "FIXTURE_IDEMPOTENCE",
    "assert_contract_valid",
    "assert_vote_schema",
    "assert_consensus_result",
    "assert_audit_entry",
    "assert_no_bypass",
    "assert_sanitized",
]
