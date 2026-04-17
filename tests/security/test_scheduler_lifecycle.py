"""
Lifecycle tests for the scheduler — reversibility of scope quarantine
and recovery of stale RUNNING tasks.

These tests pin down the contract expected from the scheduler:

P1.1 — Quarantine reversibility
  When a previously quarantined legacy task has its scope repaired (either
  hydrated from the chat context file, or patched externally on disk by an
  operator), the next reload MUST un-quarantine it automatically. The
  BLOCKED_SCOPE marker MUST be removed from last_result, the state MUST
  return to IDLE, quarantine_reason MUST be cleared, and an observability
  event MUST be emitted.

P1.3 — Stale RUNNING recovery
  When a task crashes mid-execution, its state stays at RUNNING on disk and
  no `on_success`/`on_error` ever runs. The scheduler MUST detect this via a
  TTL on `running_since` and force the state to ERROR with a
  RECOVERED_STALE_RUNNING marker, so the claim path can re-execute it later.
  The TTL MUST be configurable via the EVIDENCE_SCHEDULER_RUN_TTL_SECONDS
  env var and default to 900s.

These tests deliberately avoid touching the filesystem singleton — they
instantiate a fresh SchedulerTaskList bound to a per-test JSON store, so
they are deterministic and parallel-safe.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from python.helpers.task_scheduler import (
    SchedulerTaskList,
    ScheduledTask,
    TaskSchedule,
    TaskState,
    serialize_task,
    deserialize_task,
)
from python.helpers.persistence.stores import JsonTaskStore


def _build_scheduled_task(
    *,
    uuid: str | None = None,
    username: str | None = None,
    organization: str | None = None,
    workspace: str | None = None,
    state: TaskState = TaskState.IDLE,
    last_result: str | None = None,
    quarantine_reason: str | None = None,
    migration_state: str | None = "current",
) -> ScheduledTask:
    task = ScheduledTask.create(
        name="lifecycle-task",
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
    task.migration_state = migration_state
    return task


@pytest.fixture()
def tmp_store(tmp_path: Path) -> JsonTaskStore:
    store_path = tmp_path / "scheduler" / "tasks.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    return JsonTaskStore(path=str(store_path))


@pytest.fixture()
def task_list(tmp_store: JsonTaskStore) -> SchedulerTaskList:
    data = SchedulerTaskList(tasks=[])
    data._store = tmp_store
    return data


# ---------------------------------------------------------------------------
# P1.1 — Quarantine reversibility
# ---------------------------------------------------------------------------


class TestQuarantineReversibility:
    """A task that has regained a valid scope must exit the quarantine."""

    def test_disabled_task_with_valid_scope_is_rehabilitated(
        self, task_list: SchedulerTaskList
    ) -> None:
        """Externally repaired scope triggers auto re-enablement on reload."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.DISABLED,
            last_result=(
                "Last successful output captured on 2026-03-27\n"
                "---\n"
                "BLOCKED_SCOPE: task_missing_owner"
            ),
            quarantine_reason="task_missing_owner",
            migration_state="quarantined_task_missing_owner",
        )
        task_list.tasks = [task]

        changed = task_list._migrate_and_quarantine_legacy_tasks()

        assert changed is True, "scheduler should rewrite the task on rehabilitation"
        assert task.state == TaskState.IDLE
        assert task.quarantine_reason is None
        assert task.migration_state == "rehabilitated"
        assert task.last_result is not None
        assert "BLOCKED_SCOPE" not in task.last_result
        assert "Last successful output captured on 2026-03-27" in task.last_result

    def test_rehabilitation_preserves_non_scope_last_result_lines(
        self, task_list: SchedulerTaskList
    ) -> None:
        """Only BLOCKED_SCOPE lines must be stripped from last_result."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.DISABLED,
            last_result=(
                "Previous successful run output\n"
                "---\n"
                "BLOCKED_SCOPE: task_missing_organization"
            ),
            quarantine_reason="task_missing_organization",
            migration_state="quarantined_task_missing_organization",
        )
        task_list.tasks = [task]

        task_list._migrate_and_quarantine_legacy_tasks()

        assert task.last_result is not None
        assert "BLOCKED_SCOPE" not in task.last_result
        assert "Previous successful run output" in task.last_result

    def test_last_result_becomes_none_when_only_blocked_scope(
        self, task_list: SchedulerTaskList
    ) -> None:
        """A last_result made exclusively of BLOCKED_SCOPE lines must be cleared."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_workspace",
            quarantine_reason="task_missing_workspace",
            migration_state="quarantined_task_missing_workspace",
        )
        task_list.tasks = [task]

        task_list._migrate_and_quarantine_legacy_tasks()

        assert task.last_result is None

    def test_task_without_scope_stays_quarantined(
        self, task_list: SchedulerTaskList
    ) -> None:
        """If scope is still missing after hydration, task stays DISABLED."""
        task = _build_scheduled_task(
            username=None,
            organization=None,
            workspace=None,
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_owner",
            quarantine_reason="task_missing_owner",
            migration_state="quarantined_task_missing_owner",
        )
        task_list.tasks = [task]

        task_list._migrate_and_quarantine_legacy_tasks()

        assert task.state == TaskState.DISABLED
        assert task.quarantine_reason == "task_missing_owner"
        assert task.migration_state == "quarantined_task_missing_owner"
        assert task.last_result is not None
        assert "BLOCKED_SCOPE" in task.last_result

    def test_rehabilitation_emits_observability_event(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A task returning from quarantine must emit task_rehabilitated."""
        captured: list[dict] = []

        def _capture(**kwargs):
            captured.append(kwargs)

        monkeypatch.setattr(
            "python.helpers.task_scheduler.log_observability_event", _capture
        )

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_owner",
            quarantine_reason="task_missing_owner",
        )
        task_list.tasks = [task]

        task_list._migrate_and_quarantine_legacy_tasks()

        rehab_events = [e for e in captured if e.get("event_type") == "task_rehabilitated"]
        assert len(rehab_events) == 1
        assert rehab_events[0]["status"] == "ALLOW"
        assert rehab_events[0]["username"] == "jeremie"
        assert rehab_events[0]["organization"] == "dica"
        assert rehab_events[0]["task_uuid"] == task.uuid

    def test_rehabilitation_emits_security_audit(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A task rehabilitation must leave a security audit trail."""
        captured: list[dict] = []

        def _capture(**kwargs):
            captured.append(kwargs)

        monkeypatch.setattr(
            "python.helpers.task_scheduler.log_security_event", _capture
        )

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_owner",
            quarantine_reason="task_missing_owner",
        )
        task_list.tasks = [task]

        task_list._migrate_and_quarantine_legacy_tasks()

        rehab_events = [e for e in captured if e.get("action") == "legacy_task_rehabilitated"]
        assert len(rehab_events) == 1
        assert rehab_events[0]["decision"] == "ALLOW"
        assert rehab_events[0]["user"] == "jeremie"
        assert rehab_events[0]["organization"] == "dica"
        assert rehab_events[0]["resource_id"] == task.uuid

    def test_rehabilitation_is_idempotent(
        self, task_list: SchedulerTaskList
    ) -> None:
        """Calling the migration twice must not flip the state back."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_owner",
            quarantine_reason="task_missing_owner",
        )
        task_list.tasks = [task]

        first_changed = task_list._migrate_and_quarantine_legacy_tasks()
        second_changed = task_list._migrate_and_quarantine_legacy_tasks()

        assert first_changed is True
        assert second_changed is False
        assert task.state == TaskState.IDLE
        assert task.migration_state == "rehabilitated"

    def test_idle_task_with_valid_scope_is_never_touched(
        self, task_list: SchedulerTaskList
    ) -> None:
        """A healthy IDLE task must not be rewritten by the lifecycle pass."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.IDLE,
            last_result=None,
            quarantine_reason=None,
            migration_state="current",
        )
        task_list.tasks = [task]

        changed = task_list._migrate_and_quarantine_legacy_tasks()

        assert changed is False
        assert task.state == TaskState.IDLE
        assert task.migration_state == "current"
        assert task.quarantine_reason is None


# ---------------------------------------------------------------------------
# P1.3 — Stale RUNNING recovery
# ---------------------------------------------------------------------------


class TestStaleRunningRecovery:
    """A task stuck in RUNNING beyond the TTL must be recovered to ERROR."""

    def test_running_since_is_serialized_and_restored(self) -> None:
        """The new running_since field must round-trip through serialization."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
        )
        task.running_since = datetime(2026, 4, 17, 18, 30, tzinfo=timezone.utc)

        serialized = serialize_task(task)
        restored = deserialize_task(serialized)

        assert restored.running_since is not None
        assert restored.running_since == task.running_since

    def test_default_running_since_is_none(self) -> None:
        """By default a task has no running_since."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
        )
        assert task.running_since is None

    def test_stale_running_task_is_recovered_to_error(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A RUNNING task older than the TTL must be flipped to ERROR."""
        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
        )
        task.running_since = datetime.now(timezone.utc) - timedelta(seconds=1800)
        task_list.tasks = [task]

        changed = task_list._recover_stale_running_tasks()

        assert changed is True
        assert task.state == TaskState.ERROR
        assert task.last_result is not None
        assert "RECOVERED_STALE_RUNNING" in task.last_result
        assert task.running_since is None

    def test_fresh_running_task_is_not_touched(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A RUNNING task younger than the TTL must be preserved as-is."""
        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
        )
        task.running_since = datetime.now(timezone.utc) - timedelta(seconds=60)
        task_list.tasks = [task]

        changed = task_list._recover_stale_running_tasks()

        assert changed is False
        assert task.state == TaskState.RUNNING
        assert task.running_since is not None

    def test_running_task_without_running_since_is_recovered_as_legacy(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RUNNING tasks with no running_since are considered legacy-stale."""
        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
        )
        task.running_since = None
        task_list.tasks = [task]

        changed = task_list._recover_stale_running_tasks()

        assert changed is True
        assert task.state == TaskState.ERROR
        assert task.last_result is not None
        assert "RECOVERED_STALE_RUNNING" in task.last_result
        assert "no_running_since" in task.last_result

    def test_idle_tasks_are_never_recovered(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The recovery pass only touches RUNNING tasks."""
        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.IDLE,
        )
        task_list.tasks = [task]

        changed = task_list._recover_stale_running_tasks()

        assert changed is False
        assert task.state == TaskState.IDLE

    def test_recovery_emits_observability_event(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Stale recovery must emit task_stale_running_recovered."""
        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")
        captured: list[dict] = []

        def _capture(**kwargs):
            captured.append(kwargs)

        monkeypatch.setattr(
            "python.helpers.task_scheduler.log_observability_event", _capture
        )

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
        )
        task.running_since = datetime.now(timezone.utc) - timedelta(seconds=3600)
        task_list.tasks = [task]

        task_list._recover_stale_running_tasks()

        stale_events = [
            e for e in captured if e.get("event_type") == "task_stale_running_recovered"
        ]
        assert len(stale_events) == 1
        assert stale_events[0]["status"] == "DENY"
        assert stale_events[0]["task_uuid"] == task.uuid

    def test_recovery_ttl_is_configurable_via_env(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Shrinking the TTL must recover tasks that were previously fresh."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
        )
        task.running_since = datetime.now(timezone.utc) - timedelta(seconds=60)
        task_list.tasks = [task]

        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "30")
        changed = task_list._recover_stale_running_tasks()

        assert changed is True
        assert task.state == TaskState.ERROR

    def test_reload_triggers_stale_recovery(
        self,
        task_list: SchedulerTaskList,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """reload() must run the stale recovery pass, not just quarantine."""
        monkeypatch.setenv("EVIDENCE_SCHEDULER_RUN_TTL_SECONDS", "900")

        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.RUNNING,
        )
        task.running_since = datetime.now(timezone.utc) - timedelta(seconds=3600)
        task_list._store.put_task(serialize_task(task))

        asyncio.run(task_list.reload())

        reloaded = task_list.get_tasks()[0]
        assert reloaded.state == TaskState.ERROR
        assert reloaded.last_result is not None
        assert "RECOVERED_STALE_RUNNING" in reloaded.last_result


# ---------------------------------------------------------------------------
# Cross-cutting — reload-driven lifecycle
# ---------------------------------------------------------------------------


class TestReloadDrivenLifecycle:
    """reload() must apply both rehabilitation and stale recovery atomically."""

    def test_reload_rehabilitates_externally_fixed_task(
        self,
        task_list: SchedulerTaskList,
    ) -> None:
        """Simulate an operator patching tasks.json to repair scope."""
        task = _build_scheduled_task(
            username=None,
            organization=None,
            workspace=None,
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_owner",
            quarantine_reason="task_missing_owner",
        )
        task_list._store.put_task(serialize_task(task))

        raw = json.loads(Path(task_list._store.path).read_text())
        raw["tasks"][0]["username"] = "jeremie"
        raw["tasks"][0]["organization"] = "dica"
        raw["tasks"][0]["workspace"] = "/app/shared/users/jeremie"
        Path(task_list._store.path).write_text(json.dumps(raw, ensure_ascii=False))

        asyncio.run(task_list.reload())

        reloaded = task_list.get_tasks()[0]
        assert reloaded.state == TaskState.IDLE
        assert reloaded.quarantine_reason is None
        assert reloaded.migration_state == "rehabilitated"

    def test_json_store_claim_sets_running_since(
        self,
        tmp_store: JsonTaskStore,
    ) -> None:
        """The JSON store claim path must populate running_since."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.IDLE,
        )
        tmp_store.put_task(serialize_task(task))

        assert tmp_store.claim_task(task.uuid) is True

        raw = json.loads(Path(tmp_store.path).read_text())
        persisted = raw["tasks"][0]
        assert persisted["state"] == TaskState.RUNNING.value
        assert persisted.get("running_since") is not None
        restored = deserialize_task(persisted)
        assert restored.running_since is not None
        assert restored.running_since.tzinfo is not None

    def test_json_store_claim_conflict_preserves_running_since(
        self,
        tmp_store: JsonTaskStore,
    ) -> None:
        """A second claim on an already-running task must not overwrite running_since."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.IDLE,
        )
        tmp_store.put_task(serialize_task(task))

        assert tmp_store.claim_task(task.uuid) is True
        first_persist = json.loads(Path(tmp_store.path).read_text())
        first_ts = first_persist["tasks"][0]["running_since"]
        assert first_ts is not None

        assert tmp_store.claim_task(task.uuid) is False
        second_persist = json.loads(Path(tmp_store.path).read_text())
        assert second_persist["tasks"][0]["running_since"] == first_ts

    def test_reload_persists_rehabilitation_to_disk(
        self,
        task_list: SchedulerTaskList,
    ) -> None:
        """After reload rehabilitates a task, the change must hit disk."""
        task = _build_scheduled_task(
            username="jeremie",
            organization="dica",
            workspace="/app/shared/users/jeremie",
            state=TaskState.DISABLED,
            last_result="BLOCKED_SCOPE: task_missing_owner",
            quarantine_reason="task_missing_owner",
        )
        task_list._store.put_task(serialize_task(task))

        asyncio.run(task_list.reload())

        persisted = json.loads(Path(task_list._store.path).read_text())
        task_data = persisted["tasks"][0]
        assert task_data["state"] == TaskState.IDLE.value
        assert task_data["quarantine_reason"] is None
        assert task_data["migration_state"] == "rehabilitated"
