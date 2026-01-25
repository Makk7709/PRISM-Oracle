#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    PRISM + EVIDENCE — Rollback Script                          ║
# ║                                                                              ║
# ║  Rollback manuel vers une version précédente                                 ║
# ║  Usage: ./rollback.sh [--version VERSION] [--list]                           ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${DEPLOY_DIR}/backups"

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

list_backups() {
    echo ""
    echo "Available backups:"
    echo "─────────────────────────────────────────────────"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "  No backups found"
        return
    fi
    
    for backup in "$BACKUP_DIR"/backup_*; do
        if [ -d "$backup" ]; then
            local name=$(basename "$backup")
            local version=$(cat "${backup}/version.txt" 2>/dev/null || echo "unknown")
            local date=$(echo "$name" | grep -oP '\d{8}_\d{6}' || echo "unknown")
            echo "  $name (version: $version)"
        fi
    done
    echo ""
}

rollback_to() {
    local target="$1"
    local backup_path=""
    
    # Find backup
    if [ -d "${BACKUP_DIR}/${target}" ]; then
        backup_path="${BACKUP_DIR}/${target}"
    elif [ -d "${BACKUP_DIR}/backup_${target}"* ]; then
        backup_path=$(ls -d "${BACKUP_DIR}/backup_${target}"* 2>/dev/null | head -1)
    else
        # Try to find by version
        for backup in "$BACKUP_DIR"/backup_*; do
            if [ -f "${backup}/version.txt" ]; then
                local v=$(cat "${backup}/version.txt")
                if [ "$v" = "$target" ]; then
                    backup_path="$backup"
                    break
                fi
            fi
        done
    fi
    
    if [ -z "$backup_path" ] || [ ! -d "$backup_path" ]; then
        log_error "Backup not found: $target"
        list_backups
        exit 1
    fi
    
    local version=$(cat "${backup_path}/version.txt")
    log_info "Rolling back to version: $version"
    log_info "Backup: $backup_path"
    echo ""
    
    read -p "Confirm rollback? (y/N) " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi
    
    # Stop current
    log_info "Stopping current services..."
    cd "$DEPLOY_DIR"
    docker-compose down --timeout 30
    
    # Restore env
    log_info "Restoring configuration..."
    cp "${backup_path}/.env.backup" "${DEPLOY_DIR}/.env"
    
    # Start previous version
    log_info "Starting version $version..."
    docker-compose up -d
    
    # Wait for health
    log_info "Waiting for services..."
    sleep 10
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://127.0.0.1:5050/healthz | grep -q "healthy"; then
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    echo ""
    
    if [ $attempt -lt $max_attempts ]; then
        log_success "Rollback successful to version $version"
    else
        log_error "Rollback completed but health check failed"
        exit 1
    fi
}

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║              PRISM + EVIDENCE — Rollback                               ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    case "${1:-}" in
        --list|-l)
            list_backups
            ;;
        --version|-v)
            if [ -z "$2" ]; then
                log_error "Version required"
                exit 1
            fi
            rollback_to "$2"
            ;;
        --latest)
            local latest=$(ls -dt "$BACKUP_DIR"/backup_* 2>/dev/null | head -1)
            if [ -z "$latest" ]; then
                log_error "No backups found"
                exit 1
            fi
            rollback_to "$(basename "$latest")"
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --list, -l          List available backups"
            echo "  --version, -v VER   Rollback to specific version/backup"
            echo "  --latest            Rollback to most recent backup"
            echo "  --help, -h          Show this help"
            ;;
        *)
            list_backups
            echo "Use --version BACKUP_NAME or --latest to rollback"
            ;;
    esac
}

main "$@"
