#!/usr/bin/env bash
#
# Production deploy wrapper for KOREV Evidence (OVH).
#
# Exports the build-time git metadata (GIT_COMMIT / GIT_BRANCH / BUILD_DATE) so
# the resulting image stamps the real deployed commit into VERSION.json and the
# OCI labels. Running `docker compose up -d --build` directly leaves these empty
# and VERSION.json keeps the stale repo value — always deploy through this script.
#
# Usage (on the server, from the repo root):
#   git pull --ff-only origin main
#   ./scripts/deploy_prod.sh                 # build + (re)start
#   ./scripts/deploy_prod.sh evidence-backend  # restrict to one service
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="deploy/docker-compose.yml"

GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo "")"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export GIT_COMMIT GIT_BRANCH BUILD_DATE

if [ -z "$GIT_COMMIT" ]; then
    echo "[deploy_prod] WARNING: not a git checkout — VERSION.json will not be stamped." >&2
fi

echo "[deploy_prod] commit=${GIT_COMMIT:0:8} branch=${GIT_BRANCH} build_date=${BUILD_DATE}"
echo "[deploy_prod] building + starting (postgres 'db' profile stays OFF)…"

docker compose -f "$COMPOSE_FILE" up -d --build "$@"

echo "[deploy_prod] done. Container status:"
docker compose -f "$COMPOSE_FILE" ps
