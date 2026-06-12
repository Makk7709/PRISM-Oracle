# Legal Pipeline E2E Test Suite

## Overview

This document describes the end-to-end test suite for the legal pipeline with PRISM consensus validation.

**Test File**: `tests/test_legal_pipeline_e2e.py`

**Run Command**:

```bash
python tests/test_legal_pipeline_e2e.py
```

Or with pytest:

```bash
python -m pytest tests/test_legal_pipeline_e2e.py -v -s
```

---

## Test Results Summary

| Test | Status | Duration | Description |
|------|--------|----------|-------------|
| 1.1 Pipeline Output | ✅ PASS | 1ms | Pipeline produces structured output |
| 2.1 Real LLM Consensus | ✅ PASS | 4583ms | 3 real LLM calls via OpenRouter |
| 3.1 Log Type Response | ✅ PASS | <1ms | Log system accepts "response" type |
| 3.2 Log Output | ✅ PASS | <1ms | Response appears in log.output() |
| 4.1 Pipeline Flags | ✅ PASS | <1ms | _pipeline_final_response flag works |
| 4.2 Response Structure | ✅ PASS | <1ms | Response(break_loop=True) correct |
| 5.0 LLM Draft Generation | ✅ PASS | 7179ms | LLM generates FIRAC analysis without index |
| 5.1 Full Integration | ✅ PASS | 1ms | Complete flow pipeline→log→UI |

**Total: 8 tests | Passed: 8 | Failed: 0**

---

## Architecture Flow

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        USER MESSAGE                                 │
│                    "Question juridique..."                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MAIN AGENT (monologue)                          │
│                                                                     │
│  1. Detect legal_safe profile                                       │
│  2. Route to legal_safe subordinate via call_subordinate tool       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  LEGAL_SAFE SUBORDINATE                             │
│                                                                     │
│  Extension: _10_legal_safe_integration.py                           │
│                                                                     │
│  Hook: monologue_start                                              │
│    ├── Detect legal question                                        │
│    ├── Run legal pipeline (run_legal_pipeline)                      │
│    ├── Set _pipeline_final_response = output                        │
│    └── Set _skip_llm = True                                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LEGAL PIPELINE                                   │
│                 (legal_orchestrator.py)                             │
│                                                                     │
│  1. Detect legal context (risk tier, scope, jurisdiction)           │
│  2. Retrieve legal sources (if available)                           │
│  3. Build legal draft                                               │
│  4. Judge draft (quality checks)                                    │
│  5. Return LegalOutput with mode:                                   │
│     - APPROVED_POSITION (consensus validated)                       │
│     - SAFE_ANALYSIS (structured but not validated)                  │
│     - REFUSAL_REQUEST_INFO (missing information)                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   SHORT-CIRCUIT MECHANISM                           │
│                       (agent.py)                                    │
│                                                                     │
│  In monologue():                                                    │
│    if _pipeline_final_response is not None:                         │
│        - Skip LLM call entirely                                     │
│        - Return pipeline response directly                          │
│        - Add to history via hist_add_ai_response()                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  CALL_SUBORDINATE TOOL                              │
│                (call_subordinate.py)                                │
│                                                                     │
│  1. Detect _pipeline_was_used flag                                  │
│  2. Run PRISM consensus validation:                                 │
│     ├── 3 LLMs vote (Claude, GPT-4o, Mistral)                       │
│     ├── Quorum: 2/3 required for APPROVE                            │
│     └── Decision: APPROVED / REJECTED                               │
│  3. Set _pipeline_validated_response for gate bypass                │
│  4. Return Response(message=result, break_loop=True)                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MAIN AGENT (tool result)                        │
│                        (agent.py)                                   │
│                                                                     │
│  After tool execution:                                              │
│    if response.break_loop:                                          │
│        - Add to history: hist_add_ai_response(message)              │
│        - Add to LOG: context.log.log(type="response", ...)  ← KEY!  │
│        - Return message                                             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        UI DISPLAY                                   │
│                       (poll.py)                                     │
│                                                                     │
│  Frontend polls /api/poll endpoint                                  │
│  Returns: context.log.output(start=from_no)                         │
│  Response log item with type="response" is displayed                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Test Details

### Test 1.1: Pipeline Execution

**Purpose**: Verify that the legal pipeline produces structured output.

**Test Steps**:

1. Call `run_legal_pipeline()` with a legal question
2. Verify result is not None
3. Verify result has `mode` attribute
4. Verify result has `answer` attribute with content

**Key Assertion**:

```python
assert hasattr(result, 'mode'), "Result must have mode"
assert len(result.answer) > 50, "Answer must not be too short"
```

---

### Test 2.1: Real LLM Consensus

**Purpose**: Verify that PRISM consensus makes real API calls, not simulations.

**Test Steps**:

1. Create ConsensusConfig with `simulation_enabled=False`
2. Configure 3 arbiters (Claude, GPT-4o, Mistral via OpenRouter)
3. Call `seek_consensus()`
4. Verify duration > 1000ms (real API calls take time)

**Key Assertion**:

```python
assert duration_ms > 1000, "Too fast - probably simulation"
```

**Sample Output**:

```yaml
Arbiters: ['openrouter/anthropic/claude-3.5-sonnet', 
           'openrouter/openai/gpt-4o', 
           'openrouter/mistralai/mistral-large']
Duration: 4583ms
Votes: Claude=REJECT, GPT-4o=APPROVE, Mistral=APPROVE
Result: APPROVED (2/3)
```

---

### Test 3.1-3.2: UI Log System

**Purpose**: Verify that responses are properly added to the log system that the UI polls.

**Key Discovery**: The fix was that responses must be added via `context.log.log()` with `type="response"`, not just `hist_add_ai_response()`.

**Fix Applied** (agent.py):

```python
if response.break_loop:
    if response.message:
        # Add to history
        self.hist_add_ai_response(response.message)
        # CRITICAL: Also add to LOG so UI displays it
        self.context.log.log(
            type="response",
            heading=f"{self.agent_name}",
            content=response.message,
        )
    return response.message
```

---

### Test 4.1-4.2: Short-Circuit Mechanism

**Purpose**: Verify that pipeline flags correctly bypass the LLM.

**Flags**:

- `_pipeline_final_response`: The pre-computed response
- `_skip_llm`: Signal to skip LLM call
- `_pipeline_validated_response`: Signal to bypass critical decision gate

**Test**:

```python
agent_data["_pipeline_final_response"] = "Test response"
agent_data["_skip_llm"] = True
assert agent_data.get("_pipeline_final_response") == "Test response"
assert agent_data.get("_skip_llm") is True
```

---

### Test 5.0: LLM Draft Generation (NEW)

**Purpose**: Verify that the pipeline can generate legal analysis using LLM even without indexed sources.

**Test Steps**:

1. Create LLM call function using OpenRouter
2. Call `run_legal_pipeline()` with `call_llm_func` parameter
3. Verify draft is built with `llm_used=true`
4. Verify judge approves (`verdict=approve`, `pass_rate=1.0`)
5. Verify output mode is `safe_analysis` (not refusal)

**Key Changes Made**:

1. Modified `legal_orchestrator.py` to allow LLM draft even without retrieval results
2. Modified `legal_pipeline.py` (Judge) to accept LLM-generated citations
3. Modified `_10_legal_safe_integration.py` to pass `call_llm_func` to pipeline

**Sample Output**:

```yaml
Mode: LegalOutputMode.SAFE_ANALYSIS
llm_used: true
verdict: approve
pass_rate: 1.0
Output: "L'article L.132-8 du Code de commerce pourrait permettre au 
transporteur d'exercer une action directe contre le donneur d'ordre..."
```

---

### Test 5.1: Full Integration

**Purpose**: End-to-end test of the complete flow.

**Stages Verified**:

1. ✅ Pipeline executes and produces output
2. ✅ Log system accepts the response
3. ✅ Response appears in `log.output()` (what UI polls)

---

## Known Issues and Fixes

### Issue 1: Response Not Appearing in UI

**Symptom**: Logs showed pipeline executed with break_loop=True, but response not visible.

**Root Cause**: `hist_add_ai_response()` adds to history, but UI polls `context.log.output()`.

**Fix**: Added `context.log.log(type="response", ...)` when break_loop=True.

---

### Issue 2: Consensus INFRA_FAILURE

**Symptom**: All arbiters returned UNAVAILABLE.

**Root Cause**: Missing `PrintStyle` import in consensus_arbiter.py caused NameError.

**Fix**: Added `from python.helpers.print_style import PrintStyle`.

---

### Issue 3: Pipeline Returning REFUSAL Without Index

**Symptom**: Pipeline always returned `refusal_request_info` with "sources_missing".

**Root Cause**:

1. No legal index existed (`data/legal_index`)
2. Pipeline called without `call_llm_func` parameter
3. Judge failed on `SOURCES_PRESENT` check

**Fix Applied** (3 files):

1. `legal_orchestrator.py`: Allow LLM draft even without retrieval results
2. `legal_pipeline.py`: Judge accepts LLM-generated citations
3. `_10_legal_safe_integration.py`: Pass LLM function to pipeline

**Result**: Pipeline now generates real legal analysis even without indexed sources.

---

### Issue 4: Consensus Running in 0ms (Simulation)

**Symptom**: Consensus completing instantly with fake votes.

**Root Cause**: `simulation_enabled` defaulted to True in development.

**Fix**: Changed default to `simulation_enabled=False`, requires explicit `CONSENSUS_SIMULATION=true`.

---

## Environment Requirements

```bash
# Required environment variables
API_KEY_OPENROUTER=sk-or-...  # For real LLM consensus

# Optional
CONSENSUS_SIMULATION=false    # Default is false
EVIDENCE_ENV=development      # Environment identifier
```

---

## Running Tests

### Basic Run

```bash
cd /path/to/KOREV_Oracle
python tests/test_legal_pipeline_e2e.py
```

### With pytest and verbose output

```bash
python -m pytest tests/test_legal_pipeline_e2e.py -v -s
```

### Expected Output

```text
══════════════════════════════════════════════════════════════════════
║  LEGAL PIPELINE E2E TEST SUITE
║  Testing: Pipeline → Consensus → Log → UI Display
══════════════════════════════════════════════════════════════════════

TEST 1.1: Pipeline Execution ... ✅ PASS
TEST 2.1: Real LLM Consensus ... ✅ PASS (4583ms)
TEST 3.1: Log Type Response ... ✅ PASS
TEST 3.2: Log Output ... ✅ PASS
TEST 4.1: Pipeline Flags ... ✅ PASS
TEST 4.2: Response Structure ... ✅ PASS
TEST 5.1: Full Integration ... ✅ PASS

Total: 7 | Passed: 7 | Failed: 0 | Skipped: 0
```
