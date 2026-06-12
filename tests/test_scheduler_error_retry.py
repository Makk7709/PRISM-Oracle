"""
Tests TDD — reprise automatique des tâches planifiées en erreur + fuseau horaire.

Contexte production (2026-06-12) : trois tâches cron ont été marquées ERROR par
la récupération stale-RUNNING (ttl_exceeded_903s) le 2026-06-01 et ne sont plus
jamais reparties : get_due_tasks() n'acceptait que l'état IDLE.

Défauts couverts :
  D1 — une ScheduledTask en ERROR doit être réessayée à sa prochaine occurrence cron.
  D2 — get_next_run() doit respecter le fuseau du schedule (affichait l'heure UTC).
  D3 — running_since doit être purgé quand la tâche quitte l'état RUNNING.
  D4 — le TTL par défaut (900 s) était trop court pour des runs agents longs.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytz

from python.helpers.persistence.stores import JsonTaskStore
from python.helpers.task_scheduler import (
    _DEFAULT_RUN_TTL_SECONDS,
    ScheduledTask,
    SchedulerTaskList,
    TaskSchedule,
    TaskState,
    serialize_tasks,
)


def _make_scheduled_task(
    state: TaskState,
    schedule: TaskSchedule | None = None,
    last_run: datetime | None = None,
) -> ScheduledTask:
    task = ScheduledTask.create(
        name="task-test",
        system_prompt="sys",
        prompt="do something",
        schedule=schedule
        or TaskSchedule(minute="*", hour="*", day="*", month="*", weekday="*", timezone="UTC"),
        username="jeremie",
        workspace="/tmp/ws-jeremie",
    )
    task.organization = "DICA France"
    task.state = state
    task.last_run = last_run or (datetime.now(timezone.utc) - timedelta(hours=2))
    return task


def _task_list_with(tmp_path, tasks) -> SchedulerTaskList:
    store = JsonTaskStore(path=str(tmp_path / "tasks.json"))
    store.put_tasks(serialize_tasks(tasks))
    task_list = SchedulerTaskList(tasks=[])
    task_list._store = store
    return task_list


# ── D1 : reprise automatique des tâches cron en erreur ──────────────────────


def test_error_scheduled_task_is_due_at_next_occurrence(tmp_path):
    """Une tâche cron en ERROR doit redevenir éligible à sa prochaine occurrence."""
    task = _make_scheduled_task(TaskState.ERROR)
    task_list = _task_list_with(tmp_path, [task])

    due = asyncio.run(task_list.get_due_tasks())

    assert [t.uuid for t in due] == [task.uuid]


def test_idle_scheduled_task_still_due(tmp_path):
    """Régression : l'état IDLE reste éligible."""
    task = _make_scheduled_task(TaskState.IDLE)
    task_list = _task_list_with(tmp_path, [task])

    due = asyncio.run(task_list.get_due_tasks())

    assert [t.uuid for t in due] == [task.uuid]


def test_disabled_scheduled_task_is_not_due(tmp_path):
    """Une tâche désactivée manuellement ne doit jamais repartir seule."""
    task = _make_scheduled_task(TaskState.DISABLED)
    task_list = _task_list_with(tmp_path, [task])

    due = asyncio.run(task_list.get_due_tasks())

    assert due == []


def test_running_scheduled_task_is_not_due(tmp_path):
    """Une tâche en cours ne doit pas être relancée en parallèle."""
    task = _make_scheduled_task(TaskState.RUNNING)
    task.running_since = datetime.now(timezone.utc)
    task_list = _task_list_with(tmp_path, [task])

    due = asyncio.run(task_list.get_due_tasks())

    assert due == []


def test_error_task_not_due_before_next_occurrence(tmp_path):
    """Pas de boucle de retry serrée : la reprise attend l'occurrence cron suivante."""
    # Prochaine occurrence dans ~10 h : hors fenêtre du tick.
    target = datetime.now(timezone.utc) + timedelta(hours=10)
    schedule = TaskSchedule(
        minute=str(target.minute),
        hour=str(target.hour),
        day="*",
        month="*",
        weekday="*",
        timezone="UTC",
    )
    task = _make_scheduled_task(TaskState.ERROR, schedule=schedule)
    task_list = _task_list_with(tmp_path, [task])

    due = asyncio.run(task_list.get_due_tasks())

    assert due == []


# ── D2 : get_next_run respecte le fuseau du schedule ────────────────────────


def test_get_next_run_uses_schedule_timezone():
    """Un cron '0 9 * * *' Europe/Paris doit tomber à 09:00 heure de Paris,
    pas à 09:00 UTC (qui s'affichait 11:00 Paris en été)."""
    schedule = TaskSchedule(
        minute="0", hour="9", day="*", month="*", weekday="*", timezone="Europe/Paris"
    )
    task = _make_scheduled_task(TaskState.IDLE, schedule=schedule)

    next_run = task.get_next_run()

    assert next_run is not None
    assert next_run.tzinfo is not None, "next_run doit être timezone-aware"
    next_run_paris = next_run.astimezone(pytz.timezone("Europe/Paris"))
    assert next_run_paris.hour == 9
    assert next_run_paris.minute == 0


# ── D3 : purge de running_since hors RUNNING ─────────────────────────────────


def test_update_to_idle_clears_running_since():
    task = _make_scheduled_task(TaskState.RUNNING)
    task.running_since = datetime.now(timezone.utc)

    task.update(state=TaskState.IDLE)

    assert task.running_since is None


def test_update_to_error_clears_running_since():
    task = _make_scheduled_task(TaskState.RUNNING)
    task.running_since = datetime.now(timezone.utc)

    task.update(state=TaskState.ERROR)

    assert task.running_since is None


def test_update_to_running_keeps_running_since():
    task = _make_scheduled_task(TaskState.IDLE)
    stamp = datetime.now(timezone.utc)
    task.running_since = stamp

    task.update(state=TaskState.RUNNING)

    assert task.running_since == stamp


# ── D4 : TTL par défaut compatible avec les runs agents longs ────────────────


def test_default_run_ttl_allows_long_agent_runs():
    """900 s tuait des tâches légitimes (veille web + rapport + email).
    Le défaut doit laisser au moins 1 h avant de déclarer un run crashé."""
    assert _DEFAULT_RUN_TTL_SECONDS >= 3600
