#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# Vérification complète de l'audit KOREV Evidence
# Usage: ./scripts/audit_verify.sh [--smoke] [--verbose]
#
# Options:
#   --smoke    Exécute aussi les tests minimaux (pytest)
#   --verbose  Affiche plus de détails

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_PATH="${AUDIT_PATH:-$ROOT_DIR/docs/KOREV_Evidence_Audit.md}"

# Couleurs (si terminal)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Options
RUN_SMOKE=0
VERBOSE=0

for arg in "$@"; do
    case $arg in
        --smoke)
            RUN_SMOKE=1
            ;;
        --verbose)
            VERBOSE=1
            ;;
    esac
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  KOREV Evidence — Audit Verification Pipeline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "[INFO] Audit: ${AUDIT_PATH}"
echo ""

FAIL_COUNT=0
PASS_COUNT=0

# Étape 1: Lint documentaire
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ 1/3 Lint documentaire (règles A-D)                                     │"
echo "└─────────────────────────────────────────────────────────────────────────┘"

if python3 "$ROOT_DIR/scripts/audit_lint.py" "$AUDIT_PATH"; then
    PASS_COUNT=$((PASS_COUNT + 1))
else
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Étape 2: Vérification des fichiers référencés
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ 2/3 Vérification des fichiers référencés                               │"
echo "└─────────────────────────────────────────────────────────────────────────┘"

# Extraire les chemins de fichiers référencés dans l'audit
FILE_REFS=$(grep -oE '\`[a-zA-Z0-9_/]+\.(py|md|yml|yaml|sh)\`' "$AUDIT_PATH" 2>/dev/null | tr -d '`' | sort -u || true)
MISSING_FILES=0
FOUND_FILES=0

for ref in $FILE_REFS; do
    # Normaliser le chemin
    if [[ "$ref" == python/* ]] || [[ "$ref" == tests/* ]] || [[ "$ref" == agents/* ]] || [[ "$ref" == deploy/* ]] || [[ "$ref" == docker/* ]]; then
        full_path="$ROOT_DIR/$ref"
        if [[ -f "$full_path" ]]; then
            FOUND_FILES=$((FOUND_FILES + 1))
            [[ $VERBOSE -eq 1 ]] && echo "  ✓ $ref"
        else
            MISSING_FILES=$((MISSING_FILES + 1))
            echo "  ✗ $ref (introuvable)"
        fi
    fi
done

if [[ $MISSING_FILES -eq 0 ]]; then
    echo "[PASS] Tous les fichiers référencés existent ($FOUND_FILES fichiers)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "[WARN] $MISSING_FILES fichier(s) référencé(s) introuvable(s) (sur $FOUND_FILES trouvés)"
    # Avertissement, pas bloquant
fi
echo ""

# Étape 3: Tests smoke (optionnel)
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ 3/3 Tests smoke (optionnel)                                            │"
echo "└─────────────────────────────────────────────────────────────────────────┘"

if [[ $RUN_SMOKE -eq 1 ]] || [[ "${AUDIT_RUN_TESTS:-0}" == "1" ]]; then
    SMOKE_TESTS=(
        "tests/test_prism_tally_quorum.py"
        "tests/test_router_determinism.py"
        "tests/test_injection_handling.py"
    )
    
    SMOKE_PASS=0
    SMOKE_FAIL=0
    
    for test in "${SMOKE_TESTS[@]}"; do
        test_path="$ROOT_DIR/$test"
        if [[ -f "$test_path" ]]; then
            echo "[RUN] $test"
            if python3 -m pytest "$test_path" -v --tb=short 2>/dev/null; then
                SMOKE_PASS=$((SMOKE_PASS + 1))
            else
                SMOKE_FAIL=$((SMOKE_FAIL + 1))
            fi
        else
            echo "[SKIP] $test (fichier absent)"
        fi
    done
    
    if [[ $SMOKE_FAIL -eq 0 ]]; then
        echo "[PASS] Tests smoke: $SMOKE_PASS test(s) OK"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "[FAIL] Tests smoke: $SMOKE_FAIL échec(s)"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
else
    echo "[SKIP] Tests smoke désactivés (utiliser --smoke ou AUDIT_RUN_TESTS=1)"
fi
echo ""

# Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RÉSUMÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN}[PASS]${NC} Audit verification complète"
    echo "       $PASS_COUNT vérification(s) réussie(s), 0 échec"
    exit 0
else
    echo -e "${RED}[FAIL]${NC} Audit verification échouée"
    echo "       $PASS_COUNT réussie(s), $FAIL_COUNT échec(s)"
    exit 1
fi
