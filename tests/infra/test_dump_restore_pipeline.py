# -*- coding: utf-8 -*-
"""
P0 — Test d'infra du pipeline dump -> restore.

Ce test valide que le couple `pg_dump_daily.sh` + `pg_restore_from_dump.sh`
permet de restaurer un dump sur une base FRAÎCHE (post init script
`docker-entrypoint`) sans erreur SQL silencieuse.

Origine : DEF-8 identifie en P0 (5 mai 2026). Le dump initial omettait
`--clean --if-exists`, ce qui provoquait un conflit de PK lors du restore
sur une base qui contenait deja la table `korev_init_marker` cree par le
init script. Le restore semblait reussir mais les donnees applicatives
n'etaient PAS restaurees (fail-silent — interdit par ADR-006).

Le test cree des donnees temoins, dump, down -v, up neuf, restore, puis
verifie que TOUTES les donnees temoins sont presentes.

Marker `infra` + `slow` (3 dump/restore cycles incluant 2 starts Postgres).

Style : strict TDD anti-simplification (cf. ADR-006).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "deploy" / "docker-compose.staging.yml"
DUMP_SCRIPT = REPO_ROOT / "scripts" / "backup" / "pg_dump_daily.sh"
RESTORE_SCRIPT = REPO_ROOT / "scripts" / "backup" / "pg_restore_from_dump.sh"
SERVICE = "evidence-postgres-staging"
CONTAINER = "evidence-postgres-staging"
PROJECT = "evidence-staging"

PG_USER = os.environ.get("POSTGRES_STAGING_USER", "evidence_staging")
PG_DB = os.environ.get("POSTGRES_STAGING_DB", "evidence_staging")
PG_PASSWORD = os.environ.get("POSTGRES_STAGING_PASSWORD", "korev_dump_restore_test_pwd")


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5, check=False
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


pytestmark = [
    pytest.mark.infra,
    pytest.mark.slow,
    pytest.mark.skipif(
        not _docker_available(),
        reason="Docker non disponible — test infra skipped",
    ),
    pytest.mark.skipif(
        not COMPOSE_FILE.exists(),
        reason=f"Compose staging introuvable: {COMPOSE_FILE}",
    ),
    pytest.mark.skipif(
        not DUMP_SCRIPT.exists() or not RESTORE_SCRIPT.exists(),
        reason="Backup/restore scripts manquants",
    ),
]


def _env() -> dict:
    e = os.environ.copy()
    e["POSTGRES_STAGING_PASSWORD"] = PG_PASSWORD
    e["POSTGRES_STAGING_USER"] = PG_USER
    e["POSTGRES_STAGING_DB"] = PG_DB
    return e


def _compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE), *args],
        env=_env(), check=False, capture_output=True, text=True,
    )


def _wait_healthy(timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", CONTAINER],
            capture_output=True, text=True, check=False,
        )
        if result.stdout.strip() == "healthy":
            return
        time.sleep(2)
    raise RuntimeError(f"{CONTAINER} did not become healthy in {timeout}s")


def _psql(sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", "-i", CONTAINER,
         "psql", "-U", PG_USER, "-d", PG_DB, "-tAc", sql],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"psql failed (rc={result.returncode}): {result.stderr}"
        )
    return result.stdout.strip()


@pytest.fixture(scope="module")
def staging_lifecycle(tmp_path_factory):
    """
    Provisionne un staging propre et fournit un dossier pour les dumps.
    Le teardown est strict (`down -v`).
    """
    backup_dir = tmp_path_factory.mktemp("pg_backups")
    _compose("down", "-v")
    up = _compose("up", "-d", SERVICE)
    if up.returncode != 0:
        pytest.fail(f"up failed: {up.stdout}\n{up.stderr}")
    _wait_healthy()
    try:
        yield {"backup_dir": backup_dir}
    finally:
        _compose("down", "-v")


# ============================================================================
# T7 — pipeline dump -> restore preserve toutes les donnees
# ============================================================================

def test_T7_dump_then_restore_preserves_all_data(staging_lifecycle):
    """
    Verifie que le pipeline dump_daily.sh -> down -v -> up -> restore_from_dump.sh
    restaure toutes les donnees, y compris une ligne `korev_init_marker`
    insere apres le init script (cas DEF-8).
    """
    # 1) Insertion de donnees temoins
    _psql(
        "INSERT INTO public.korev_init_marker (phase, extensions, schemas) "
        "VALUES ('TEST_T7_BEFORE_DUMP', ARRAY['vector'], ARRAY['identity']);"
    )
    _psql(
        "CREATE TABLE chats.test_t7_table ("
        "id SERIAL PRIMARY KEY, "
        "payload TEXT NOT NULL, "
        "embedding vector(3));"
    )
    _psql(
        "INSERT INTO chats.test_t7_table (payload, embedding) VALUES "
        "('alpha', '[1,2,3]'), ('beta', '[4,5,6]'), ('gamma', '[7,8,9]');"
    )

    # 2) Dump via pg_dump_daily.sh
    backup_dir = str(staging_lifecycle["backup_dir"])
    dump_env = _env()
    dump_env.update({
        "KOREV_PG_CONTAINER": CONTAINER,
        "KOREV_PG_USER": PG_USER,
        "KOREV_PG_DB": PG_DB,
        "KOREV_PG_BACKUP_DIR": backup_dir,
        "KOREV_PG_RETENTION_DAYS": "30",
    })
    dump_result = subprocess.run(
        ["bash", str(DUMP_SCRIPT)],
        env=dump_env, check=False, capture_output=True, text=True,
    )
    assert dump_result.returncode == 0, (
        f"pg_dump_daily.sh failed: {dump_result.stdout}\n{dump_result.stderr}"
    )

    dumps = sorted(Path(backup_dir).glob(f"{PG_DB}-*.sql.gz"))
    assert len(dumps) == 1, f"Expected 1 dump, found {len(dumps)}"
    dump_file = dumps[0]
    assert dump_file.stat().st_size > 0, "Dump is empty"

    # 3) Tear down complet (down -v supprime le volume = perte totale)
    down = _compose("down", "-v")
    assert down.returncode == 0, f"down failed: {down.stdout}\n{down.stderr}"

    # 4) Up neuf (init script s'execute donc korev_init_marker existe deja)
    up = _compose("up", "-d", SERVICE)
    assert up.returncode == 0, f"up failed: {up.stdout}\n{up.stderr}"
    _wait_healthy()

    # Sanity check : la base est "fraiche" (post-init), 1 seul marker P0
    fresh_markers = _psql("SELECT count(*) FROM public.korev_init_marker;")
    assert fresh_markers == "1", (
        f"Expected fresh DB with 1 marker (init), found {fresh_markers}. "
        f"Init script may not have run."
    )
    fresh_phase = _psql("SELECT phase FROM public.korev_init_marker;")
    assert fresh_phase == "P0", (
        f"Fresh DB marker should be P0, got {fresh_phase!r}"
    )

    # 5) Restore via pg_restore_from_dump.sh
    restore_env = _env()
    restore_env.update({
        "KOREV_PG_CONTAINER": CONTAINER,
        "KOREV_PG_USER": PG_USER,
        "KOREV_PG_DB": PG_DB,
    })
    restore_result = subprocess.run(
        ["bash", str(RESTORE_SCRIPT), str(dump_file)],
        env=restore_env, check=False, capture_output=True, text=True,
    )
    assert restore_result.returncode == 0, (
        f"pg_restore_from_dump.sh failed: "
        f"STDOUT:{restore_result.stdout}\nSTDERR:{restore_result.stderr}"
    )

    # 6) Verification : TOUTES les donnees doivent etre presentes
    # 6a) Le marker TEST_T7_BEFORE_DUMP est present (le piege de DEF-8)
    markers = _psql(
        "SELECT phase FROM public.korev_init_marker ORDER BY phase;"
    )
    marker_set = set(line.strip() for line in markers.split("\n") if line.strip())
    assert "TEST_T7_BEFORE_DUMP" in marker_set, (
        f"DEF-8 regression : la ligne 'TEST_T7_BEFORE_DUMP' insere AVANT le "
        f"dump n'est PAS presente apres restore. Markers trouves: {marker_set}. "
        f"Cela signifie que le restore a echoue silencieusement sur le conflit "
        f"de PK avec le init script. Verifier que pg_dump utilise "
        f"--clean --if-exists et que le restore utilise ON_ERROR_STOP=1."
    )

    # 6b) test_t7_table existe et contient les 3 lignes
    payloads = _psql(
        "SELECT payload FROM chats.test_t7_table ORDER BY payload;"
    )
    payload_set = set(line.strip() for line in payloads.split("\n") if line.strip())
    assert payload_set == {"alpha", "beta", "gamma"}, (
        f"Payloads attendus: alpha,beta,gamma. Obtenus: {payload_set}"
    )

    # 6c) La colonne vector(3) est preservee (pgvector reconnait le type)
    closest = _psql(
        "SELECT payload FROM chats.test_t7_table "
        "ORDER BY embedding <-> '[1,2,3]' LIMIT 1;"
    )
    assert closest == "alpha", (
        f"L1 distance attendait 'alpha' (closest a [1,2,3]), got {closest!r}"
    )
