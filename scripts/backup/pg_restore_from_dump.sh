#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  KOREV EVIDENCE — pg_restore depuis dump pg_dump_daily (P0, ADR-007)        ║
# ║                                                                              ║
# ║  Restaure un dump genere par scripts/backup/pg_dump_daily.sh dans un        ║
# ║  container Postgres cible. Verifie l'integrite du gzip, valide le SHA-256   ║
# ║  contre le manifeste, applique le dump avec ON_ERROR_STOP=1 (fail-loud      ║
# ║  conformement a ADR-006) et chronometre l'operation.                        ║
# ║                                                                              ║
# ║  Usage :                                                                     ║
# ║    ./scripts/backup/pg_restore_from_dump.sh <DUMP_FILE> [--container NAME]  ║
# ║                                                                              ║
# ║  Variables d'env :                                                           ║
# ║    KOREV_PG_CONTAINER  container cible (defaut: evidence-postgres)           ║
# ║    KOREV_PG_USER       user Postgres   (defaut: evidence)                   ║
# ║    KOREV_PG_DB         base cible      (defaut: evidence)                   ║
# ║                                                                              ║
# ║  Le dump DOIT avoir ete produit avec --clean --if-exists pour pouvoir       ║
# ║  s'appliquer sur une base deja initialisee (sinon conflit de PK sur les     ║
# ║  tables creees par le init script docker-entrypoint).                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

CONTAINER="${KOREV_PG_CONTAINER:-evidence-postgres}"
DB_USER="${KOREV_PG_USER:-evidence}"
DB_NAME="${KOREV_PG_DB:-evidence}"

DUMP_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --container) CONTAINER="$2"; shift 2 ;;
        --user) DB_USER="$2"; shift 2 ;;
        --db) DB_NAME="$2"; shift 2 ;;
        -h|--help) sed -n '1,25p' "$0"; exit 0 ;;
        -*)
            echo "Unknown flag: $1" >&2
            exit 64
            ;;
        *)
            if [[ -z "${DUMP_FILE}" ]]; then
                DUMP_FILE="$1"
            else
                echo "Unexpected arg: $1" >&2
                exit 64
            fi
            shift
            ;;
    esac
done

if [[ -z "${DUMP_FILE}" ]]; then
    echo "[restore] FATAL: dump file is required" >&2
    sed -n '15,18p' "$0" >&2
    exit 64
fi

if [[ ! -f "${DUMP_FILE}" ]]; then
    echo "[restore] FATAL: dump file not found: ${DUMP_FILE}" >&2
    exit 2
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
    echo "[restore] FATAL: container ${CONTAINER} not running" >&2
    exit 2
fi

echo "[restore] gzip integrity check..."
if ! gunzip --test "${DUMP_FILE}" 2>/dev/null; then
    echo "[restore] FATAL: gzip integrity check failed" >&2
    exit 3
fi

# Verification optionnelle SHA-256 si MANIFEST.sha256 est present
MANIFEST_DIR=$(dirname "${DUMP_FILE}")
MANIFEST="${MANIFEST_DIR}/MANIFEST.sha256"
if [[ -f "${MANIFEST}" ]]; then
    EXPECTED=$(grep "  $(basename "${DUMP_FILE}")  " "${MANIFEST}" \
        | awk '{print $1}' | head -1)
    if [[ -n "${EXPECTED}" ]]; then
        ACTUAL=$(sha256sum "${DUMP_FILE}" | awk '{print $1}')
        if [[ "${ACTUAL}" != "${EXPECTED}" ]]; then
            echo "[restore] FATAL: SHA-256 mismatch (expected=${EXPECTED}, actual=${ACTUAL})" >&2
            exit 4
        fi
        echo "[restore] SHA-256 manifest verified: ${ACTUAL:0:12}..."
    fi
fi

echo "[restore] Applying dump to ${CONTAINER} (db=${DB_NAME}, user=${DB_USER})..."
T_START=$(date -u +%s)

# ON_ERROR_STOP=1 = fail-loud strict (cf. ADR-006).
# La moindre erreur SQL fait echouer le restore et exit code != 0.
# `|| RC=$?` capture le code de retour SANS declencher `set -e` (qui
# tuerait le script avant la ligne RC=$?).
RC=0
gunzip -c "${DUMP_FILE}" \
    | docker exec -i "${CONTAINER}" psql \
        --set ON_ERROR_STOP=1 \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
    > /tmp/pg_restore_stdout.log 2> /tmp/pg_restore_stderr.log || RC=$?

T_END=$(date -u +%s)
DURATION=$((T_END - T_START))

if [[ ${RC} -ne 0 ]]; then
    echo "[restore] FATAL: psql restore failed (rc=${RC}, duration=${DURATION}s)" >&2
    echo "--- stderr ---" >&2
    tail -30 /tmp/pg_restore_stderr.log >&2 || true
    exit 5
fi

if grep -qiE 'ERROR|FATAL' /tmp/pg_restore_stderr.log 2>/dev/null; then
    echo "[restore] FATAL: SQL errors detected in stderr (incomplete restore?)" >&2
    grep -iE 'ERROR|FATAL' /tmp/pg_restore_stderr.log | head -10 >&2
    exit 6
fi

echo "[restore] OK — duration: ${DURATION}s"
echo "[restore] Use the following query to verify:"
echo "  docker exec ${CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \"SELECT phase, applied_at FROM korev_init_marker ORDER BY id;\""
