#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    PRISM + EVIDENCE — Upgrade Script                           ║
# ║                                                                              ║
# ║  Mise à jour avec rollback automatique si smoke test échoue                  ║
# ║  Usage: ./upgrade.sh --version NEW_VERSION                                   ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$DEPLOY_DIR")"

ENV_FILE="${DEPLOY_DIR}/.env"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
BACKUP_DIR="${DEPLOY_DIR}/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

get_current_version() {
    source "$ENV_FILE" 2>/dev/null || true
    echo "${EVIDENCE_VERSION:-unknown}"
}

backup_current() {
    log_info "Backing up current version..."
    
    local current_version=$(get_current_version)
    local backup_name="backup_${current_version}_$(date +%Y%m%d_%H%M%S)"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    mkdir -p "$backup_path"
    
    # Save current .env
    cp "$ENV_FILE" "${backup_path}/.env.backup"
    
    # Save image tags
    docker images korev/evidence-* --format "{{.Repository}}:{{.Tag}}" > "${backup_path}/images.txt"
    
    # Save version info
    echo "$current_version" > "${backup_path}/version.txt"
    
    log_success "Backup created: $backup_path"
    echo "$backup_path"
}

pull_new_version() {
    local new_version="$1"
    log_info "Pulling version $new_version..."
    
    cd "$DEPLOY_DIR"
    
    # Update version in env
    sed -i.bak "s/^EVIDENCE_VERSION=.*/EVIDENCE_VERSION=${new_version}/" "$ENV_FILE" || \
        echo "EVIDENCE_VERSION=${new_version}" >> "$ENV_FILE"
    
    # Build new images
    EVIDENCE_VERSION="$new_version" docker-compose build
    
    log_success "New version built: $new_version"
}

stop_services() {
    log_info "Stopping current services..."
    cd "$DEPLOY_DIR"
    docker-compose down --timeout 30
    log_success "Services stopped"
}

start_new_version() {
    local new_version="$1"
    log_info "Starting version $new_version..."
    
    cd "$DEPLOY_DIR"
    EVIDENCE_VERSION="$new_version" docker-compose up -d
    
    log_success "Services started"
}

health_check() {
    log_info "Waiting for health check..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://127.0.0.1:5050/healthz | grep -q "healthy"; then
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    return 1
}

run_smoke_test() {
    log_info "Running smoke tests..."
    cd "$PROJECT_DIR"
    python tools/smoke_test.py --offline
}

rollback() {
    local backup_path="$1"
    log_warn "ROLLBACK: Restoring previous version..."
    
    # Get previous version
    local prev_version=$(cat "${backup_path}/version.txt")
    
    # Stop current
    cd "$DEPLOY_DIR"
    docker-compose down --timeout 10
    
    # Restore env
    cp "${backup_path}/.env.backup" "$ENV_FILE"
    
    # Start previous version
    EVIDENCE_VERSION="$prev_version" docker-compose up -d
    
    log_info "Waiting for rollback to complete..."
    sleep 10
    
    if health_check; then
        log_success "Rollback successful to version $prev_version"
    else
        log_error "Rollback failed - manual intervention required"
        exit 1
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 5)..."
    
    cd "$BACKUP_DIR" 2>/dev/null || return
    
    ls -dt backup_* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true
    
    log_success "Cleanup complete"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║              PRISM + EVIDENCE — Upgrade                                ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    local new_version=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                new_version="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 --version NEW_VERSION"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    if [ -z "$new_version" ]; then
        log_error "Version required: --version NEW_VERSION"
        exit 1
    fi
    
    local current_version=$(get_current_version)
    log_info "Current version: $current_version"
    log_info "Target version:  $new_version"
    echo ""
    
    # Confirm
    read -p "Proceed with upgrade? (y/N) " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Upgrade cancelled"
        exit 0
    fi
    
    # Create backup
    mkdir -p "$BACKUP_DIR"
    local backup_path=$(backup_current)
    
    # Upgrade process
    pull_new_version "$new_version"
    stop_services
    start_new_version "$new_version"
    
    # Validate
    if health_check; then
        log_success "Health check passed"
        
        if run_smoke_test; then
            log_success "Smoke tests passed"
            cleanup_old_backups
            
            echo ""
            echo "═══════════════════════════════════════════════════════════════════════"
            echo -e "${GREEN}UPGRADE SUCCESSFUL: $current_version -> $new_version${NC}"
            echo "═══════════════════════════════════════════════════════════════════════"
        else
            log_error "Smoke tests failed"
            rollback "$backup_path"
            exit 1
        fi
    else
        log_error "Health check failed"
        rollback "$backup_path"
        exit 1
    fi
}

main "$@"
