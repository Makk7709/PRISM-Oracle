> ⚠️ **DOCUMENT ARCHIVÉ**
> **Statut** : Historique
> **Date d'archivage** : 2026-05-31
> **Raison** : Inventaire des chemins consensus daté 2026-01-25, antérieur au réalignement du chemin critique (mai 2026).
> **Remplacé par** : `docs/audit/critical_request_path_map.md`
> **Ne pas utiliser comme référence opérationnelle active.**

# Consensus Paths Inventory

> **Generated**: 2026-01-25
> **Purpose**: Document all paths through which a user query can produce a response, identifying choke points for consensus enforcement.

---

## 1. Entry Points (User Query Reception)

### 1.1 HTTP API Entry
- **File**: `python/api/message.py`
- **Class**: `Message(ApiHandler)`
- **Method**: `process()` → `communicate()` → `context.communicate()`
- **Flow**:
  ```
  HTTP POST /message → Message.process() → Message.communicate()
    → context.communicate(UserMessage) → AgentContext._process_chain()
    → agent.monologue()
  ```

### 1.2 Agent Context Communication
- **File**: `agent.py`
- **Class**: `AgentContext`
- **Method**: `communicate(msg: UserMessage)`
- **Flow**:
  ```
  communicate() → run_task(_process_chain)
    → agent.hist_add_user_message(msg)
    → agent.monologue()
  ```

---

## 2. Processing Paths (Query → Response)

### 2.1 Main Agent Loop
- **File**: `agent.py`
- **Class**: `Agent`
- **Method**: `monologue()`
- **Flow**:
  ```
  monologue():
    while True:
      prepare_prompt() → call_chat_model() → process_tools()
        if tools_result: return tools_result  # EXIT POINT
  ```

### 2.2 Tool Processing
- **File**: `agent.py`
- **Method**: `process_tools(msg)`
- **Flow**:
  ```
  process_tools():
    tool_request = extract_tools.json_parse_dirty(msg)
    tool = get_tool() or mcp_tool
    response = tool.execute()
    if response.break_loop: return response.message  # EXIT POINT
  ```

---

## 3. Exit Points (Response Emission)

### 3.1 Response Tool (Primary Exit)
- **File**: `python/tools/response.py`
- **Class**: `Response(Tool)`
- **Method**: `execute()`
- **Code**:
  ```python
  async def execute(self, **kwargs):
      return Response(message=self.args["text"], break_loop=True)
  ```
- **⚠️ CRITICAL**: This is where ALL final responses exit. **MUST be gated**.

### 3.2 Subordinate Delegation Return
- **File**: `python/tools/call_subordinate.py`
- **Class**: `Delegation(Tool)`
- **Method**: `execute()`
- **Code**:
  ```python
  result = await subordinate.monologue()
  return Response(message=result, break_loop=False)  # Returns to superior
  ```
- **✅ ALREADY GATED**: Consensus validation added for critical profiles.

### 3.3 Superior Chain Return
- **File**: `agent.py`
- **Method**: `_process_chain()`
- **Code**:
  ```python
  response = await agent.monologue()
  if superior:
      response = await self._process_chain(superior, response, False)
  return response
  ```
- **Note**: Bubbles up through hierarchy.

---

## 4. Bypass Paths (Must Be Closed)

### 4.1 Direct Response Without Tool
- **Risk**: Agent could return without using `response` tool (malformed response)
- **Mitigation**: Already handled - misformat warning added to history
- **Status**: ✅ OK

### 4.2 Direct Research Tool Call
- **File**: `python/helpers/research_executor.py`
- **Risk**: Direct call to executor bypasses consensus
- **Mitigation**: Research executor must delegate to `ResearchConsensusIntegration`
- **Status**: ⚠️ NEEDS WIRING

### 4.3 MCP Tool Direct Execution
- **File**: `python/helpers/mcp_handler.py`
- **Risk**: MCP tools can return data without consensus
- **Mitigation**: Critical domain detection should apply to MCP results
- **Status**: ⚠️ NEEDS WIRING

---

## 5. Choke Points (Where Gate MUST Be Applied)

| ID | Location | Description | Priority |
|----|----------|-------------|----------|
| CP1 | `response.py` | Final answer emission | 🔴 CRITICAL |
| CP2 | `call_subordinate.py` | Delegation to critical agents | ✅ DONE |
| CP3 | `research_executor.py` | Research results for critical domains | 🔴 CRITICAL |
| CP4 | `AgentContext.communicate()` | Entry point detection | 🟡 HIGH |

---

## 6. Required Gate Insertions

### 6.1 Response Tool Gate (CP1)
```python
# In python/tools/response.py
async def execute(self, **kwargs):
    text = self.args.get("text", "")
    
    # ═══ CRITICAL DECISION GATE ═══
    from python.helpers.critical_decision_gate import validate_final_output
    assessment, validated_text = await validate_final_output(
        output=text,
        agent_profile=self.agent.config.profile,
        context_metadata={"agent_name": self.agent.agent_name},
    )
    
    if not assessment.can_emit:
        return Response(message=assessment.fail_closed_response, break_loop=True)
    # ═══════════════════════════════
    
    return Response(message=validated_text, break_loop=True)
```

### 6.2 Entry Point Gate (CP4)
```python
# In agent.py AgentContext.communicate()
def communicate(self, msg: UserMessage):
    # ═══ CRITICAL DECISION GATE ═══
    from python.helpers.critical_decision_gate import enforce_or_route
    assessment = enforce_or_route(
        query=msg.message,
        agent_profile=self.agent0.config.profile,
    )
    # Store assessment for downstream use
    self.set_data("_gate_assessment", assessment.to_dict())
    # ═══════════════════════════════
    
    # ... rest of communicate()
```

---

## 7. Summary

| Path Type | Count | Gated |
|-----------|-------|-------|
| Entry Points | 1 | ⚠️ Pending |
| Processing Paths | 2 | N/A |
| Exit Points | 3 | 1/3 ✅ |
| Bypass Paths | 3 | 0/3 ⚠️ |
| Choke Points | 4 | 1/4 ✅ |

**Next Steps**:
1. Create `CriticalDecisionGate` module
2. Wire CP1 (response tool)
3. Wire CP4 (entry point)
4. Wire CP3 (research executor)
