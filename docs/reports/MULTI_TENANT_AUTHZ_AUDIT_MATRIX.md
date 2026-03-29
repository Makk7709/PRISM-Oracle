# Multi-Tenant Authorization Audit Matrix

## Scope

This audit covers API handlers, context/task access, scheduler operations, polling, and file/workspace operations.

## Risk Matrix (Surface -> Policy -> Risk)

| Surface | Resource Keys | Enforced Policy | Current Risk |
|---|---|---|---|
| `poll` | `context`, `context_id` | `can_access_context`, `can_access_task` | Low |
| `chat_remove` | `context` | `_authorize_context_access` | Low |
| `chat_create` | `current_context`, `new_context` | `use_context` on both source/target | Low |
| `chat_export`, `history_get`, `chat_reset`, `ctx_window_get`, `message` | `context` | `use_context` centralized check | Low |
| `scheduler_task_list` | `task.uuid`, `task.organization`, `task.username` | `can_access_task` | Low |
| `scheduler_task_run/update/delete` | `task_id` | `_authorize_task_access` | Low |
| `scheduler_task_create` | new task attrs | write-bound to current user/org | Low |
| `get/upload/delete/download work dir file` | `path`, workspace path | `_authorize_workspace_access` + path safety | Low |
| `file_info` | `path` | workspace-scoped resolution + path safety | Low |
| `chat_load` | imported chat payloads | re-owned to importer (user/org/workspace) | Medium (import abuse mitigated) |
| API-key endpoints (`api_message`, `api_log_get`, `api_reset_chat`, `api_terminate_chat`) | `context_id` | now routed via `use_context` | Medium (depends on API key custody) |
| backup / restore / maintenance endpoints | archive paths, restore payloads | admin gate in route wrapper | Medium (high impact, admin-only) |

## Key Findings Fixed

1. Removed distributed ad-hoc ownership checks in critical endpoints.
2. Enforced deterministic policy through centralized authorization module.
3. Removed permissive owner adoption behavior for legacy unscoped contexts in authenticated flows.
4. Closed direct `AgentContext.use(...)` IDOR paths in multiple handlers.
5. Hardened file download/info paths to enforce workspace boundaries.

## Residual Risks

1. API-key endpoints are trusted-channel interfaces and remain sensitive to API-key leakage.
2. Backup/restore operations are high-impact by design; they are admin-gated but should move behind stronger operator controls (MFA/JIT approvals).
3. Existing historical records without owner/org are fail-closed in authenticated flows; operational migration must keep data quality high.

## Recommended Next Actions

1. Rotate MCP/API keys and enforce short-lifetime tokens.
2. Add rate-limit tiers per endpoint class (read vs destructive).
3. Add canary tests in CI for every new API handler requiring explicit policy assertion.
