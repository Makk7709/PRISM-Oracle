#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════════
#  KOREV Oracle — Test Runner
#
#  Point d'entrée unique et reproductible pour exécuter la suite de tests, avec
#  les variables d'environnement correctes et une détection de version Python.
#
#  Usage:
#    ./scripts/run_tests.sh <cible> [args pytest additionnels...]
#
#  Cibles:
#    scope     Périmètre consensus / gate / criticality router (baseline verte).
#              Tourne en local sur Python 3.9+. C'est le filet de sécurité minimal
#              à exécuter avant tout commit touchant ces modules.
#    fast      Gate rapide CI (~2-10s) — contrats PRISM, router, harness.
#    local     Tout ce qui est exécutable hors infra (Redis/Docker) ET hors
#              modules nécessitant Python 3.10+ ou des deps optionnelles absentes.
#              Utilise --continue-on-collection-errors pour ne pas abandonner la
#              session sur les fichiers non importables localement.
#    security  Suite sécurité (tests/security/). Certains cas nécessitent Redis.
#    unit      Gate unitaire hermétique (hors e2e/integration/infra/property/slow,
#              hors reasoning_engine et dockerfile OCR). Cf. CI_EXECUTION_REPORT.
#    blocking  Enchaîne scope + fast + security (gates merge bloquants, verts).
#    extended  e2e + integration + infra + property (non bloquant par défaut).
#    full      FULL GATE canonique: `pytest -q` sur toute la suite.
#              ⚠️ Nécessite Python 3.10+ ET toutes les deps (requirements*.txt).
#              Contient des tests non hermétiques → peut TIMEOUT (cf. rapport CI).
#    docker    Lance `full` à l'intérieur de l'image runtime (Python 3.11+/Kali),
#              qui est le SEUL contexte où la full-suite est probante (= prod).
#
#  Variables d'environnement posées automatiquement (mode test déterministe):
#    EVIDENCE_ENV=development        → autorise les chemins de dev/test
#    CONSENSUS_SIMULATION=true       → vote consensus simulé (pas d'appel LLM réel)
#
#  Exemples:
#    ./scripts/run_tests.sh scope
#    ./scripts/run_tests.sh fast -x
#    ./scripts/run_tests.sh local 2>&1 | tee /tmp/korev_local_suite.log
#    ./scripts/run_tests.sh docker
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Couleurs (si terminal)
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# Interpréteur Python (surchargeable: PYTHON=python3.11 ./scripts/run_tests.sh ...)
PYTHON="${PYTHON:-python3}"
export PYTHON

# Environnement de test déterministe
export EVIDENCE_ENV="${EVIDENCE_ENV:-development}"
export CONSENSUS_SIMULATION="${CONSENSUS_SIMULATION:-true}"

# Périmètre "scope": modules consensus / gate / criticality router.
# Cette liste est la baseline verte garantie en local (cf. docs/reports/PROD_READINESS_AUDIT.md).
SCOPE_TESTS=(
    tests/test_anti_bypass.py
    tests/test_gate_validate_uses_original_query.py
    tests/test_gate_correlation_id_chain.py
    tests/test_user_entry_gate.py
    tests/test_final_output_claim_integrity.py
    tests/test_research_bypass.py
    tests/test_medical_agent_hardening.py
    tests/test_consensus_entrypoint_delegation.py
    tests/test_consensus_fail_soft_envelope.py
    tests/test_consensus_no_simulation_prod.py
    tests/test_observability_logs.py
    tests/test_dossier_confidence_calculated.py
    tests/test_finalize_proposal_idempotent.py
)

# Gate rapide hermétique. NB: tests/test_reasoning_engine.py est listé comme
# "fast gate" dans pytest.ini mais n'est PAS hermétique (appel réseau/LLM → hang
# en l'absence de provider mocké). Il est volontairement exclu de cette cible.
FAST_TESTS=(
    tests/test_prism_contract.py
    tests/test_prism_tally_quorum.py
    tests/test_metacognition_policy.py
    tests/test_harness_integrity.py
)

py_minor() {
    "$PYTHON" -c 'import sys; print(sys.version_info[1])'
}

check_python_310() {
    local minor
    minor="$(py_minor)"
    if [[ "$minor" -lt 10 ]]; then
        echo -e "${YELLOW}[WARN]${NC} $($PYTHON --version 2>&1) détecté."
        echo -e "${YELLOW}      La full-suite référence du code Python 3.10+ (syntaxe 'X | None').${NC}"
        echo -e "${YELLOW}      Des erreurs de COLLECTION (et non des régressions) sont attendues.${NC}"
        echo -e "${YELLOW}      Validation probante: cible 'docker' (Python 3.11+/Kali) ou CI 3.11+.${NC}"
        echo ""
        return 1
    fi
    return 0
}

TARGET="${1:-scope}"
shift || true
# Bash 3.2 (macOS) : sous `set -u`, l'expansion d'un array vide échoue.
# On capture les args restants de façon sûre ; l'expansion utilise le pattern
# "${arr[@]+"${arr[@]}"}" qui ne produit rien quand l'array est vide.
EXTRA_ARGS=()
if [[ "$#" -gt 0 ]]; then
    EXTRA_ARGS=("$@")
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  KOREV Oracle — Test Runner  |  cible='${TARGET}'  |  $($PYTHON --version 2>&1)${NC}"
echo -e "${BLUE}  EVIDENCE_ENV=${EVIDENCE_ENV}  CONSENSUS_SIMULATION=${CONSENSUS_SIMULATION}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

case "$TARGET" in
    scope)
        exec "$PYTHON" -m pytest "${SCOPE_TESTS[@]}" -q -p no:cacheprovider "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    fast)
        exec "$PYTHON" -m pytest "${FAST_TESTS[@]}" -q -p no:cacheprovider "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    local)
        check_python_310 || true
        # --continue-on-collection-errors: les fichiers non importables localement
        # (deps optionnelles absentes, syntaxe 3.10+) ne doivent pas abandonner la
        # session entière. Ils restent visibles dans le récapitulatif "errors".
        exec "$PYTHON" -m pytest tests/ -q -p no:cacheprovider \
            --continue-on-collection-errors \
            --ignore=tests/security \
            --ignore=tests/infra \
            "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    security)
        exec "$PYTHON" -m pytest tests/security/ -q -p no:cacheprovider "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    unit)
        if ! check_python_310; then
            echo -e "${RED}[ABORT]${NC} 'unit' exige Python 3.10+."
            exit 2
        fi
        exec "$PYTHON" -m pytest tests/ -q -p no:cacheprovider \
            --ignore=tests/e2e \
            --ignore=tests/integration \
            --ignore=tests/infra \
            --ignore=tests/property \
            --ignore=tests/test_reasoning_engine.py \
            --ignore=tests/test_dockerfile_backend_ocr.py \
            -m "not slow" \
            "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    blocking)
        if ! check_python_310; then
            echo -e "${RED}[ABORT]${NC} 'blocking' exige Python 3.10+."
            exit 2
        fi
        set +e
        for gate in scope fast security; do
            echo -e "${BLUE}[blocking]${NC} gate=${gate}"
            bash "$ROOT_DIR/scripts/run_tests.sh" "$gate" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
            gate_rc=$?
            if [[ "$gate_rc" -ne 0 ]]; then
                echo -e "${RED}[blocking]${NC} ÉCHEC sur gate=${gate} (exit=$gate_rc)"
                exit "$gate_rc"
            fi
        done
        set -e
        echo -e "${GREEN}[blocking]${NC} Tous les gates bloquants sont VERTS."
        exit 0
        ;;
    extended)
        if ! check_python_310; then
            echo -e "${RED}[ABORT]${NC} 'extended' exige Python 3.10+."
            exit 2
        fi
        exec "$PYTHON" -m pytest tests/e2e tests/integration tests/infra tests/property -q -p no:cacheprovider \
            "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    full)
        if ! check_python_310; then
            echo -e "${RED}[ABORT]${NC} 'full' exige Python 3.10+. Utilisez 'docker' ou un interpréteur 3.10+."
            echo -e "        Exemple: PYTHON=python3.11 ./scripts/run_tests.sh full"
            exit 2
        fi
        exec "$PYTHON" -m pytest tests/ -q "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    docker)
        IMAGE="${KOREV_TEST_IMAGE:-korev-evidence-run:local}"
        if ! command -v docker >/dev/null 2>&1; then
            echo -e "${RED}[ABORT]${NC} docker introuvable dans le PATH."
            exit 2
        fi
        if ! docker info >/dev/null 2>&1; then
            echo -e "${RED}[ABORT]${NC} le daemon docker n'est pas démarré."
            exit 2
        fi
        echo -e "${BLUE}[INFO]${NC} Exécution de la full-suite dans l'image '${IMAGE}'."
        exec docker run --rm \
            -e EVIDENCE_ENV=development \
            -e CONSENSUS_SIMULATION=true \
            -v "$ROOT_DIR":/app -w /app \
            "$IMAGE" \
            python -m pytest tests/ -q "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        ;;
    *)
        echo -e "${RED}[ERREUR]${NC} Cible inconnue: '${TARGET}'."
        echo "Cibles valides: scope | fast | unit | blocking | security | extended | local | full | docker"
        exit 2
        ;;
esac
