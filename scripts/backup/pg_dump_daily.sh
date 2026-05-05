#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  KOREV EVIDENCE — pg_dump quotidien (P0, ADR-007)                           ║
# ║                                                                              ║
# ║  Dump compressé du SGBD Postgres avec rétention locale et empreinte         ║
# ║  SHA-256. À placer dans cron (root, 03h00 par exemple) :                    ║
# ║                                                                              ║
# ║    0 3 * * * /home/ubuntu/PRISM-Oracle/scripts/backup/pg_dump_daily.sh      ║
# ║                                                                              ║
# ║  Variables d'env utilisables (sinon valeurs par défaut documentées) :        ║
# ║    KOREV_PG_CONTAINER       container ciblé (défaut: evidence-postgres)     ║
# ║    KOREV_PG_USER            user Postgres   (défaut: evidence)               ║
# ║    KOREV_PG_DB              base à dumper   (défaut: evidence)               ║
# ║    KOREV_PG_BACKUP_DIR      dir local       (défaut: /home/ubuntu/backups/pg)║
# ║    KOREV_PG_RETENTION_DAYS  rétention       (défaut: 30)                     ║
# ║                                                                              ║
# ║  P0 : pas d'upload externe (Backblaze/S3) — ajouté en P1 quand des données  ║
# ║  réelles seront stockées.                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

CONTAINER="${KOREV_PG_CONTAINER:-evidence-postgres}"
DB_USER="${KOREV_PG_USER:-evidence}"
DB_NAME="${KOREV_PG_DB:-evidence}"
BACKUP_DIR="${KOREV_PG_BACKUP_DIR:-/home/ubuntu/backups/pg}"
RETENTION_DAYS="${KOREV_PG_RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
    echo "[pg_dump] FATAL: container ${CONTAINER} not running" >&2
    exit 2
fi

TS=$(date -u +%Y%m%d-%H%M%S)
OUT="${BACKUP_DIR}/${DB_NAME}-${TS}.sql.gz"
TMP="${BACKUP_DIR}/.${DB_NAME}-${TS}.sql.gz.tmp"

echo "[pg_dump] Dumping ${DB_NAME} from ${CONTAINER}..."
# `--clean --if-exists` rend le dump restaurable sur une base deja
# initialisee : il prefixe chaque CREATE par un DROP IF EXISTS. Sans cela,
# un restore sur une base "fraiche" (avec le init script docker-entrypoint
# deja execute) echoue silencieusement sur les conflits de cle primaire,
# ne restaurant qu'une partie des donnees. Ce comportement contrevient a
# ADR-006 (fail-loud) et a ete identifie en P0.
#
# `--no-owner` et `--no-acl` empechent le dump de tenter d'attribuer des
# proprietaires ou des roles qui pourraient ne pas exister sur la cible.
docker exec "${CONTAINER}" pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --format=plain \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
    --quote-all-identifiers \
    | gzip -c > "${TMP}"

mv "${TMP}" "${OUT}"

SHA=$(sha256sum "${OUT}" | awk '{print $1}')
SIZE=$(stat -c %s "${OUT}" 2>/dev/null || stat -f %z "${OUT}")
echo "${SHA}  $(basename "${OUT}")  ${SIZE} bytes" >> "${BACKUP_DIR}/MANIFEST.sha256"

echo "[pg_dump] OK: ${OUT} (${SIZE} bytes, sha256=${SHA:0:12}...)"

# CRITICAL — vérification d'intégrité AVANT toute opération de rétention.
# Si le nouveau dump est corrompu, on doit conserver les anciens à tout prix.
if ! gunzip --test "${OUT}" 2>/dev/null; then
    echo "[pg_dump] FATAL: integrity check failed for ${OUT} — keeping old backups" >&2
    exit 3
fi
echo "[pg_dump] integrity check OK"

# Rétention : suppression des dumps plus vieux que RETENTION_DAYS
# (UNIQUEMENT après que le nouveau dump est validé)
find "${BACKUP_DIR}" -maxdepth 1 -name "${DB_NAME}-*.sql.gz" \
    -mtime "+${RETENTION_DAYS}" -print -delete

echo "[pg_dump] retention check OK (>${RETENTION_DAYS} days removed)"
