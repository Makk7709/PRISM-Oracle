# Persistent Identity Migration Plan (Post `users.json`)

## Target Model

### `organizations`

- `id` (PK, text)
- `name` (unique)
- `created_at` (timestamp)

### `users`

- `id` (PK, text)
- `username` (unique, not null)
- `password_hash` (not null)
- `system_role` (`admin` / `user`)
- `status` (`active` / `deleted`)
- `created_at`
- `updated_at`

### `memberships`

- `id` (PK, text)
- `user_id` (FK `users.id`, on delete cascade)
- `organization_id` (FK `organizations.id`, on delete cascade)
- `org_role` (`OWNER` / `MEMBER`)
- Unique (`user_id`, `organization_id`)

### `chats`

- `id` (PK, text)
- `owner_user_id` (FK `users.id`)
- `organization_id` (FK `organizations.id`)
- `visibility` (`PRIVATE` / `ORG`)
- `created_at`
- `updated_at`

### `tasks`

- `id` (PK, text)
- `chat_id` (nullable FK `chats.id`)
- `owner_user_id` (FK `users.id`)
- `organization_id` (FK `organizations.id`)
- `state`
- `type`
- `payload_json`
- `created_at`
- `updated_at`

## Integrity Constraints

1. `memberships.org_role` constrained to enum-like CHECK.
2. `chats.organization_id` must equal owner's membership organization.
3. `tasks.organization_id` must equal owner membership organization.
4. Foreign keys enabled + cascading delete rules for account purge.
5. Partial unique index to enforce single OWNER per organization if desired.

## Migration Strategy

1. Create DB schema alongside legacy `users.json`.
2. Import users from `users.json` -> `users`, `organizations`, `memberships`.
3. Backfill `tmp/chats/*/chat.json` and scheduler tasks into `chats`/`tasks`.
4. Enable dual-read (DB primary, JSON fallback read-only).
5. Enable DB write path behind feature flag.
6. Remove JSON write path after burn-in and backups validated.

## Rollback Plan

1. Keep `users.json` snapshots before each migration step.
2. Keep idempotent export script from DB to `users.json` fallback format.
3. Feature flag `AUTH_BACKEND=json|db` for instant rollback.
4. Preserve data snapshots for chats/tasks before backfill and after.

## Known Blockers

1. Current runtime stores chat/task payloads mostly as file JSON; requires storage abstraction.
2. Existing API-key endpoints have no user principal model and need service-account identities.
3. Long-running task reconciliation must map deterministic task IDs across stores.
