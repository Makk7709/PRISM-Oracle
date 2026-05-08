#!/usr/bin/env bash
set -e
echo "=== KOREV Evidence — Capture preuve A12 (build Docker) ==="
echo "Date d'execution : $(date '+%Y-%m-%d %H:%M:%S %z')"
echo "Machine : $(uname -snm)"
echo "HEAD Git : $(git rev-parse --short HEAD)"
echo "Docker version : $(docker --version)"
echo "Compose version : $(docker compose version 2>&1 | head -1)"
echo
echo "=== Pre-requis : Docker Desktop demarre ==="
docker info 2>&1 | head -5
echo
echo "=== docker compose config (validation syntaxe) ==="
cd "$(git rev-parse --show-toplevel)/deploy"
docker compose -f docker-compose.yml config --quiet 2>&1 | tail -5
echo "Exit code config : $?"
echo
echo "=== docker compose build backend ==="
docker compose -f docker-compose.yml build backend 2>&1 | tail -30
echo "Exit code build : $?"
echo
echo "=== Image construite ==="
docker images | grep -i korev | head -5 || true
