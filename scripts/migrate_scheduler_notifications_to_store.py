#!/usr/bin/env python3
"""
Idempotent migration from legacy JSON/in-memory scheduler-notifications
to transactional store backend (Redis).
"""

import argparse
import json
import os
from pathlib import Path

from python.helpers.files import get_abs_path, read_file
from python.helpers.persistence.stores import JsonTaskStore, get_task_store


def migrate_tasks(dry_run: bool = False) -> dict[str, int]:
    src = JsonTaskStore(path=get_abs_path("tmp/scheduler", "tasks.json"))
    dst = get_task_store()
    tasks = src.list_tasks()
    migrated = 0
    quarantined = 0
    for task in tasks:
        username = task.get("username")
        organization = task.get("organization")
        workspace = task.get("workspace")
        if not username or not organization or not workspace:
            task["state"] = "disabled"
            reason = "task_missing_scope_during_migration"
            task["quarantine_reason"] = task.get("quarantine_reason") or reason
            prev = task.get("last_result") or ""
            task["last_result"] = f"{prev}\n---\nBLOCKED_SCOPE: {reason}".strip() if prev else f"BLOCKED_SCOPE: {reason}"
            quarantined += 1
        if not dry_run:
            dst.put_task(task)
        migrated += 1
    return {"migrated": migrated, "quarantined": quarantined}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-backend", default="redis")
    parser.add_argument("--backup-file", default="")
    args = parser.parse_args()
    current_backend = os.environ.get("KOREV_PERSISTENCE_BACKEND", "json").strip().lower()
    if current_backend != args.require_backend:
        raise SystemExit(
            f"Refusing migration: KOREV_PERSISTENCE_BACKEND={current_backend!r}, expected {args.require_backend!r}"
        )
    if args.backup_file:
        src = JsonTaskStore(path=get_abs_path("tmp/scheduler", "tasks.json"))
        backup_payload = {"tasks": src.list_tasks()}
        Path(args.backup_file).write_text(json.dumps(backup_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    result = migrate_tasks(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
