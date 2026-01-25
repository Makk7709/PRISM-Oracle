#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    PRISM + EVIDENCE — Portable Stop (Unix)                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PID_FILE="${PROJECT_DIR}/evidence.pid"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} Evidence is not running (no PID file)"
    exit 1
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping Evidence (PID: $PID)..."
    kill "$PID"
    
    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing..."
        kill -9 "$PID"
    fi
    
    rm -f "$PID_FILE"
    echo -e "${GREEN}[OK]${NC} Evidence stopped"
else
    echo "Process $PID not found"
    rm -f "$PID_FILE"
fi
