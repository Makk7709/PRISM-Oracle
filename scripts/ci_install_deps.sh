#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# Installation des dépendances CI (alignée sur .github/workflows/tests.yml).
#
# Usage:
#   ./scripts/ci_install_deps.sh [répertoire_venv]
#
# Par défaut crée/utilise .venv-ci311 à la racine du projet.
# Sur macOS, duckduckgo-search peut échouer (pyreqwest-impersonate / Rust) ;
# le script installe alors requirements sans cette ligne (cf. CI_EXECUTION_REPORT).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${1:-$ROOT_DIR/.venv-ci311}"
PYTHON="${PYTHON:-python3.11}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "[ABORT] $PYTHON introuvable. Installez Python 3.11+ (ex: brew install python@3.11)."
    exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "[ABORT] uv introuvable. Installez uv (https://docs.astral.sh/uv/) ou utilisez le workflow GitHub Actions."
    exit 2
fi

echo "[INFO] Création venv: $VENV_DIR ($($PYTHON --version))"
"$PYTHON" -m venv "$VENV_DIR"
PY="$VENV_DIR/bin/python"

install_req() {
    local file="$1"
    if uv pip install -r "$file" -p "$PY" 2>/dev/null; then
        echo "[OK] $file"
        return 0
    fi
    echo "[WARN] Échec install groupé pour $file — retry sans duckduckgo-search (macOS)..."
    grep -v '^duckduckgo-search' "$file" > /tmp/ci-req-stripped.txt
    uv pip install -r /tmp/ci-req-stripped.txt -p "$PY"
    echo "[OK] $file (sans duckduckgo-search)"
}

install_req "$ROOT_DIR/requirements.txt"
uv pip install -r "$ROOT_DIR/requirements2.txt" -p "$PY"
uv pip install -r "$ROOT_DIR/requirements.dev.txt" -p "$PY"

echo "[INFO] Playwright chromium (optionnel, peut prendre plusieurs minutes)..."
"$PY" -m playwright install chromium 2>/dev/null || echo "[WARN] playwright install chromium ignoré"

echo "[DONE] Environnement prêt: $PY"
echo "       Exemple: PYTHON=$PY ./scripts/run_tests.sh scope"
