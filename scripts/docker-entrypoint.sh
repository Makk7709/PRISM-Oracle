#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  KOREV Evidence — Docker Entrypoint                                        ║
# ║                                                                            ║
# ║  Auto-configures MCP servers and starts the application.                   ║
# ║  Runs BEFORE the main Python process on every container start.             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

MCP_READY_FLAG="/app/tmp/.mcp_setup_done"
MCP_CONFIG_PROD="/app/deploy/mcp_config.production.json"
MCP_CONFIG_TARGET="/app/mcp_config.json"

log_info()  { echo "[entrypoint] ✓ $*"; }
log_warn()  { echo "[entrypoint] ⚠ $*"; }
log_err()   { echo "[entrypoint] ✗ $*" >&2; }

# ─────────────────────────────────────────────────────────────────────────────
# 1. Install production MCP config (replaces local-path config)
# ─────────────────────────────────────────────────────────────────────────────
setup_mcp_config() {
    if [ -f "$MCP_CONFIG_PROD" ]; then
        cp "$MCP_CONFIG_PROD" "$MCP_CONFIG_TARGET"
        log_info "Production MCP config installed"
    else
        log_warn "No production MCP config found at $MCP_CONFIG_PROD"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Pre-warm npx packages (first run only — cached in node_modules)
# ─────────────────────────────────────────────────────────────────────────────
prewarm_npx_packages() {
    if [ -f "$MCP_READY_FLAG" ]; then
        log_info "MCP packages already pre-warmed (cached)"
        return 0
    fi

    log_info "Pre-warming MCP npx packages (first run, may take 1-2 min)..."

    local packages=(
        "firecrawl-mcp"
        "tavily-mcp"
        "pubmed-mcp-server"
        "@playwright/mcp"
        "@anthropic-ai/mcp-server-brave-search"
        "@modelcontextprotocol/server-puppeteer@0.6.2"
    )

    local success=0
    local failed=0

    for pkg in "${packages[@]}"; do
        if npx -y "$pkg" --help >/dev/null 2>&1 || npx -y "$pkg" --version >/dev/null 2>&1; then
            success=$((success + 1))
        else
            log_warn "Could not pre-warm: $pkg (non-fatal, will install on first use)"
            failed=$((failed + 1))
        fi
    done

    log_info "Pre-warmed $success npx packages ($failed skipped)"
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Pre-warm uvx packages (fetch + arxiv)
# ─────────────────────────────────────────────────────────────────────────────
prewarm_uvx_packages() {
    if [ -f "$MCP_READY_FLAG" ]; then
        return 0
    fi

    if command -v uvx >/dev/null 2>&1; then
        log_info "Pre-warming uvx MCP packages..."

        for pkg in "mcp-server-fetch" "arxiv-mcp-server"; do
            if uvx "$pkg" --help >/dev/null 2>&1; then
                log_info "  uvx: $pkg ready"
            else
                log_warn "  uvx: $pkg pre-warm failed (non-fatal)"
            fi
        done
    else
        log_warn "uvx not found — fetch & arxiv MCP servers will be unavailable"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Verify local MCP servers (semanticscholar, openalex)
# ─────────────────────────────────────────────────────────────────────────────
verify_local_mcp_servers() {
    local ss_server="/app/mcp_servers/semanticscholar/server.py"
    local oa_server="/app/mcp_servers/openalex/src/server.js"

    if [ -f "$ss_server" ]; then
        if python -c "import sys; sys.path.insert(0,'/app/mcp_servers/semanticscholar'); import server" 2>/dev/null; then
            log_info "Semantic Scholar MCP: OK"
        else
            log_warn "Semantic Scholar MCP: import failed (missing deps?)"
        fi
    else
        log_warn "Semantic Scholar MCP: server.py not found at $ss_server"
    fi

    if [ -f "$oa_server" ]; then
        if node -e "require('/app/mcp_servers/openalex/src/server.js')" 2>/dev/null; then
            log_info "OpenAlex MCP: OK"
        else
            if [ -f "/app/mcp_servers/openalex/package.json" ]; then
                log_info "OpenAlex MCP: installing npm deps..."
                cd /app/mcp_servers/openalex && npm install --production 2>/dev/null && log_info "OpenAlex MCP: deps installed" || log_warn "OpenAlex MCP: npm install failed"
                cd /app
            fi
        fi
    else
        log_warn "OpenAlex MCP: server.js not found at $oa_server"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. Mark setup as done
# ─────────────────────────────────────────────────────────────────────────────
finalize() {
    touch "$MCP_READY_FLAG" 2>/dev/null || true
    log_info "MCP setup complete"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
log_info "KOREV Evidence — Starting entrypoint..."

setup_mcp_config
verify_local_mcp_servers

# Pre-warm packages in background to not delay startup
(
    prewarm_uvx_packages
    prewarm_npx_packages
    finalize
) &

log_info "Starting application..."
exec "$@"
