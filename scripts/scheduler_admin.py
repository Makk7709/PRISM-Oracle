#!/usr/bin/env python3
"""Operator CLI for the KOREV Evidence task scheduler.

This tool is the last-resort administration path for the scheduler. It is
intended to be used from the OVH backend container (``docker exec ...``) to
recover from situations where the REST API cannot administrate tasks:

  * legacy tasks quarantined because their scope is missing
    (``BLOCKED_SCOPE: task_missing_*``) — the REST API refuses to update or
    delete them because the authorization policy fails closed on missing
    ``organization``.
  * orphan tasks whose owner user or organization has been purged from
    ``users.json`` — they pollute every reload and can never execute.
  * tasks stuck in ``RUNNING`` after a backend crash: ``running_since`` is
    older than the configured TTL, but the normal recovery path didn't
    trigger yet (e.g. before the backend restarts).

Usage::

    python -m scripts.scheduler_admin list [--state disabled] [--quarantined]
    python -m scripts.scheduler_admin rescope --task-uuid UUID \
        --username U --organization O --workspace W \
        --operator OPERATOR --apply
    python -m scripts.scheduler_admin purge-orphans --operator OPERATOR --apply
    python -m scripts.scheduler_admin unstick --operator OPERATOR --apply

All mutating commands default to ``--dry-run``. Use ``--apply`` to write to
disk. Every operation emits a JSON report on stdout and a
``log_security_event`` for audit traceability.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# Ensure project root on path when invoked as a script.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from python.helpers.persistence.stores import JsonTaskStore  # noqa: E402
from python.helpers.task_scheduler import (  # noqa: E402
    TaskState,
    _get_run_ttl_seconds,
    _strip_blocked_scope_from_last_result,
)

try:
    from python.security.security_audit import log_security_event  # noqa: E402
except Exception:  # pragma: no cover - legacy deployments without audit module
    def log_security_event(**kwargs):
        return None


DEFAULT_TASKS_FILE = "tmp/scheduler/tasks.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_user_manager():
    """Best-effort load of the USER_MANAGER for orphan detection.

    Returns None when users.json cannot be located or parsed; callers must
    handle the ``None`` case by refusing to purge rather than assuming every
    user is an orphan.
    """
    candidates = [
        os.environ.get("KOREV_USERS_JSON"),
        str(_PROJECT_ROOT / "deploy" / "users.json"),
        str(_PROJECT_ROOT / "users.json"),
        "/app/deploy/users.json",
        "/app/users.json",
    ]
    for path in candidates:
        if not path:
            continue
        try:
            if not Path(path).exists():
                continue
        except OSError:
            continue
        try:
            from python.helpers.user_manager import UserManager

            return UserManager(users_json_path=path, strict=False)
        except Exception:
            continue
    return None


def _open_store(tasks_file: str) -> JsonTaskStore:
    """Return a JsonTaskStore bound to the given tasks.json path.

    The CLI MUST route every read/write through JsonTaskStore so that the
    thread lock and (future) flock semantics match the in-process scheduler.
    Writing directly with ``Path.write_text`` would race with the job_loop
    ticks that run every 15s in production.
    """
    Path(tasks_file).parent.mkdir(parents=True, exist_ok=True)
    return JsonTaskStore(path=tasks_file)


def _read_tasks(tasks_file: str) -> list[dict[str, Any]]:
    return _open_store(tasks_file).list_tasks()


def _write_tasks(tasks_file: str, tasks: list[dict[str, Any]]) -> None:
    _open_store(tasks_file).put_tasks(tasks)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _diagnose(task: dict[str, Any]) -> str:
    state = task.get("state")
    if state == TaskState.RUNNING.value:
        return "running"
    if state == TaskState.DISABLED.value and (
        (task.get("last_result") or "").startswith("BLOCKED_SCOPE")
        or task.get("quarantine_reason")
    ):
        return "quarantined_scope"
    if state == TaskState.DISABLED.value:
        return "disabled_manual"
    if state == TaskState.ERROR.value:
        return "error"
    return "healthy"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_list(
    *,
    tasks_file: str,
    state: Optional[str] = None,
    quarantined_only: bool = False,
) -> dict[str, Any]:
    tasks = _read_tasks(tasks_file)
    out: list[dict[str, Any]] = []
    for task in tasks:
        diagnosis = _diagnose(task)
        if state is not None and task.get("state") != state:
            continue
        if quarantined_only and diagnosis != "quarantined_scope":
            continue
        out.append({
            "uuid": task.get("uuid"),
            "name": task.get("name"),
            "state": task.get("state"),
            "username": task.get("username"),
            "organization": task.get("organization"),
            "workspace": task.get("workspace"),
            "last_result": task.get("last_result"),
            "quarantine_reason": task.get("quarantine_reason"),
            "running_since": task.get("running_since"),
            "diagnosis": diagnosis,
        })
    return {"tasks": out, "count": len(out)}


def cmd_rescope(
    *,
    tasks_file: str,
    task_uuid: str,
    username: str,
    organization: str,
    workspace: str,
    operator: str,
    dry_run: bool,
) -> dict[str, Any]:
    missing = [
        name
        for name, value in (
            ("username", username),
            ("organization", organization),
            ("workspace", workspace),
        )
        if not (value or "").strip()
    ]
    if missing:
        log_security_event(
            action="admin_scheduler_rescope",
            decision="DENY",
            user=operator,
            organization=organization or None,
            resource_type="task",
            resource_id=task_uuid,
            reason=f"missing_fields:{','.join(missing)}",
        )
        raise ValueError(
            f"Missing required fields: {', '.join(missing)}"
        )

    tasks = _read_tasks(tasks_file)
    target = next((t for t in tasks if t.get("uuid") == task_uuid), None)
    if target is None:
        raise KeyError(f"Task {task_uuid} not found in {tasks_file}")

    target["username"] = username
    target["organization"] = organization
    target["workspace"] = workspace
    target["state"] = TaskState.IDLE.value
    target["quarantine_reason"] = None
    target["migration_state"] = "admin_rescoped"
    target["last_result"] = _strip_blocked_scope_from_last_result(
        target.get("last_result")
    )
    target["updated_at"] = _now_iso()

    if dry_run:
        log_security_event(
            action="admin_scheduler_rescope_dry_run",
            decision="ALLOW",
            user=operator,
            organization=organization,
            resource_type="task",
            resource_id=task_uuid,
            reason="dry_run",
        )
        return {
            "status": "rescoped_dry_run",
            "task_uuid": task_uuid,
            "new_scope": {
                "username": username,
                "organization": organization,
                "workspace": workspace,
            },
        }

    _write_tasks(tasks_file, tasks)
    log_security_event(
        action="admin_scheduler_rescope",
        decision="ALLOW",
        user=operator,
        organization=organization,
        resource_type="task",
        resource_id=task_uuid,
        reason="applied",
    )
    return {
        "status": "rescoped",
        "task_uuid": task_uuid,
        "new_scope": {
            "username": username,
            "organization": organization,
            "workspace": workspace,
        },
    }


def cmd_purge_orphans(
    *,
    tasks_file: str,
    operator: str,
    dry_run: bool,
) -> dict[str, Any]:
    user_mgr = _load_user_manager()
    if user_mgr is None:
        return {
            "status": "skipped",
            "reason": "user_manager_unavailable",
            "removed": [],
            "would_remove": [],
        }

    known_users = set(user_mgr.list_users())
    tasks = _read_tasks(tasks_file)

    orphan_uuids: list[str] = []
    remaining: list[dict[str, Any]] = []
    for task in tasks:
        owner = task.get("username")
        if owner and owner not in known_users:
            orphan_uuids.append(task.get("uuid"))
            log_security_event(
                action="admin_scheduler_purge_orphan",
                decision="ALLOW" if not dry_run else "DRY_RUN",
                user=operator,
                organization=task.get("organization"),
                resource_type="task",
                resource_id=task.get("uuid"),
                reason=f"owner_missing:{owner}",
            )
            if dry_run:
                remaining.append(task)
            # else: drop from remaining list
        else:
            remaining.append(task)

    if not dry_run:
        _write_tasks(tasks_file, remaining)
        return {"status": "purged", "removed": orphan_uuids}
    return {"status": "purged_dry_run", "would_remove": orphan_uuids}


def cmd_unstick(
    *,
    tasks_file: str,
    operator: str,
    dry_run: bool,
) -> dict[str, Any]:
    tasks = _read_tasks(tasks_file)
    ttl = timedelta(seconds=_get_run_ttl_seconds())
    now = datetime.now(timezone.utc)
    stuck: list[str] = []
    for task in tasks:
        if task.get("state") != TaskState.RUNNING.value:
            continue
        running_since_raw = task.get("running_since")
        running_since: datetime | None
        if running_since_raw is None:
            running_since = None
        else:
            try:
                running_since = datetime.fromisoformat(running_since_raw)
                if running_since.tzinfo is None:
                    running_since = running_since.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                running_since = None

        if running_since is not None and (now - running_since) < ttl:
            continue

        stuck.append(task.get("uuid"))
        if dry_run:
            log_security_event(
                action="admin_scheduler_unstick",
                decision="DRY_RUN",
                user=operator,
                organization=task.get("organization"),
                resource_type="task",
                resource_id=task.get("uuid"),
                reason="would_recover_stale_running",
            )
            continue

        reason = "no_running_since" if running_since is None else "ttl_exceeded"
        marker = f"RECOVERED_STALE_RUNNING: {reason}_admin"
        previous = task.get("last_result") or ""
        task["state"] = TaskState.ERROR.value
        task["running_since"] = None
        task["updated_at"] = now.isoformat()
        task["last_result"] = (
            f"{previous}\n---\n{marker}".strip() if previous else marker
        )
        log_security_event(
            action="admin_scheduler_unstick",
            decision="ALLOW",
            user=operator,
            organization=task.get("organization"),
            resource_type="task",
            resource_id=task.get("uuid"),
            reason=reason,
        )

    if not dry_run:
        _write_tasks(tasks_file, tasks)
        return {"status": "unstuck", "unstuck": stuck}
    return {"status": "unstuck_dry_run", "would_unstick": stuck}


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    # Common arguments re-exposed on every subcommand so that both
    #   scheduler_admin --tasks-file F list
    #   scheduler_admin list --tasks-file F
    # work identically, matching operator ergonomics.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--tasks-file",
        default=DEFAULT_TASKS_FILE,
        help="Path to tasks.json (default: tmp/scheduler/tasks.json)",
    )

    parser = argparse.ArgumentParser(
        prog="scheduler_admin",
        description="KOREV Evidence scheduler operator CLI",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", parents=[common], help="Inventory scheduler tasks")
    p_list.add_argument("--state", default=None, help="Filter by state")
    p_list.add_argument(
        "--quarantined",
        action="store_true",
        dest="quarantined_only",
        help="Only show scope-quarantined tasks",
    )

    # rescope
    p_rescope = sub.add_parser(
        "rescope",
        parents=[common],
        help="Repair the scope of a legacy task and re-enable it",
    )
    p_rescope.add_argument("--task-uuid", required=True)
    p_rescope.add_argument("--username", required=True)
    p_rescope.add_argument("--organization", required=True)
    p_rescope.add_argument("--workspace", required=True)
    p_rescope.add_argument("--operator", required=True)
    _add_apply_flag(p_rescope)

    # purge-orphans
    p_purge = sub.add_parser(
        "purge-orphans",
        parents=[common],
        help="Delete tasks whose owner user no longer exists in users.json",
    )
    p_purge.add_argument("--operator", required=True)
    _add_apply_flag(p_purge)

    # unstick
    p_unstick = sub.add_parser(
        "unstick",
        parents=[common],
        help="Force-recover RUNNING tasks past the TTL to ERROR state",
    )
    p_unstick.add_argument("--operator", required=True)
    _add_apply_flag(p_unstick)

    return parser


def _add_apply_flag(sub: argparse.ArgumentParser) -> None:
    group = sub.add_mutually_exclusive_group()
    group.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes to disk (default: dry-run)",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Do not persist changes (default)",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse already printed the error message to stderr; translate its
        # SystemExit into a plain non-zero return code so callers (and tests)
        # get a deterministic integer without relying on interpreter exit.
        code = exc.code if isinstance(exc.code, int) else 2
        return code if code is not None else 2
    dry_run = not getattr(args, "apply", False)

    try:
        if args.command == "list":
            result = cmd_list(
                tasks_file=args.tasks_file,
                state=args.state,
                quarantined_only=args.quarantined_only,
            )
        elif args.command == "rescope":
            result = cmd_rescope(
                tasks_file=args.tasks_file,
                task_uuid=args.task_uuid,
                username=args.username,
                organization=args.organization,
                workspace=args.workspace,
                operator=args.operator,
                dry_run=dry_run,
            )
        elif args.command == "purge-orphans":
            result = cmd_purge_orphans(
                tasks_file=args.tasks_file,
                operator=args.operator,
                dry_run=dry_run,
            )
        elif args.command == "unstick":
            result = cmd_unstick(
                tasks_file=args.tasks_file,
                operator=args.operator,
                dry_run=dry_run,
            )
        else:  # pragma: no cover - argparse enforces the choices
            parser.error(f"Unknown command {args.command}")
            return 2
    except (ValueError, KeyError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
