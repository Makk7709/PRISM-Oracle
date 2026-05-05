#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  KOREV EVIDENCE — Snapshot pre-migration (P0, ADR-007)                      ║
# ║                                                                              ║
# ║  Capture un état de référence IMMUTABLE de la prod avant chaque phase de    ║
# ║  migration RDBMS. À exécuter sur le VPS OVH avec un user disposant de       ║
# ║  l'accès Docker (ubuntu, ou root).                                          ║
# ║                                                                              ║
# ║  Le snapshot contient :                                                      ║
# ║    1. git_HEAD.txt          : commit courant du repo de prod                 ║
# ║    2. docker_ps.txt         : état des containers                            ║
# ║    3. docker_volumes.txt    : liste des volumes Docker                       ║
# ║    4. users.json + .live    : copie de l'état utilisateurs                   ║
# ║    5. volumes_sizes.txt     : taille de chaque volume métier                 ║
# ║    6. <volume>.tar.gz       : tarball par volume métier                      ║
# ║                                                                              ║
# ║  Usage :                                                                     ║
# ║    ./scripts/backup/snapshot_pre_migration.sh [--label LABEL] [--no-tar]    ║
# ║                                                                              ║
# ║  Options :                                                                   ║
# ║    --label LABEL   Étiquette ajoutée au nom du dossier (ex: pre-P1)          ║
# ║    --no-tar        Skip le tar des volumes (snapshot léger / smoke)          ║
# ║    --keep N        Nombre de snapshots à conserver (défaut: 10)              ║
# ║                                                                              ║
# ║  Sortie : /home/ubuntu/snapshots/<label>-<YYYYMMDD-HHMMSS>/                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

LABEL="pre-migration"
DO_TAR=1
KEEP=10
REPO_DIR="${KOREV_REPO_DIR:-/home/ubuntu/PRISM-Oracle}"
SNAP_BASE="${KOREV_SNAPSHOT_BASE:-/home/ubuntu/snapshots}"
# Volumes inclus dans le tar (donnees critiques pour rollback)
VOLUMES=(evidence-tmp evidence-shared evidence-memory evidence-data evidence-audit)
# Volumes seulement mesures (taille uniquement) — exclus du tar.
# evidence-logs : ne contient que des logs applicatifs reconstruisibles ;
# inclure dans le tar gonflerait le snapshot inutilement (138 MB sur prod).
MEASURE_VOLUMES=("${VOLUMES[@]}" evidence-logs)

while [[ $# -gt 0 ]]; do
    case "$1" in
        --label) LABEL="$2"; shift 2 ;;
        --no-tar) DO_TAR=0; shift ;;
        --keep) KEEP="$2"; shift 2 ;;
        -h|--help) sed -n '1,30p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 64 ;;
    esac
done

TS=$(date -u +%Y%m%d-%H%M%S)
SNAP_DIR="${SNAP_BASE}/${LABEL}-${TS}"

echo "[snapshot] Creating ${SNAP_DIR}"
mkdir -p "${SNAP_DIR}"

cd "${REPO_DIR}"
git log -1 --format='%H %s' > "${SNAP_DIR}/git_HEAD.txt"
git status --short > "${SNAP_DIR}/git_status.txt" || true

docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' > "${SNAP_DIR}/docker_ps.txt"
docker volume ls > "${SNAP_DIR}/docker_volumes.txt"

if [[ -f "${REPO_DIR}/deploy/users.json" ]]; then
    cp "${REPO_DIR}/deploy/users.json" "${SNAP_DIR}/users.json"
fi
docker exec evidence-backend cat /app/deploy/users.json \
    > "${SNAP_DIR}/users.json.live" 2>/dev/null || true

{
    for v in "${MEASURE_VOLUMES[@]}"; do
        sz=$(docker run --rm -v "${v}:/d" alpine sh -c 'du -sh /d 2>/dev/null' 2>/dev/null \
            | awk '{print $1}')
        echo "${v} ${sz}"
    done
} > "${SNAP_DIR}/volumes_sizes.txt"

if [[ ${DO_TAR} -eq 1 ]]; then
    for v in "${VOLUMES[@]}"; do
        echo "[snapshot] tar ${v}..."
        docker run --rm \
            -v "${v}:/data:ro" \
            -v "${SNAP_DIR}:/backup" \
            alpine tar czf "/backup/${v}.tar.gz" -C /data . 2>&1 | tail -3
    done
    echo "[snapshot] tar done"
fi

# SHA-256 manifest pour intégrité
sha256sum "${SNAP_DIR}"/*.* 2>/dev/null \
    | sort > "${SNAP_DIR}/MANIFEST.sha256"

echo "[snapshot] complete: ${SNAP_DIR}"
ls -lah "${SNAP_DIR}"

# Rotation : on garde les ${KEEP} plus récents portant le même label
echo "[snapshot] rotation (keep=${KEEP}, label=${LABEL})"
ls -1dt "${SNAP_BASE}/${LABEL}-"* 2>/dev/null \
    | tail -n +$((KEEP + 1)) \
    | while read -r old; do
        echo "[snapshot] removing ${old}"
        rm -rf "${old}"
    done

echo "[snapshot] OK"
