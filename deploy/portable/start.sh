#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    PRISM + EVIDENCE — Portable Start (Unix)                    ║
# ║                                                                              ║
# ║  Démarrage en mode portable (sans Docker)                                    ║
# ║  Usage: ./start.sh [--port PORT]                                             ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
VENV_DIR="${PROJECT_DIR}/venv"
DATA_DIR="${PROJECT_DIR}/data"
LOGS_DIR="${PROJECT_DIR}/logs"
AUDIT_DIR="${PROJECT_DIR}/audit"
PID_FILE="${PROJECT_DIR}/evidence.pid"

PORT="${EVIDENCE_PORT:-5050}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python not found"
        exit 1
    fi
    
    local version=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+')
    log_success "Python found: $($PYTHON_CMD --version)"
}

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    fi
    
    # Activate venv
    source "${VENV_DIR}/bin/activate"
    
    # Install dependencies if needed
    if [ ! -f "${VENV_DIR}/.installed" ]; then
        log_info "Installing dependencies..."
        pip install --upgrade pip wheel
        pip install -r "${PROJECT_DIR}/requirements.txt"
        touch "${VENV_DIR}/.installed"
        log_success "Dependencies installed"
    fi
}

setup_directories() {
    mkdir -p "$DATA_DIR" "$LOGS_DIR" "$AUDIT_DIR"
    log_success "Directories created"
}

check_already_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_warn "Evidence is already running (PID: $pid)"
            log_info "Use ./stop.sh to stop it first"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi
}

start_evidence() {
    log_info "Starting Evidence on port $PORT..."
    
    cd "$PROJECT_DIR"
    
    # Set environment
    export DATA_DIR="$DATA_DIR"
    export LOGS_DIR="$LOGS_DIR"
    export AUDIT_DIR="$AUDIT_DIR"
    export EVIDENCE_ENV="production"
    export OFFLINE_MODE="${OFFLINE_MODE:-true}"
    
    # Start in background
    nohup $PYTHON_CMD run_ui.py --port "$PORT" > "${LOGS_DIR}/evidence.log" 2>&1 &
    local pid=$!
    
    echo "$pid" > "$PID_FILE"
    
    log_success "Evidence started (PID: $pid)"
}

wait_for_ready() {
    log_info "Waiting for Evidence to be ready..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://127.0.0.1:${PORT}/healthz" > /dev/null 2>&1; then
            log_success "Evidence is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    log_error "Evidence did not start in time"
    log_info "Check logs: ${LOGS_DIR}/evidence.log"
    return 1
}

print_info() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo -e "${GREEN}EVIDENCE STARTED (Portable Mode)${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo ""
    echo "  URL:      http://127.0.0.1:${PORT}"
    echo "  Health:   http://127.0.0.1:${PORT}/healthz"
    echo "  Logs:     ${LOGS_DIR}/evidence.log"
    echo ""
    echo "  Stop:     ./stop.sh"
    echo "  Status:   ./status.sh"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
}

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║              PRISM + EVIDENCE — Portable Mode                          ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Parse args
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port|-p)
                PORT="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    check_python
    check_already_running
    setup_venv
    setup_directories
    start_evidence
    
    if wait_for_ready; then
        print_info
    else
        exit 1
    fi
}

main "$@"
