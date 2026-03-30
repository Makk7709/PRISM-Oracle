#!/usr/bin/env python3
"""
One-shot idempotent migration: normalize organization fields in all persisted data.

Targets:
- /app/tmp/chats/*/chat.json   (chat contexts)
- /app/tmp/scheduler/tasks.json (scheduled tasks)

For each object:
1. Read current `organization` value
2. Normalize to canonical slug via normalize_org_id()
3. If value changed, write back
4. If `organization` is missing, attempt to infer from `username` → users.json mapping
5. Log every transformation

Usage:
    python scripts/normalize_org_migration.py [--dry-run]

Safe to run multiple times (idempotent).
"""

import json
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers.organization import normalize_org_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("org_migration")

DRY_RUN = "--dry-run" in sys.argv

CHATS_DIR = os.environ.get("CHATS_DIR", "/app/tmp/chats")
TASKS_FILE = os.environ.get("TASKS_FILE", "/app/tmp/scheduler/tasks.json")
USERS_FILE = os.environ.get("USERS_FILE", "/app/deploy/users.json")


def load_user_org_map() -> dict[str, str]:
    """Build username → normalized_org_id mapping from users.json."""
    mapping: dict[str, str] = {}
    if not os.path.exists(USERS_FILE):
        log.warning("users.json not found at %s", USERS_FILE)
        return mapping
    with open(USERS_FILE) as f:
        data = json.load(f)
    for username, info in data.get("users", {}).items():
        org_display = info.get("organization", "")
        if org_display:
            mapping[username] = normalize_org_id(org_display)
    return mapping


def migrate_chats(user_org: dict[str, str]) -> dict:
    stats = {"total": 0, "normalized": 0, "inferred": 0, "already_ok": 0, "orphan": 0, "errors": 0}
    if not os.path.isdir(CHATS_DIR):
        log.warning("Chats dir not found: %s", CHATS_DIR)
        return stats

    for ctx_id in sorted(os.listdir(CHATS_DIR)):
        chat_file = os.path.join(CHATS_DIR, ctx_id, "chat.json")
        if not os.path.isfile(chat_file):
            continue
        stats["total"] += 1
        try:
            with open(chat_file) as f:
                data = json.load(f)
        except Exception as e:
            log.error("Failed to read %s: %s", chat_file, e)
            stats["errors"] += 1
            continue

        original_org = data.get("organization")
        username = data.get("username")
        normalized = normalize_org_id(original_org) if original_org else ""
        changed = False

        if original_org and normalized and normalized != original_org:
            log.info("NORMALIZE chat=%s org '%s' → '%s'", ctx_id, original_org, normalized)
            data["organization"] = normalized
            changed = True
            stats["normalized"] += 1
        elif original_org and normalized == original_org:
            stats["already_ok"] += 1
        elif not original_org and username and username in user_org:
            inferred = user_org[username]
            log.info("INFER chat=%s username=%s → org='%s'", ctx_id, username, inferred)
            data["organization"] = inferred
            changed = True
            stats["inferred"] += 1
        else:
            log.warning("ORPHAN chat=%s username=%s org=%s", ctx_id, username, original_org)
            stats["orphan"] += 1

        if changed and not DRY_RUN:
            tmp = chat_file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, chat_file)

    return stats


def migrate_tasks(user_org: dict[str, str]) -> dict:
    stats = {"total": 0, "normalized": 0, "inferred": 0, "already_ok": 0, "orphan": 0, "errors": 0}
    if not os.path.isfile(TASKS_FILE):
        log.warning("Tasks file not found: %s", TASKS_FILE)
        return stats

    try:
        with open(TASKS_FILE) as f:
            tasks_data = json.load(f)
    except Exception as e:
        log.error("Failed to read tasks.json: %s", e)
        stats["errors"] += 1
        return stats

    tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("tasks", [])
    any_changed = False

    for task in tasks:
        stats["total"] += 1
        original_org = task.get("organization")
        username = task.get("username")
        normalized = normalize_org_id(original_org) if original_org else ""

        if original_org and normalized and normalized != original_org:
            log.info("NORMALIZE task=%s org '%s' → '%s'", task.get("uuid", "?"), original_org, normalized)
            task["organization"] = normalized
            any_changed = True
            stats["normalized"] += 1
        elif original_org and normalized == original_org:
            stats["already_ok"] += 1
        elif not original_org and username and username in user_org:
            inferred = user_org[username]
            log.info("INFER task=%s username=%s → org='%s'", task.get("uuid", "?"), username, inferred)
            task["organization"] = inferred
            any_changed = True
            stats["inferred"] += 1
        else:
            log.warning("ORPHAN task=%s username=%s org=%s", task.get("uuid", "?"), username, original_org)
            stats["orphan"] += 1

    if any_changed and not DRY_RUN:
        tmp = TASKS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, TASKS_FILE)

    return stats


def main():
    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log.info("=== Organization Migration (%s) ===", mode)
    log.info("Timestamp: %s", datetime.now(timezone.utc).isoformat())

    user_org = load_user_org_map()
    log.info("User→Org mapping: %s", user_org)

    log.info("--- Migrating chats ---")
    chat_stats = migrate_chats(user_org)
    log.info("Chat stats: %s", chat_stats)

    log.info("--- Migrating tasks ---")
    task_stats = migrate_tasks(user_org)
    log.info("Task stats: %s", task_stats)

    log.info("=== Migration Complete (%s) ===", mode)
    log.info("REPORT:")
    log.info("  Chats: %d total, %d normalized, %d inferred, %d already_ok, %d orphan, %d errors",
             chat_stats["total"], chat_stats["normalized"], chat_stats["inferred"],
             chat_stats["already_ok"], chat_stats["orphan"], chat_stats["errors"])
    log.info("  Tasks: %d total, %d normalized, %d inferred, %d already_ok, %d orphan, %d errors",
             task_stats["total"], task_stats["normalized"], task_stats["inferred"],
             task_stats["already_ok"], task_stats["orphan"], task_stats["errors"])

    collisions = set()
    for orig, norm in [("DICA France", "dica-france"), ("Korev AI", "korev-ai"), ("Scriptoura", "scriptoura")]:
        if normalize_org_id(orig) != norm:
            collisions.add((orig, norm))
    if collisions:
        log.error("COLLISION DETECTED: %s", collisions)
    else:
        log.info("No slug collisions detected.")


if __name__ == "__main__":
    main()
