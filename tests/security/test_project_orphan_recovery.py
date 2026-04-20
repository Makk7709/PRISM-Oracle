"""
Tests de robustesse : quand un chat reference un projet dont le `project.json`
n'existe plus sur disque (projet supprime, volume perdu, dossier jamais cree),
le scheduler de memoire NE DOIT PAS crasher avec une FileNotFoundError
remontant dans `monologue_start`.

Regression reproduite en production (Apr 2026) : chat `nL2vzKZq` de
jeremie/dica-france avec `data.project = "mairie"`, le dossier
`/app/usr/projects/mairie/` n'existait pas, chaque message declenchait
`monologue_start -> get_agent_memory_subdir -> load_basic_project_data
-> read_file(project.json) -> FileNotFoundError` non rattrape.

Contrat attendu de `python.helpers.projects.get_context_memory_subdir` :

  1. Si le projet reference n'existe plus (FileNotFoundError sur
     `project.json`), la fonction DOIT retourner `None` (fallback memory
     par defaut) au lieu de lever.
  2. Elle DOIT auto-heal le contexte en appelant
     `context.set_data(CONTEXT_DATA_KEY_PROJECT, None)` pour que les
     appels suivants ne refassent pas le meme chemin d'echec.
  3. Elle DOIT persister le cleanup via `persist_chat.save_tmp_chat`
     pour que le chat.json sur disque ne reference plus le projet
     orphelin.
  4. Elle DOIT emettre un evenement d'observabilite
     `project_reference_orphaned` (status=`WARN`) avec username,
     organization, task_uuid=None, correlation_id=`chat:<id>`,
     reason="<project_name>", metadata={"project_name": ...,
     "chat_id": ...}.
  5. Sur un projet valide + `memory="own"`, le comportement actuel DOIT
     etre preserve (retourne `projects/<name>`).
  6. Sur un projet valide + `memory="global"`, retourne `None` (pas de
     scoping projet).
  7. Pas de projet actif -> retourne `None`.
  8. Si `project.json` existe mais est corrompu (JSON invalide),
     meme traitement que "missing" : retourne None + auto-heal
     + event, sans crash.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from python.helpers import projects, persist_chat
from python.helpers.projects import (
    CONTEXT_DATA_KEY_PROJECT,
    PROJECT_HEADER_FILE,
    PROJECT_META_DIR,
    PROJECTS_PARENT_DIR,
    get_context_memory_subdir,
)


class _FakeContext:
    """Minimal stub satisfying the surface used by get_context_memory_subdir."""

    def __init__(
        self,
        *,
        context_id: str = "test-ctx",
        project_name: str | None = None,
        username: str | None = "alice",
        organization: str | None = "acme",
    ):
        self.id = context_id
        self.username = username
        self.organization = organization
        self._data: dict[str, Any] = {}
        if project_name is not None:
            self._data[CONTEXT_DATA_KEY_PROJECT] = project_name

    def get_data(self, key: str):
        return self._data.get(key)

    def set_data(self, key: str, value: Any):
        self._data[key] = value


@pytest.fixture
def isolated_repo(monkeypatch, tmp_path: Path):
    """Redirect the project root used by `files.get_abs_path` to tmp_path."""
    from python.helpers import files as files_module

    monkeypatch.setattr(files_module, "get_base_dir", lambda: str(tmp_path))
    (tmp_path / PROJECTS_PARENT_DIR).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def captured_save(monkeypatch):
    """Intercept persist_chat.save_tmp_chat to observe cleanup persistence."""
    calls: list[Any] = []

    def _fake_save(context):
        calls.append(context)

    monkeypatch.setattr(persist_chat, "save_tmp_chat", _fake_save)
    return calls


@pytest.fixture
def captured_events(monkeypatch):
    """Capture observability events emitted by the module under test."""
    events: list[dict[str, Any]] = []

    def _fake_log(**kwargs):
        events.append(kwargs)

    # The projects module will import log_observability_event lazily or at
    # module-scope. Either patch works if we attach to the module the
    # function is imported into (see GREEN phase). Default target below:
    monkeypatch.setattr(
        "python.observability.runtime.log_observability_event",
        _fake_log,
        raising=False,
    )
    # Also patch any already-imported alias inside the projects module:
    if hasattr(projects, "log_observability_event"):
        monkeypatch.setattr(
            projects, "log_observability_event", _fake_log, raising=False
        )
    return events


def _write_project_header(tmp_path: Path, name: str, header: dict):
    proj_dir = tmp_path / PROJECTS_PARENT_DIR / name / PROJECT_META_DIR
    proj_dir.mkdir(parents=True, exist_ok=True)
    with open(proj_dir / PROJECT_HEADER_FILE, "w", encoding="utf-8") as f:
        json.dump(header, f)


def _write_empty_header(tmp_path: Path, name: str):
    """Write an empty project.json.

    dirty_json.parse("") -> None, which causes load_project_header to raise
    TypeError on `header["name"] = name`. This reproduces the real-world
    failure mode for half-written / truncated files on a crashed disk.
    """
    proj_dir = tmp_path / PROJECTS_PARENT_DIR / name / PROJECT_META_DIR
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / PROJECT_HEADER_FILE).write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# Regression scenarios (missing or broken project)
# ---------------------------------------------------------------------------


def test_missing_project_returns_none_instead_of_crashing(
    isolated_repo, captured_save, captured_events
):
    ctx = _FakeContext(project_name="mairie")

    # Sanity: projet absent du disque.
    assert not (isolated_repo / PROJECTS_PARENT_DIR / "mairie").exists()

    # MUST NOT raise FileNotFoundError
    result = get_context_memory_subdir(ctx)

    assert result is None


def test_missing_project_autoheals_context_data(
    isolated_repo, captured_save, captured_events
):
    ctx = _FakeContext(project_name="mairie")

    get_context_memory_subdir(ctx)

    assert ctx.get_data(CONTEXT_DATA_KEY_PROJECT) is None, (
        "Context must be auto-healed so subsequent calls do not re-trigger "
        "the missing-project path."
    )


def test_missing_project_persists_cleanup_to_disk(
    isolated_repo, captured_save, captured_events
):
    ctx = _FakeContext(project_name="mairie")

    get_context_memory_subdir(ctx)

    assert len(captured_save) == 1, (
        "persist_chat.save_tmp_chat must be called exactly once to persist "
        "the cleared project reference to disk."
    )
    assert captured_save[0] is ctx


def test_missing_project_emits_observability_event(
    isolated_repo, captured_save, captured_events
):
    ctx = _FakeContext(
        context_id="nL2vzKZq",
        project_name="mairie",
        username="jeremie",
        organization="dica-france",
    )

    get_context_memory_subdir(ctx)

    orphaned = [
        e for e in captured_events if e.get("event_type") == "project_reference_orphaned"
    ]
    assert len(orphaned) == 1, (
        f"Expected exactly one project_reference_orphaned event, got {captured_events}"
    )
    ev = orphaned[0]
    assert ev.get("status") == "WARN"
    assert ev.get("username") == "jeremie"
    assert ev.get("organization") == "dica-france"
    assert ev.get("correlation_id") == "chat:nL2vzKZq"
    assert ev.get("reason") == "mairie"
    assert ev.get("metadata", {}).get("project_name") == "mairie"
    assert ev.get("metadata", {}).get("chat_id") == "nL2vzKZq"


def test_missing_project_only_emits_once_across_multiple_calls(
    isolated_repo, captured_save, captured_events
):
    ctx = _FakeContext(project_name="mairie")

    get_context_memory_subdir(ctx)
    get_context_memory_subdir(ctx)
    get_context_memory_subdir(ctx)

    orphaned = [
        e for e in captured_events if e.get("event_type") == "project_reference_orphaned"
    ]
    assert len(orphaned) == 1, (
        "Auto-heal must make subsequent calls no-op: only the first call "
        "should emit the orphan event."
    )
    assert len(captured_save) == 1, (
        "Only the first call should persist cleanup; idempotence required."
    )


def test_truncated_project_json_treated_as_missing(
    isolated_repo, captured_save, captured_events
):
    _write_empty_header(isolated_repo, "broken")
    ctx = _FakeContext(project_name="broken")

    result = get_context_memory_subdir(ctx)

    assert result is None
    assert ctx.get_data(CONTEXT_DATA_KEY_PROJECT) is None
    assert len(captured_save) == 1
    orphaned = [
        e for e in captured_events if e.get("event_type") == "project_reference_orphaned"
    ]
    assert len(orphaned) == 1


# ---------------------------------------------------------------------------
# Regression guards (nominal paths must remain intact)
# ---------------------------------------------------------------------------


def test_existing_project_with_own_memory_still_returns_project_subdir(
    isolated_repo, captured_save, captured_events
):
    _write_project_header(
        isolated_repo,
        "valid",
        {
            "title": "Valid",
            "description": "",
            "instructions": "",
            "color": "",
            "owner": "",
            "memory": "own",
        },
    )
    ctx = _FakeContext(project_name="valid")

    result = get_context_memory_subdir(ctx)

    assert result == "projects/valid"
    assert ctx.get_data(CONTEXT_DATA_KEY_PROJECT) == "valid"
    assert captured_save == [], "No cleanup must happen on the nominal path."
    assert captured_events == [], "No orphan event on the nominal path."


def test_existing_project_with_global_memory_returns_none(
    isolated_repo, captured_save, captured_events
):
    _write_project_header(
        isolated_repo,
        "shared",
        {
            "title": "Shared",
            "description": "",
            "instructions": "",
            "color": "",
            "owner": "",
            "memory": "global",
        },
    )
    ctx = _FakeContext(project_name="shared")

    result = get_context_memory_subdir(ctx)

    assert result is None
    assert ctx.get_data(CONTEXT_DATA_KEY_PROJECT) == "shared", (
        "Global-memory projects must NOT be deactivated on lookup."
    )
    assert captured_save == []
    assert captured_events == []


def test_no_active_project_returns_none_without_side_effect(
    isolated_repo, captured_save, captured_events
):
    ctx = _FakeContext(project_name=None)

    result = get_context_memory_subdir(ctx)

    assert result is None
    assert captured_save == []
    assert captured_events == []
