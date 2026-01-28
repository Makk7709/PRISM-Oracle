PRISM Consensus - Current Architecture (Snapshot)
=================================================

Scope
-----
This document maps the current consensus stack across:
- python/helpers/consensus_manager.py
- python/helpers/consensus_arbiter.py
- python/helpers/consensus_contracts.py
- python/helpers/consensus_integration.py
- python/helpers/consensus_mcp_integration.py
- python/helpers/research_consensus_integration.py
- python/helpers/criticality_router.py
- python/helpers/router/router.py (deterministic routing)

Public entrypoints (current)
---------------------------
1) python/helpers/consensus_arbiter.py
   - get_consensus_orchestrator()
   - ConsensusOrchestrator.seek_consensus()
   - seek_consensus() (module function)
   - Delegates to python/consensus/engine.py

2) python/helpers/consensus_integration.py
   - ResearchPipeline.validate_with_consensus()
   - Delegates to python/consensus/engine.py

3) python/helpers/consensus_mcp_integration.py
   - research_with_consensus() -> MCP collect + engine.run_consensus()

4) python/helpers/research_consensus_integration.py
   - ResearchConsensusPipeline.research() -> CriticalityRouter -> Evidence -> ConsensusOrchestrator

5) python/helpers/research_pipeline.py
   - ResearchPipeline._validate_consensus() -> ConsensusManager (local)

Router and triggers
-------------------
- python/helpers/criticality_router.py
  - Level 1 / 2 / 3 classification exists in code, but tests expect
    domain detection to trigger consensus (legacy mismatch).
  - Multiple triggers still present in other pipelines.
- python/helpers/router/router.py
  - Deterministic routing for agent intent (not consensus).

Call graph (simplified)
-----------------------
User request
  -> router/router.decide_route(...)  (intent routing)
  -> criticality_router.CriticalityRouter.assess(...)
     -> in research_consensus_integration:
        -> EvidenceBuilder.build()
        -> ConsensusOrchestrator.seek_consensus(...)
           -> ConsensusManager.propose(...)
           -> ArbiterCaller.call_arbiter(...) (LLM votes)
           -> ConsensusManager.submit_vote(...)
           -> ConsensusManager.wait_for_consensus(...)

Other parallel consensus paths
------------------------------
- consensus_integration.ResearchPipeline
  -> MCP collect + engine.run_consensus()
- consensus_mcp_integration.research_with_consensus
  -> MCP collect + engine.run_consensus()
- research_pipeline.ResearchPipeline
  -> analysis + engine.run_consensus()

Key collisions and risks
------------------------
- Multiple entrypoints exist but now delegate to engine (single decision point).
- Enum duplication eliminated by importing from consensus_contracts.
- Simulated votes removed from adapters; engine enforces real votes in production.
- Status vocabulary aligned (NO_CONSENSUS/INFRA_FAILURE; legacy TIMEOUT removed).
- Router now enforces L1/L2/L3 "no-overkill" behavior.
- User-facing narration should be suppressed in user channel (logs are JSON).
- Correlation_id is logged across router->adapter->arbiter->tally->envelope.

Impact summary
--------------
The consensus decision is not centralized. The system has multiple
orchestrators, duplicated contracts, and heuristic approval paths. This
violates single source of truth, deterministic routing, and auditability.
