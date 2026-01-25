#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    PRISM + EVIDENCE — Installation Script                      ║
# ║                                                                              ║
# ║  Script d'installation pour déploiement Docker                               ║
# ║  Usage: ./install.sh [--version VERSION] [--env ENV_FILE]                    ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$DEPLOY_DIR")"

VERSION="${EVIDENCE_VERSION:-latest}"
ENV_FILE="${DEPLOY_DIR}/.env"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_success "Docker found: $(docker --version)"
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    log_success "Docker Compose found"
    
    # Check Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    log_success "Docker daemon is running"
}

setup_env() {
    log_info "Setting up environment..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "${DEPLOY_DIR}/.env.example" ]; then
            cp "${DEPLOY_DIR}/.env.example" "$ENV_FILE"
            log_warn "Created .env from example - PLEASE CONFIGURE API KEYS"
        else
            log_error ".env.example not found"
            exit 1
        fi
    else
        log_success ".env file exists"
    fi
    
    # Validate required vars
    source "$ENV_FILE" 2>/dev/null || true
    
    if [ -z "$EVIDENCE_VERSION" ]; then
        echo "EVIDENCE_VERSION=${VERSION}" >> "$ENV_FILE"
    fi
}

create_volumes() {
    log_info "Creating Docker volumes..."
    
    docker volume create evidence-data 2>/dev/null || true
    docker volume create evidence-logs 2>/dev/null || true
    docker volume create evidence-audit 2>/dev/null || true
    
    log_success "Volumes created"
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$DEPLOY_DIR"
    
    # Build with version tag
    EVIDENCE_VERSION="$VERSION" docker-compose build --no-cache
    
    log_success "Images built with version: $VERSION"
}

start_services() {
    log_info "Starting services..."
    
    cd "$DEPLOY_DIR"
    docker-compose up -d
    
    log_success "Services started"
}

wait_for_health() {
    log_info "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://127.0.0.1:5050/healthz > /dev/null 2>&1; then
            log_success "Backend is healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    log_error "Services did not become healthy in time"
    return 1
}

run_smoke_test() {
    log_info "Running smoke tests..."
    
    cd "$PROJECT_DIR"
    
    if python tools/smoke_test.py --offline; then
        log_success "Smoke tests passed"
    else
        log_warn "Some smoke tests failed (check output above)"
    fi
}

print_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo -e "${GREEN}EVIDENCE INSTALLATION COMPLETE${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo ""
    echo "  Version:  $VERSION"
    echo "  Backend:  http://127.0.0.1:5050"
    echo "  Frontend: http://127.0.0.1:8080"
    echo ""
    echo "  Health:   http://127.0.0.1:5050/healthz"
    echo "  Ready:    http://127.0.0.1:5050/readyz"
    echo ""
    echo "  Logs:     docker-compose -f $COMPOSE_FILE logs -f"
    echo "  Stop:     docker-compose -f $COMPOSE_FILE down"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║              PRISM + EVIDENCE — Installation                           ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                VERSION="$2"
                shift 2
                ;;
            --env)
                ENV_FILE="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [--version VERSION] [--env ENV_FILE]"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    check_prerequisites
    setup_env
    create_volumes
    build_images
    start_services
    
    if wait_for_health; then
        run_smoke_test
    fi
    
    print_summary
}

main "$@"
