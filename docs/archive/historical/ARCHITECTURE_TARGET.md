> ⚠️ **DOCUMENT ARCHIVÉ**
> **Statut** : Historique / Remplacé
> **Date d'archivage** : 2026-05-31
> **Raison** : Cible consensus « PRISM-first » (janv. 2026). La doctrine « fail-soft : never refuse » décrite ici est remplacée par le **fail-closed par défaut** sur les sorties critiques (ADR-010) ; la cible « single source of truth » est largement réalisée via ADR-008.
> **Remplacé par** : `docs/adr/ADR-008-consensus-v1-to-v2-migration.md`, `docs/adr/ADR-010-critical-output-doctrine.md`
> **Ne pas utiliser comme référence opérationnelle active.**

PRISM-First Consensus - Target Architecture
==========================================

Goals (non-negotiable)
----------------------

- Single Source of Truth: one entrypoint for any consensus decision.
- One enum set: stable casing, backward compatible mapping.
- No simulated approvals in production.
- Fail-soft: never refuse; always return graded reliability.
- No-overkill router: Level 1 never triggers consensus.
- Observability: correlation_id + JSON logs across router->pipeline->consensus.
- Determinism and robustness: 2/3 quorum on valid votes; abstain/timeout excluded.

Core components
---------------

A) ConsensusEngine (authoritative)

- Location: python/consensus/engine.py
- Entry point: run_consensus(evidence_pack, policy) -> ConsensusDecision
- Internals:
  - ConsensusManager (tally, timeouts, quorum)
  - ArbiterCaller (real LLM votes only)
- Guards:
  - No approval without real votes in production
  - Schema validation on inputs/outputs

B) EvidenceAdapters (collect only)

- MCP/web/docs collection
- No decision logic, no simulated votes
- Outputs a normalized evidence_pack

C) IntegrityChecks (optional, non-decision)

- Collaborative debate for hallucination detection
- Produces warnings only (never a verdict)

D) CriticalityRouter (3 levels)

- L1: simple definition/summary/translation/weather -> direct answer
- L2: professional analysis -> structured answer, no consensus
- L3: action/decision/real-case -> consensus + audit + graded reliability
- Domain detection enriches metadata; does not trigger consensus alone

Unified contracts
-----------------

Single enum set (source-of-truth in consensus_contracts.py):

- verdict: approve | reject | abstain
- status: APPROVED | REJECTED | NO_CONSENSUS | INFRA_FAILURE | SKIPPED

Strict validation
-----------------

All inter-module IO is validated using Pydantic schemas:

- EvidencePackSchema (adapter output)
- ConsensusPolicySchema (engine input)
- ConsensusResultSchema (engine output)
- ResponseEnvelope (user-facing output)

Fail-soft ResponseEnvelope
--------------------------

ResponseEnvelope fields (always present for critical outputs):

- answer
- reliability_tiers: [{tier, claims, rationale, sources}]
- unknowns
- recommended_next_steps
- consensus: {status, quorum, votes_summary, warnings}
- debug_trace (optional)

Example flows
-------------

Flow L1 (simple):
  Router(L1) -> direct answer
  No consensus, no integrity checks

Flow L2 (professional):
  Router(L2) -> structured answer
  No consensus by default

Flow L3 (critical):
  Router(L3) -> EvidenceAdapters.collect() -> ConsensusEngine.run_consensus()
  -> (optional) IntegrityChecks
  -> ResponseEnvelope (graded reliability, no refusal)

Migration strategy
------------------

- Add feature flag CONSENSUS_ENGINE_V2
- Default: legacy behavior, but warnings on old entrypoints
- Staging: enable V2, compare audit logs
- Production: switch to V2 and deprecate legacy entrypoints
