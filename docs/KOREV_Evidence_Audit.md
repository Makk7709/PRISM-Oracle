# KOREV Evidence — Objective Audit (Evidence-Based)
## Executive Summary (FR)
Pipeline multi-agents verifiable par code/tests. [C-001]  
Routage deterministe disponible mais flag-gate. [C-002]  
Detection d'injection dans le routeur (usage conditionnel). [C-003]  
Consensus multi-LLM (quorum 2/3) disponible. [C-005]  
Debat collaboratif 3 tours pour claims. [C-021]  
Fail-closed present (consensus/contrats). [C-007]  
Contrat medical FAIL_CLOSED sur sortie non conforme. [C-008]  
Pipeline legal avec invariants + tests E2E. [C-009]  
Securite API par handler (cle/loopback/CSRF). [C-011]  
Audit persistant long terme non demontre. UNVERIFIED  
Suivi couts/tokens non demontre. UNVERIFIED  
Redaction PII automatique non demontree. UNVERIFIED  
Deploiement documente via Docker compose. [C-012]

## Executive Summary (EN)
Multi-agent pipeline backed by code/tests. [C-001]  
Deterministic routing exists but is flag-gated. [C-002]  
Prompt-injection detection exists in router (conditional). [C-003]  
Multi-LLM consensus (2/3 quorum) exists. [C-005]  
3-round collaborative debate exists. [C-021]  
Fail-closed behaviors exist. [C-007]  
Medical output contract enforces FAIL_CLOSED. [C-008]  
Legal pipeline has invariants + E2E tests. [C-009]  
API security is per-handler (API key/loopback/CSRF). [C-011]  
Long-term audit retention not proven. UNVERIFIED  
Cost/token tracking not proven. UNVERIFIED  
Automatic PII redaction not proven. UNVERIFIED  
Deployment documented via Docker compose. [C-012]

## 1. Scope & Method
- What was inspected (folders, entrypoints)
  - `python/`, `agents/`, `prompts/`, `tests/`, `deploy/`, `docker/`, `docs/`, `webui/`
  - Entrypoints: `initialize.py`, `run_ui.py`, `run_tunnel.py`
- Evidence policy (how claims are validated)
  - Priority: tests > code > docs/prompts
  - Any claim without concrete code/test evidence is labeled `UNVERIFIED`
- How to reproduce (commands)
  - `python -m pytest tests/test_prism_consensus.py -v`
  - `python -m pytest tests/test_prism_tally_quorum.py -v`
  - `python -m pytest tests/test_router_determinism.py -v`
  - `python -m pytest tests/test_injection_handling.py -v`
  - `python -m pytest tests/test_legal_orchestrator.py -v`
  - `python test_consensus_simple.py`

## 2. Capability Matrix
| Capability | Status | ClaimID | Evidence (file/function/test) | How to validate | Notes/limits |
|---|---|---|---|---|---|
| Deterministic routing | Partial | C-002 | `python/helpers/router/router.py`; `tests/test_router_determinism.py` | Run router tests | Flag-gated |
| Prompt-injection detection | Partial | C-003 | `python/helpers/router/router.py`; `tests/test_injection_handling.py` | Run injection tests | Router-dependent |
| Criticality routing | Implemented | C-004 | `python/helpers/criticality_router.py`; `python/tools/call_subordinate.py` | Run criticality tests | Wired |
| Critical decision gate | Partial | C-007 | `python/helpers/critical_decision_gate.py` | Inspect wiring | Wiring unclear |
| Evidence pack | Partial | C-006 | `python/helpers/evidence.py` | Unit inspection | Wiring unclear |
| Consensus PRISM (2/3) | Implemented | C-005 | `python/helpers/consensus_manager.py`; `tests/test_prism_tally_quorum.py` | Run quorum tests | Providers required |
| LLM arbiter calling | Partial | C-010 | `python/helpers/consensus_arbiter.py`; `python/helpers/llm_provider.py` | Manual | No integration test |
| Consensus simulation guard | Partial | C-013 | `python/helpers/consensus_arbiter.py` | Manual | No test |
| Collaborative debate | Partial | C-021 | `python/helpers/collaborative_consensus.py` | Manual | No test |
| Debate integration | Partial | C-014 | `python/tools/call_subordinate.py` | Manual | No test |
| Legal pipeline | Partial | C-009 | `python/helpers/legal_orchestrator.py`; `tests/test_legal_orchestrator.py` | Run legal tests | External index |
| Medical contract | Partial | C-008 | `python/helpers/medical_contract.py` | Schema validation | Wiring unclear |
| Tool policy (images) | Partial | C-015 | `python/helpers/tool_policy.py` | Inspect policy | Image-only |
| Response envelope | Partial | C-016 | `python/helpers/response_contract.py` | Schema validation | Wiring unclear |
| Router metrics | Partial | C-017 | `python/helpers/router/metrics.py` | Inspect metrics | Router-dependent |
| API key protection | Partial | C-011 | `run_ui.py`; `python/api/api_message.py` | Test endpoint | Per-handler |
| CSRF protection | Partial | C-011 | `run_ui.py`; `python/helpers/api.py` | Test endpoint | Auth-only |
| Cost/token accounting | Unverified | C-019 | NOT FOUND | N/A | UNVERIFIED |
| Audit retention | Partial | C-018 | `deploy/docker-compose.yml` volume `evidence-audit` | Manual | Not enforced |
| PII redaction | Unverified | C-020 | NOT FOUND | N/A | UNVERIFIED |

## 2.1 Registre des briques (Brick Register)
### B-001 — Routage deterministe (Router V2)
- Statut: Partial
- ClaimID: C-002
- Preuves:
  - Code: `python/helpers/router/router.py` `decide_route()`
  - Test: `tests/test_router_determinism.py`
  - Wiring runtime: `python/tools/call_subordinate.py` (flag `DETERMINISTIC_ROUTER_V2`)
- Validation:
  - Commande: `python -m pytest tests/test_router_determinism.py -v`
  - Preuve attendue: tests PASS
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Desactive si flag off

### B-002 — Detection d'injection (Router)
- Statut: Partial
- ClaimID: C-003
- Preuves:
  - Code: `python/helpers/router/router.py` `_check_injection()`
  - Test: `tests/test_injection_handling.py`
  - Wiring runtime: depend du router deterministe
- Validation:
  - Commande: `python -m pytest tests/test_injection_handling.py -v`
  - Preuve attendue: tests PASS
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Inactif si router desactive

### B-003 — Evaluation de criticite (router)
- Statut: Implemented
- ClaimID: C-004
- Preuves:
  - Code: `python/helpers/criticality_router.py`
  - Wiring runtime: `python/tools/call_subordinate.py` `router.assess(...)`
  - Test: `tests/test_criticality_router.py`
- Validation:
  - Commande: `python -m pytest tests/test_criticality_router.py -v`
  - Preuve attendue: tests PASS
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Regles heuristiques

### B-004 — Gate fail-closed
- Statut: Partial
- ClaimID: C-007
- Preuves:
  - Code: `python/helpers/critical_decision_gate.py`
  - Test: `tests/test_strict_evidence_fail_closed.py`
- Validation:
  - Commande: `python -m pytest tests/test_strict_evidence_fail_closed.py -v`
  - Preuve attendue: FAIL_CLOSED sur preuves insuffisantes
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Wiring global non demontre

### B-005 — Evidence Pack
- Statut: Partial
- ClaimID: C-006
- Preuves:
  - Code: `python/helpers/evidence.py`
  - Test: `tests/test_final_output_claim_integrity.py`
- Validation:
  - Commande: `python -m pytest tests/test_final_output_claim_integrity.py -v`
  - Preuve attendue: claims non sources refuses
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Usage runtime incertain

### B-006 — Consensus PRISM (2/3)
- Statut: Implemented
- ClaimID: C-005
- Preuves:
  - Code: `python/helpers/consensus_manager.py` `check_consensus()`
  - Code: `python/consensus/engine.py` `run_consensus()`
  - Test: `tests/test_prism_tally_quorum.py`
  - Wiring runtime: `python/helpers/consensus_arbiter.py` `seek_consensus()`
- Validation:
  - Commande: `python -m pytest tests/test_prism_tally_quorum.py -v`
  - Preuve attendue: quorum 2/3 valide
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Providers LLM requis

### B-007 — Appel arbitres LLM
- Statut: Partial
- ClaimID: C-010
- Preuves:
  - Code: `python/helpers/consensus_arbiter.py` `ArbiterCaller`
  - Code: `python/helpers/llm_provider.py` `get_provider()`
- Validation:
  - Commande: appel consensuel avec API keys valides
  - Preuve attendue: logs `arbiter_call`
  - Critere PASS/FAIL: PASS si votes reels
- Limites:
  - Pas de test d'integration

### B-008 — Guardrail simulation consensus en prod
- Statut: Partial
- ClaimID: C-013
- Preuves:
  - Code: `python/helpers/consensus_arbiter.py` `load_consensus_config()`
- Validation:
  - Commande: `EVIDENCE_ENV=production CONSENSUS_SIMULATION=true python -c "from python.helpers.consensus_arbiter import load_consensus_config; load_consensus_config()"`
  - Preuve attendue: exception SimulationError
  - Critere PASS/FAIL: PASS si exception levee
- Limites:
  - Non teste automatiquement

### B-009 — Debat collaboratif (3 rounds)
- Statut: Partial
- ClaimID: C-021
- Preuves:
  - Code: `python/helpers/collaborative_consensus.py` `run_debate()`
  - Wiring runtime: `python/tools/call_subordinate.py` `_validate_with_consensus()`
- Validation:
  - Commande: delegation critique (legal_safe/medical)
  - Preuve attendue: badge "Debat Collaboratif"
  - Critere PASS/FAIL: PASS si badge affiche
- Limites:
  - Pas de test dedie

### B-010 — Integration debat delegation
- Statut: Partial
- ClaimID: C-014
- Preuves:
  - Code: `python/tools/call_subordinate.py` `_validate_with_consensus()`
- Validation:
  - Commande: `Delegation.execute()` en domaine critique
  - Preuve attendue: logs "COLLABORATIVE DEBATE"
  - Critere PASS/FAIL: PASS si logs presents
- Limites:
  - Depend du routing

### B-011 — Pipeline legal orchestre
- Statut: Partial
- ClaimID: C-009
- Preuves:
  - Code: `python/helpers/legal_orchestrator.py`
  - Test: `tests/test_legal_orchestrator.py`
- Validation:
  - Commande: `python -m pytest tests/test_legal_orchestrator.py -v`
  - Preuve attendue: tests PASS
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Index legal externe requis

### B-012 — Contrat medical (output)
- Statut: Partial
- ClaimID: C-008
- Preuves:
  - Code: `python/helpers/medical_contract.py`
  - Test: `tests/test_medical_agent_hardening.py`
- Validation:
  - Commande: `python -m pytest tests/test_medical_agent_hardening.py -v`
  - Preuve attendue: sorties non conformes rejetees
  - Critere PASS/FAIL: PASS si 0 echec
- Limites:
  - Wiring global non demontre

### B-013 — Tool policy (images)
- Statut: Partial
- ClaimID: C-015
- Preuves:
  - Code: `python/helpers/tool_policy.py`
- Validation:
  - Commande: `python -c "from python.helpers.tool_policy import check_tool_policy; print(check_tool_policy('generate_image','marketing'))"`
  - Preuve attendue: decision ALLOWED/FORBIDDEN conforme
  - Critere PASS/FAIL: PASS si decision coherente
- Limites:
  - Image-only

### B-014 — Router metrics & audit sampling
- Statut: Partial
- ClaimID: C-017
- Preuves:
  - Code: `python/helpers/router/metrics.py`
  - Wiring runtime: `python/tools/call_subordinate.py` `RouterMetrics.record_decision(...)`
- Validation:
  - Commande: delegation avec router active
  - Preuve attendue: logs `[ROUTER_METRICS]`
  - Critere PASS/FAIL: PASS si logs presents
- Limites:
  - Flag router requis

### B-015 — Securite API (cle/loopback/CSRF)
- Statut: Partial
- ClaimID: C-011
- Preuves:
  - Code: `run_ui.py` `register_api_handler()`
  - Code: `python/api/api_message.py` `requires_api_key()`
- Validation:
  - Commande: appel `/api_message` sans cle
  - Preuve attendue: 401 "API key required"
  - Critere PASS/FAIL: PASS si 401
- Limites:
  - Per-handler

### B-016 — Deploiement Docker
- Statut: Partial
- ClaimID: C-012
- Preuves:
  - Code: `deploy/docker-compose.yml`
  - Code: `docker/run/docker-compose.yml`
- Validation:
  - Commande: `docker compose -f deploy/docker-compose.yml config`
  - Preuve attendue: config valide
  - Critere PASS/FAIL: PASS si sortie sans erreur
- Limites:
  - Ne prouve pas la sante runtime

### B-017 — Audit log persistant
- Statut: Unverified
- ClaimID: C-018
- Preuves:
  - Code: `deploy/docker-compose.yml` volume `evidence-audit` (config seulement)
- Validation:
  - Commande: verifier ecriture reelle dans `/app/audit`
  - Preuve attendue: fichiers d'audit presents
  - Critere PASS/FAIL: PASS si fichiers crees
- Limites:
  - Persistance non demontree par le code ; volume docker configure mais aucun code d'ecriture trouve. UNVERIFIED

### B-018 — Suivi couts/tokens
- Statut: Unverified
- ClaimID: C-019
- Preuves:
  - Code: NOT FOUND
- Validation:
  - Commande: N/A
  - Preuve attendue: N/A
  - Critere PASS/FAIL: FAIL par defaut
- Limites:
  - Aucune preuve dans le repo

### B-019 — Redaction PII automatique
- Statut: Unverified
- ClaimID: C-020
- Preuves:
  - Code: NOT FOUND
- Validation:
  - Commande: N/A
  - Preuve attendue: N/A
  - Critere PASS/FAIL: FAIL par defaut
- Limites:
  - Seulement des regles prompt

## 3. System Architecture (As-Built)
- High-level flow diagram (ASCII)
```
User Request
   |
   v
Deterministic Router (optional) ----> Criticality Router
   |                                     |
   v                                     v
Agent Delegation (profiles)          Critical Decision Gate
   |                                     |
   v                                     v
Collaborative Debate (3 rounds)      Evidence Pack + Consensus Engine
   |                                     |
   v                                     v
User Response (envelope + badges) <--- Fail-closed if insufficient
```
- Core modules map (with file paths)
  - Routing: `python/helpers/router/router.py`, `python/helpers/router/policy.py`, `python/helpers/router/metrics.py`
  - Criticality: `python/helpers/criticality_router.py`
  - Gate: `python/helpers/critical_decision_gate.py`
  - Evidence: `python/helpers/evidence.py`
  - Consensus: `python/helpers/consensus_manager.py`, `python/helpers/consensus_arbiter.py`, `python/consensus/engine.py`
  - Debate: `python/helpers/collaborative_consensus.py`, `python/tools/call_subordinate.py`
  - Legal pipeline: `python/helpers/legal_orchestrator.py`
  - Medical contract: `python/helpers/medical_contract.py`
- Runtime modes
  - `EVIDENCE_ENV`, `CONSENSUS_SIMULATION`, `OFFLINE_MODE`, `DETERMINISTIC_ROUTER_V2`

## 4. Specialized Agents Catalog (As-Built)
**legal_safe**
- Name / Role: legal-safe analysis, FR/EU only
- Inputs / Outputs: JSON `response` (prompt-defined)
- Tools allowed: prompt-defined tools
- Guardrails: sourcing required, refusal on restricted acts
- Failure modes: out-of-scope jurisdiction -> refusal
- Evidence: `agents/legal_safe/_context.md`, `agents/legal_safe/prompts/agent.system.main.role.md`, `tests/test_legal_orchestrator.py`

**medical**
- Name / Role: medical reasoning with claim-first schema
- Inputs / Outputs: JSON `structured_response` (claims + citations)
- Tools allowed: prompt-defined MCP tools
- Guardrails: patient-specific actions forbidden; FAIL_CLOSED on violations
- Failure modes: insufficient evidence -> FAIL_CLOSED
- Evidence: `agents/medical/_context.md`, `agents/medical/prompts/agent.system.main.role.md`, `python/helpers/medical_contract.py`

**researcher / finance / sales / marketing / developer / hacker / default**
- Name / Role: prompt-defined only
- Inputs / Outputs: UNVERIFIED
- Tools allowed: UNVERIFIED
- Guardrails: UNVERIFIED
- Failure modes: UNVERIFIED
- Evidence: `agents/*/_context.md` (where present)

## 5. Multi-LLM Debate (As-Built)
- Mechanics: 3 rounds; round 2 can be skipped if unanimous [C-021]
- Roles: arbiters from UI settings or defaults [C-021]
- Termination rules: fixed rounds with timeouts [C-021]
- Storage/logging: stdout only; no persistence found UNVERIFIED
- Evidence: `python/helpers/collaborative_consensus.py` `run_debate()`, `python/tools/call_subordinate.py` `_validate_with_consensus()`

## 6. Consensus / Arbitration (As-Built)
- Vote schema: APPROVE/REJECT/ABSTAIN + availability [C-005]
- Quorum rules: 2/3 effective votes; unavailable excluded [C-005]
- Weighting: none (equal weight) [C-005]
- Timeouts/retries/fallback: timeout -> INFRA_FAILURE if 0 effective votes else NO_CONSENSUS [C-005]
- Fail-closed rules: NO_CONSENSUS/INFRA_FAILURE do not approve [C-007]
- Evidence + test mapping:
  - Code: `python/helpers/consensus_manager.py`, `python/helpers/consensus_arbiter.py`, `python/consensus/engine.py`
  - Tests: `tests/test_prism_consensus.py`, `tests/test_prism_tally_quorum.py`, `test_consensus_simple.py`

## 7. Quality, Tests, and Determinism
- Test inventory + commands: see Appendix B
- Determinism controls: router hashing; arbiter temp=0 [C-002]
- Known nondeterminism sources: LLM outputs, MCP data, network timeouts UNVERIFIED

## 8. Observability & Auditability
- Logs/metrics/traces: consensus JSON logs, router metrics [C-017]
- Correlation IDs: consensus engine correlation_id [C-017]
- Audit logs & retention: in-memory + docker volume only (persistence UNVERIFIED) [C-018]
- Cost tracking: NOT FOUND / UNVERIFIED [C-019]

## 9. Security Posture
- Prompt injection defenses: deterministic router patterns [C-003]
- Tool policy / sandboxing: image-only tool policy; no sandbox found [C-015]
- PII handling: prompt minimization only; no redaction [C-020]
- Secrets hygiene: `.env.example` documents keys [C-012]
- Known gaps: no cost tracking, no retention enforcement UNVERIFIED

## 10. Deployment & Operations
- Installation steps: `docker build -f DockerfileLocal -t korev-evidence:local .` [C-012]
- Env vars: `.env.example` [C-012]
- Docker/scripts: `deploy/docker-compose.yml`, `docker/run/docker-compose.yml` [C-012]
- On-prem notes: binds to localhost (compose) [C-012]
- Constraints: provider credentials required [C-010]

## 11. Risks & Blind Spots (Devil's Advocate)
- Prompt-only controls for critical domains [C-020]
- Simulation misuse risk [C-013]
- Audit persistence unclear (volume existe, code d'ecriture UNVERIFIED) [C-018]
- Worst-case: consensus unavailable -> fail-closed -> no response [C-007]
- Mitigations: unify enforcement in code; add persistence UNVERIFIED

## 12. Commercial Extract (1 page, FR)
**What it does (verifiable)**
  - Orchestration multi-agents avec delegation et profils specialises. [C-001]
  - Consensus multi-LLM (quorum 2/3, fail-closed). [C-005]
  - Debat collaboratif 3 tours. [C-021]
  - Pipeline legal + medical avec contrats stricts. [C-008]
**Differentiators (verifiable)**
  - Routage deterministe testable. [C-002]
  - Quorum calcule sur votes effectifs. [C-005]
  - Contrats medicaux enforces. [C-008]
**Use cases (grounded)**
  - Validation de reponses critiques. [C-009]
  - Analyses sourcees avec audit trail in-memory (persistance UNVERIFIED). [C-018]
  - Cadre de confiance multi-agents. [C-001]
**Proof points (tests, metrics)**
  - Tests consensus/quorum/injection/determinisme. [C-005]
  - Logs structures + correlation_id. [C-017]
**What it does NOT do (honesty section)**
  - Exactitude factuelle garantie: UNVERIFIED
  - Audit logs persistants: UNVERIFIED
  - Redaction PII automatique: UNVERIFIED
  - Suivi couts/tokens: UNVERIFIED

## 13. CTO Brief (1 page, EN)
**Current state assessment**
  - Strong: criticality routing + consensus engine with tests. [C-004]
  - Medium: legal pipeline depends on external index. [C-009]
  - Weak/unknown: cost tracking, audit retention, PII redaction. UNVERIFIED
**Technical debt hotspots**
  - Large core modules (legal_orchestrator, criticality_router). [C-009]
  - Prompt-defined constraints not enforced by runtime. UNVERIFIED
**30/60/90 day priorities**
  - 30 days: inventory runtime wiring; add metrics persistence. UNVERIFIED
  - 60 days: enforce policy in code; integrate PII redaction. UNVERIFIED
  - 90 days: harden logging/retention; add cost tracking. UNVERIFIED
**Hiring expectations & ownership boundaries**
  - Ownership of consensus/guardrails, routing, legal/medical pipelines. [C-001]
  - Security ownership for injection/PII enforcement. [C-003]

## Appendix A — Evidence Index
| Claim ID | BrickID | Evidence links (file path + function + test) | Confidence | Notes |
|---|---|---|---|---|
| C-001 | B-010 | `python/tools/call_subordinate.py`; `agents/*/_context.md` | Medium | Multi-agent orchestration |
| C-002 | B-001 | `python/helpers/router/router.py`; `tests/test_router_determinism.py` | High | Flag-gated |
| C-003 | B-002 | `python/helpers/router/router.py`; `tests/test_injection_handling.py` | High | Router-dependent |
| C-004 | B-003 | `python/tools/call_subordinate.py`; `tests/test_criticality_router.py` | High | Wired |
| C-005 | B-006 | `python/helpers/consensus_manager.py`; `tests/test_prism_tally_quorum.py` | High | Quorum 2/3 |
| C-006 | B-005 | `python/helpers/evidence.py`; `tests/test_final_output_claim_integrity.py` | Medium | Evidence pack |
| C-007 | B-004 | `python/helpers/consensus_manager.py` timeout/no_consensus | Medium | Gate wiring unclear |
| C-008 | B-012 | `python/helpers/medical_contract.py` | High | Contract only |
| C-009 | B-011 | `python/helpers/legal_orchestrator.py`; `tests/test_legal_orchestrator.py` | Medium | External index |
| C-010 | B-007 | `python/helpers/consensus_arbiter.py`; `python/helpers/llm_provider.py` | Medium | Provider required |
| C-011 | B-015 | `run_ui.py`; `python/api/api_message.py` | Medium | Per-handler |
| C-012 | B-016 | `deploy/docker-compose.yml`; `docker/run/docker-compose.yml`; `.env.example` | Medium | Config only |
| C-013 | B-008 | `python/helpers/consensus_arbiter.py` `load_consensus_config()` | Medium | No test |
| C-014 | B-010 | `python/tools/call_subordinate.py` `_validate_with_consensus()` | Medium | No test |
| C-015 | B-013 | `python/helpers/tool_policy.py` | Medium | Image-only |
| C-016 | B-013 | `python/helpers/response_contract.py` | Low | Wiring unclear |
| C-017 | B-014 | `python/helpers/router/metrics.py` | Medium | Router-dependent |
| C-018 | B-017 | `python/helpers/consensus_arbiter.py` `_audit_log`; `deploy/docker-compose.yml` | Low | Persistence UNVERIFIED |
| C-019 | B-018 | NOT FOUND | Low | UNVERIFIED |
| C-020 | B-019 | NOT FOUND | Low | UNVERIFIED |
| C-021 | B-009 | `python/helpers/collaborative_consensus.py` `run_debate()` | Medium | Collaborative debate 3 rounds |

## Appendix B — Commands & Repro Checklist
- How to run
  - `python run_ui.py`
  - `python run_tunnel.py`
- How to verify debate/consensus
  - `python -m pytest tests/test_prism_consensus.py -v`
  - `python -m pytest tests/test_prism_tally_quorum.py -v`
  - `python test_consensus_simple.py`
- How to generate logs/metrics proof
  - Enable logging and run router/consensus tests; inspect stdout
  - `make audit-verify`

<!-- END AUDIT -->
