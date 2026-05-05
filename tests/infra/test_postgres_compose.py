# -*- coding: utf-8 -*-
"""
P0 — Tests d'infra Postgres + pgvector (ADR-007).

Ces tests valident que le compose `deploy/docker-compose.staging.yml` est
fonctionnel : Postgres 16 démarre, l'extension pgvector est chargée, les
schémas applicatifs sont créés, et l'init script `01_extensions.sql` a posé
le marker `korev_init_marker`.

Marker `infra` :
    * skipped par défaut (pytest standard ne les lance pas)
    * exécutés par CI dans un job dédié OU manuellement :
          pytest -m infra tests/infra/

Pré-requis :
    * Docker disponible sur la machine
    * `POSTGRES_STAGING_PASSWORD` exportée dans l'env (cf. deploy/.env.example)
    * Port 5433 (défaut) libre, ou `POSTGRES_STAGING_PORT` exporté

Garanties :
    * Aucun test ne touche à la prod.
    * Le compose staging est strictement isolé (réseau, volumes, ports).
    * `down -v` dans le teardown supprime tout.

Style : strict TDD anti-simplification (cf. ADR-006).
Aucun assert n'est conditionnel : si Docker n'est pas disponible, le test
est SKIP, pas marqué green.
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
SERVICE = "evidence-postgres-staging"
CONTAINER = "evidence-postgres-staging"

# Project name explicite : ANTI-INCIDENT.
# Sans `-p`, Docker Compose utilise le nom du répertoire courant comme
# project. Si ce projet partage un répertoire de travail avec la prod
# (ce qui peut arriver sur un VPS déployé), un `down --remove-orphans`
# pourrait toucher des containers prod « orphelins ». Le project name
# explicite garantit l'isolation totale.
PROJECT = "evidence-staging"

PG_USER = os.environ.get("POSTGRES_STAGING_USER", "evidence_staging")
PG_DB = os.environ.get("POSTGRES_STAGING_DB", "evidence_staging")
PG_PASSWORD = os.environ.get("POSTGRES_STAGING_PASSWORD", "korev_staging_test_pwd_P0")


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
    pytest.mark.skipif(
        not _docker_available(),
        reason="Docker non disponible — test infra skipped",
    ),
    pytest.mark.skipif(
        not COMPOSE_FILE.exists(),
        reason=f"Compose staging introuvable: {COMPOSE_FILE}",
    ),
]


@pytest.fixture(scope="module")
def staging_postgres():
    """
    Démarre le service Postgres staging via docker-compose, attend healthy,
    yield, puis tear down strict (`down -v`).

    Le fixture est `scope=module` pour partager le démarrage entre tous les
    tests de ce module — démarrer/arrêter Postgres entre chaque test serait
    trop coûteux et ne testerait pas le bon scope.
    """
    env = os.environ.copy()
    env["POSTGRES_STAGING_PASSWORD"] = PG_PASSWORD
    env["POSTGRES_STAGING_USER"] = PG_USER
    env["POSTGRES_STAGING_DB"] = PG_DB

    # CRITICAL: jamais `--remove-orphans` sans `-p` explicite.
    # Voir docstring de PROJECT plus haut + post-mortem dans
    # docs/migration-rdbms/P0_PRE_REQUIS_INFRA.md.
    subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE),
         "down", "-v"],
        env=env, check=False, capture_output=True,
    )

    up = subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE),
         "up", "-d", SERVICE],
        env=env, check=False, capture_output=True, text=True,
    )
    if up.returncode != 0:
        pytest.fail(
            f"docker compose up failed:\nSTDOUT:\n{up.stdout}\nSTDERR:\n{up.stderr}"
        )

    deadline = time.time() + 90.0
    healthy = False
    last_status = "unknown"
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", CONTAINER],
            capture_output=True, text=True, check=False,
        )
        last_status = result.stdout.strip()
        if last_status == "healthy":
            healthy = True
            break
        time.sleep(2)

    if not healthy:
        logs = subprocess.run(
            ["docker", "logs", "--tail", "100", CONTAINER],
            capture_output=True, text=True, check=False,
        )
        subprocess.run(
            ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE),
             "down", "-v"],
            env=env, check=False, capture_output=True,
        )
        pytest.fail(
            f"Postgres did not become healthy in 90s (last={last_status})\n"
            f"---LOGS---\n{logs.stdout}\n{logs.stderr}"
        )

    try:
        yield {"container": CONTAINER, "user": PG_USER, "db": PG_DB}
    finally:
        subprocess.run(
            ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE),
             "down", "-v"],
            env=env, check=False, capture_output=True,
        )


def _psql(container: str, user: str, db: str, sql: str) -> str:
    """Exécute du SQL via `docker exec` et retourne stdout (raise sinon)."""
    result = subprocess.run(
        ["docker", "exec", "-i", container,
         "psql", "-U", user, "-d", db, "-tAc", sql],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"psql failed (rc={result.returncode}):\n"
            f"SQL: {sql}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return result.stdout.strip()


# ============================================================================
# T1 — Postgres répond
# ============================================================================

def test_T1_postgres_is_reachable(staging_postgres):
    """Le SGBD répond à une requête triviale."""
    out = _psql(
        staging_postgres["container"],
        staging_postgres["user"],
        staging_postgres["db"],
        "SELECT 1;",
    )
    assert out == "1", f"Postgres ne répond pas '1' à SELECT 1 (got: {out!r})"


# ============================================================================
# T2 — pgvector chargé
# ============================================================================

def test_T2_pgvector_extension_loaded(staging_postgres):
    """L'extension pgvector est installée et chargée."""
    out = _psql(
        staging_postgres["container"],
        staging_postgres["user"],
        staging_postgres["db"],
        "SELECT extname FROM pg_extension WHERE extname = 'vector';",
    )
    assert out == "vector", (
        f"Extension pgvector absente (pg_extension.extname renvoie {out!r}). "
        f"Vérifier que l'image pgvector/pgvector:pg16 est bien utilisée et "
        f"que init/01_extensions.sql contient CREATE EXTENSION vector."
    )


def test_T3_pgvector_can_create_vector_column(staging_postgres):
    """pgvector permet de créer une colonne `vector(N)` (smoke fonctionnel)."""
    cont = staging_postgres["container"]
    user = staging_postgres["user"]
    db = staging_postgres["db"]

    _psql(cont, user, db, "DROP TABLE IF EXISTS infra_smoke_vec;")
    _psql(
        cont, user, db,
        "CREATE TABLE infra_smoke_vec (id INT PRIMARY KEY, e vector(3));",
    )
    _psql(cont, user, db,
          "INSERT INTO infra_smoke_vec VALUES (1, '[1,2,3]'), (2, '[4,5,6]');")

    out = _psql(
        cont, user, db,
        "SELECT id FROM infra_smoke_vec ORDER BY e <-> '[1,2,3]' LIMIT 1;",
    )
    assert out == "1", f"L1 distance ne renvoie pas le vecteur le plus proche (got {out!r})"

    _psql(cont, user, db, "DROP TABLE infra_smoke_vec;")


# ============================================================================
# T4 — Schémas applicatifs créés
# ============================================================================

def test_T4_application_schemas_present(staging_postgres):
    """Les schémas identity / chats / memory / audit / legal existent."""
    expected = {"identity", "chats", "memory", "audit", "legal"}
    out = _psql(
        staging_postgres["container"],
        staging_postgres["user"],
        staging_postgres["db"],
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name IN ('identity','chats','memory','audit','legal');",
    )
    found = {line.strip() for line in out.split("\n") if line.strip()}
    missing = expected - found
    assert not missing, (
        f"Schémas applicatifs manquants : {missing}. "
        f"Vérifier que init/01_extensions.sql a bien été appliqué."
    )


# ============================================================================
# T5 — Marker d'init enregistré
# ============================================================================

def test_T5_init_marker_recorded(staging_postgres):
    """Le marker `korev_init_marker` enregistre la phase et les extensions."""
    cont = staging_postgres["container"]
    user = staging_postgres["user"]
    db = staging_postgres["db"]

    out = _psql(
        cont, user, db,
        "SELECT phase || '|' || array_to_string(extensions, ',') "
        "FROM korev_init_marker ORDER BY id LIMIT 1;",
    )
    parts = out.split("|", 1)
    assert len(parts) == 2, f"Format inattendu : {out!r}"
    phase, exts = parts
    assert phase == "P0", f"phase attendue 'P0', obtenue {phase!r}"
    assert "vector" in exts, f"vector absent du marker (got {exts!r})"
    assert "pgcrypto" in exts, f"pgcrypto absent du marker (got {exts!r})"


# ============================================================================
# T6 — Aucune table métier en P0
# ============================================================================

def test_T6_no_business_table_in_P0(staging_postgres):
    """
    P0 ne crée aucune table métier dans les schémas applicatifs. Les premières
    tables seront introduites en P1 (identity) via des migrations dédiées.
    """
    out = _psql(
        staging_postgres["container"],
        staging_postgres["user"],
        staging_postgres["db"],
        "SELECT count(*)::text FROM information_schema.tables "
        "WHERE table_schema IN ('identity','chats','memory','audit','legal');",
    )
    assert out == "0", (
        f"P0 ne doit pas créer de table métier (trouvé : {out}). "
        f"Si une table apparaît, c'est qu'une phase ultérieure a fuité dans P0."
    )
