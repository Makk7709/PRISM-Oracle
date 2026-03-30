from python.helpers.task_scheduler import (
    SchedulerTaskList,
    ScheduledTask,
    TaskSchedule,
    TaskState,
    deserialize_task,
    serialize_task,
)


def _build_task(
    *,
    username: str | None,
    organization: str | None,
    workspace: str | None,
) -> ScheduledTask:
    return ScheduledTask.create(
        name="weekly",
        system_prompt="sys",
        prompt="run",
        schedule=TaskSchedule(minute="0", hour="8", day="*", month="*", weekday="1", timezone="UTC"),
        username=username,
        organization=organization,
        workspace=workspace,
    )


def test_scheduler_quarantines_unscoped_task():
    task = _build_task(username="jeremie", organization=None, workspace="/app/shared/users/jeremie")
    data = SchedulerTaskList(tasks=[task])
    changed = data._migrate_and_quarantine_legacy_tasks()

    assert changed is True
    assert task.state == TaskState.DISABLED
    assert (task.last_result or "").startswith("BLOCKED_SCOPE:")


def test_scheduler_add_task_rejects_missing_scope():
    task = _build_task(username="jeremie", organization=None, workspace="/app/shared/users/jeremie")
    data = SchedulerTaskList(tasks=[])
    try:
        import asyncio

        asyncio.run(data.add_task(task))
        assert False, "Expected scope rejection"
    except ValueError as exc:
        assert "task_missing_organization" in str(exc)


def test_task_serialization_roundtrip_keeps_organization():
    task = _build_task(
        username="jeremie",
        organization="dica",
        workspace="/app/shared/users/jeremie",
    )
    serialized = serialize_task(task)
    restored = deserialize_task(serialized)
    assert restored.organization == "dica"
