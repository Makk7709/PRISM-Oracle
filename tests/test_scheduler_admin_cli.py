"""
TDD tests for the operator CLI ``scripts/scheduler_admin.py``.

The CLI is the operator's last-resort tool when the REST API cannot be used
to administrate tasks (e.g. quarantined tasks whose scope is missing,
orphan tasks pointing at purged users, or tasks stuck in RUNNING after a
container crash). Each command MUST:

  - accept ``--dry-run`` and default to it when mutating data,
  - emit a machine-readable JSON report on stdout,
  - emit a ``log_security_event`` with the operator identity,
  - refuse to rewrite tasks.json atomically broken (invalid JSON input).

These tests import the CLI module directly rather than invoking it via
subprocess, so failures produce actionable tracebacks.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python.helpers.persistence.stores import JsonTaskStore
from python.helpers.task_scheduler import (
    ScheduledTask,
    TaskSchedule,
    TaskState,
    serialize_task,
)


def _build_task(
    *,
    name: str = "task",
    uuid: str | None = None,
    username: str | None = None,
    organization: str | None = None,
    workspace: str | None = None,
    state: TaskState = TaskState.IDLE,
    last_result: str | None = None,
    quarantine_reason: str | None = None,
    running_since: datetime | None = None,
) -> ScheduledTask:
    task = ScheduledTask.create(
        name=name,
        system_prompt="sys",
        prompt="run",
        schedule=TaskSchedule(
            minute="0", hour="8", day="*", month="*", weekday="1", timezone="UTC"
        ),
        username=username,
        organization=organization,
        workspace=workspace,
    )
    if uuid:
        task.uuid = uuid
        task.context_id = uuid
    task.state = state
    task.last_result = last_result
    task.quarantine_reason = quarantine_reason
    task.running_since = running_since
    return task


@pytest.fixture()
def tasks_file(tmp_path: Path) -> Path:
    path = tmp_path / "scheduler" / "tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
    return path


@pytest.fixture()
def seeded_store(tasks_file: Path) -> JsonTaskStore:
    """A store pre-loaded with a representative quarantine/orphan/stuck scenario."""
    store = JsonTaskStore(path=str(tasks_file))
    tasks = [
        _build_task(
            name="legacy-unscoped",
            uuid="legacy-uuid-1",
            username=None,
            organization=None,
            workspace=None,
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_owner",
            quarantine_reason="task_missing_owner",
        ),
        _build_task(
            name="orphan-user",
            uuid="orphan-uuid-1",
            username="ghost",
            organization="scriptoura",
            workspace="/app/shared/users/ghost",
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_workspace",
            quarantine_reason="task_missing_workspace",
        ),
        _build_task(
            name="stuck-running",
            uuid="stuck-uuid-1",
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
            running_since=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
        _build_task(
            name="healthy-idle",
            uuid="healthy-uuid-1",
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.IDLE,
        ),
    ]
    store.put_tasks([serialize_task(t) for t in tasks])
    return store


@pytest.fixture()
def user_manager_stub(monkeypatch: pytest.MonkeyPatch):
    """Provide a stub UserManager injected into scheduler_admin."""
    known_users = {"jeremie", "amine"}

    class _Stub:
        def list_users(self) -> list[str]:
            return list(known_users)

        def get_organization(self, username: str) -> str | None:
            if username in known_users:
                return "dica"
            return None

    stub = _Stub()

    from scripts import scheduler_admin

    monkeypatch.setattr(scheduler_admin, "_load_user_manager", lambda: stub)
    return stub


@pytest.fixture()
def captured_security_events(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    events: list[dict] = []

    def _capture(**kwargs):
        events.append(kwargs)

    from scripts import scheduler_admin

    monkeypatch.setattr(scheduler_admin, "log_security_event", _capture)
    return events


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------


class TestListCommand:
    def test_list_returns_all_tasks_by_default(
        self, seeded_store: JsonTaskStore, tasks_file: Path
    ) -> None:
        from scripts import scheduler_admin

        result = scheduler_admin.cmd_list(tasks_file=str(tasks_file), state=None)
        assert len(result["tasks"]) == 4

    def test_list_filters_by_state(
        self, seeded_store: JsonTaskStore, tasks_file: Path
    ) -> None:
        from scripts import scheduler_admin

        result = scheduler_admin.cmd_list(tasks_file=str(tasks_file), state="disabled")
        names = {t["name"] for t in result["tasks"]}
        assert names == {"legacy-unscoped", "orphan-user"}

    def test_list_flags_quarantined_tasks(
        self, seeded_store: JsonTaskStore, tasks_file: Path
    ) -> None:
        from scripts import scheduler_admin

        result = scheduler_admin.cmd_list(
            tasks_file=str(tasks_file), state=None, quarantined_only=True
        )
        names = {t["name"] for t in result["tasks"]}
        assert names == {"legacy-unscoped", "orphan-user"}

    def test_list_reports_diagnosis_per_task(
        self, seeded_store: JsonTaskStore, tasks_file: Path
    ) -> None:
        from scripts import scheduler_admin

        result = scheduler_admin.cmd_list(tasks_file=str(tasks_file), state=None)
        by_name = {t["name"]: t for t in result["tasks"]}
        assert by_name["legacy-unscoped"]["diagnosis"] == "quarantined_scope"
        assert by_name["stuck-running"]["diagnosis"] == "running"
        assert by_name["healthy-idle"]["diagnosis"] == "healthy"


# ---------------------------------------------------------------------------
# rescope command
# ---------------------------------------------------------------------------


class TestRescopeCommand:
    def test_rescope_updates_scope_and_reenables(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        captured_security_events: list[dict],
    ) -> None:
        from scripts import scheduler_admin

        result = scheduler_admin.cmd_rescope(
            tasks_file=str(tasks_file),
            task_uuid="legacy-uuid-1",
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            operator="ops-amine",
            dry_run=False,
        )
        assert result["status"] == "rescoped"
        persisted = json.loads(tasks_file.read_text())
        target = next(t for t in persisted["tasks"] if t["uuid"] == "legacy-uuid-1")
        assert target["username"] == "jeremie"
        assert target["organization"] == "dica"
        assert target["workspace"] == "/app/shared/users/jeremie"
        assert target["state"] == TaskState.IDLE.value
        assert target["quarantine_reason"] is None
        assert target["migration_state"] == "admin_rescoped"
        assert (target.get("last_result") or "").find("BLOCKED_SCOPE") == -1
        assert any(
            e.get("action") == "admin_scheduler_rescope"
            and e.get("decision") == "ALLOW"
            and e.get("user") == "ops-amine"
            for e in captured_security_events
        )

    def test_rescope_dry_run_does_not_persist(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        captured_security_events: list[dict],
    ) -> None:
        from scripts import scheduler_admin

        before = tasks_file.read_text()
        result = scheduler_admin.cmd_rescope(
            tasks_file=str(tasks_file),
            task_uuid="legacy-uuid-1",
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            operator="ops-amine",
            dry_run=True,
        )
        assert result["status"] == "rescoped_dry_run"
        assert tasks_file.read_text() == before
        assert any(
            e.get("action") == "admin_scheduler_rescope_dry_run"
            for e in captured_security_events
        )

    def test_rescope_refuses_missing_fields(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        captured_security_events: list[dict],
    ) -> None:
        from scripts import scheduler_admin

        with pytest.raises(ValueError) as excinfo:
            scheduler_admin.cmd_rescope(
                tasks_file=str(tasks_file),
                task_uuid="legacy-uuid-1",
                username="jeremie",
                organization="",
                workspace="/app/shared/users/jeremie",
                operator="ops-amine",
                dry_run=False,
            )
        assert "organization" in str(excinfo.value).lower()
        persisted = json.loads(tasks_file.read_text())
        target = next(t for t in persisted["tasks"] if t["uuid"] == "legacy-uuid-1")
        assert target["state"] == TaskState.DISABLED.value
        assert any(
            e.get("action") == "admin_scheduler_rescope"
            and e.get("decision") == "DENY"
            for e in captured_security_events
        )

    def test_rescope_unknown_task_raises(
        self, seeded_store: JsonTaskStore, tasks_file: Path
    ) -> None:
        from scripts import scheduler_admin

        with pytest.raises(KeyError):
            scheduler_admin.cmd_rescope(
                tasks_file=str(tasks_file),
                task_uuid="unknown-uuid",
                username="jeremie",
                organization="dica",
                workspace="/app/shared/users/jeremie",
                operator="ops-amine",
                dry_run=False,
            )


# ---------------------------------------------------------------------------
# purge-orphans command
# ---------------------------------------------------------------------------


class TestPurgeOrphansCommand:
    def test_purge_orphans_detects_missing_user(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        user_manager_stub,
        captured_security_events: list[dict],
    ) -> None:
        from scripts import scheduler_admin

        result = scheduler_admin.cmd_purge_orphans(
            tasks_file=str(tasks_file),
            operator="ops-amine",
            dry_run=False,
        )
        assert result["removed"] == ["orphan-uuid-1"]
        persisted = json.loads(tasks_file.read_text())
        remaining_uuids = {t["uuid"] for t in persisted["tasks"]}
        assert "orphan-uuid-1" not in remaining_uuids
        assert "legacy-uuid-1" in remaining_uuids
        assert any(
            e.get("action") == "admin_scheduler_purge_orphan"
            and e.get("resource_id") == "orphan-uuid-1"
            for e in captured_security_events
        )

    def test_purge_orphans_dry_run_does_not_remove(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        user_manager_stub,
    ) -> None:
        from scripts import scheduler_admin

        before = tasks_file.read_text()
        result = scheduler_admin.cmd_purge_orphans(
            tasks_file=str(tasks_file),
            operator="ops-amine",
            dry_run=True,
        )
        assert result["would_remove"] == ["orphan-uuid-1"]
        assert tasks_file.read_text() == before

    def test_purge_orphans_skips_tasks_without_owner(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        user_manager_stub,
    ) -> None:
        """Tasks without any username are scope-quarantined, not orphans."""
        from scripts import scheduler_admin

        result = scheduler_admin.cmd_purge_orphans(
            tasks_file=str(tasks_file),
            operator="ops-amine",
            dry_run=True,
        )
        assert "legacy-uuid-1" not in result["would_remove"]


# ---------------------------------------------------------------------------
# unstick command
# ---------------------------------------------------------------------------


class TestUnstickCommand:
    def test_unstick_resets_running_to_idle_after_ttl(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        captured_security_events: list[dict],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import scheduler_admin

        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")
        result = scheduler_admin.cmd_unstick(
            tasks_file=str(tasks_file),
            operator="ops-amine",
            dry_run=False,
        )
        assert result["unstuck"] == ["stuck-uuid-1"]
        persisted = json.loads(tasks_file.read_text())
        target = next(t for t in persisted["tasks"] if t["uuid"] == "stuck-uuid-1")
        assert target["state"] == TaskState.ERROR.value
        assert "RECOVERED_STALE_RUNNING" in (target.get("last_result") or "")
        assert target.get("running_since") is None
        assert any(
            e.get("action") == "admin_scheduler_unstick"
            and e.get("resource_id") == "stuck-uuid-1"
            for e in captured_security_events
        )

    def test_unstick_dry_run_preserves_state(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import scheduler_admin

        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")
        before = tasks_file.read_text()
        result = scheduler_admin.cmd_unstick(
            tasks_file=str(tasks_file),
            operator="ops-amine",
            dry_run=True,
        )
        assert result["would_unstick"] == ["stuck-uuid-1"]
        assert tasks_file.read_text() == before

    def test_unstick_leaves_fresh_running_alone(
        self,
        tasks_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import scheduler_admin

        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")
        store = JsonTaskStore(path=str(tasks_file))
        fresh = _build_task(
            uuid="fresh-uuid",
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
            running_since=datetime.now(timezone.utc) - timedelta(seconds=60),
        )
        store.put_task(serialize_task(fresh))

        result = scheduler_admin.cmd_unstick(
            tasks_file=str(tasks_file),
            operator="ops-amine",
            dry_run=False,
        )
        assert result["unstuck"] == []
        persisted = json.loads(tasks_file.read_text())
        target = next(t for t in persisted["tasks"] if t["uuid"] == "fresh-uuid")
        assert target["state"] == TaskState.RUNNING.value


# ---------------------------------------------------------------------------
# CLI entrypoint smoke
# ---------------------------------------------------------------------------


class TestCliEntrypoint:
    def test_main_list_exits_zero(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from scripts import scheduler_admin

        exit_code = scheduler_admin.main(
            ["list", "--tasks-file", str(tasks_file)]
        )
        assert exit_code == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert "tasks" in payload

    def test_main_rescope_requires_all_fields(
        self,
        seeded_store: JsonTaskStore,
        tasks_file: Path,
    ) -> None:
        from scripts import scheduler_admin

        exit_code = scheduler_admin.main(
            [
                "rescope",
                "--tasks-file",
                str(tasks_file),
                "--task-uuid",
                "legacy-uuid-1",
                "--username",
                "jeremie",
                "--organization",
                "dica",
                # --workspace missing on purpose
                "--operator",
                "ops-amine",
                "--apply",
            ]
        )
        assert exit_code != 0
