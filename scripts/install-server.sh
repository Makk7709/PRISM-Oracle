#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#  KOREV EVIDENCE — Installation serveur (Ubuntu/Debian)
#═══════════════════════════════════════════════════════════════════════════════
#
#  Usage (depuis un serveur Ubuntu/Debian fraîchement provisionné) :
#
#    curl -fsSL https://raw.githubusercontent.com/Makk7709/PRISM-Oracle/main/scripts/install-server.sh | bash
#
#  Ou manuellement :
#    git clone https://github.com/Makk7709/PRISM-Oracle.git
#    cd PRISM-Oracle
#    chmod +x scripts/install-server.sh
#    ./scripts/install-server.sh
#
#  Ce script :
#    1. Vérifie / installe Docker Engine + Docker Compose
#    2. Vérifie / installe Git
#    3. Clone le dépôt (si nécessaire)
#    4. Configure le fichier .env
#    5. Ouvre les ports 80/443 (ufw)
#    6. Construit l'image Docker
#    7. Démarre les services (backend + Caddy)
#    8. Vérifie le health check
#
#  Testé sur : Ubuntu 22.04, Ubuntu 24.04, Debian 12
#═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Couleurs ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

TOTAL_STEPS=8

log_step()  { echo -e "\n${BLUE}${BOLD}[$1/$TOTAL_STEPS]${NC} ${BOLD}$2${NC}"; }
log_ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
log_warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
log_fail()  { echo -e "  ${RED}✗${NC} $1"; }

fail_exit() {
    log_fail "$1"
    echo -e "\n${RED}Installation interrompue.${NC}"
    exit 1
}

REPO_URL="https://github.com/Makk7709/PRISM-Oracle.git"
REPO_DIR="PRISM-Oracle"
DOCKER_FRESHLY_INSTALLED=false

# Préfixe docker : sudo si l'utilisateur n'est pas dans le groupe docker
docker_cmd() {
    if $DOCKER_FRESHLY_INSTALLED && [ "$(id -u)" -ne 0 ]; then
        sudo docker "$@"
    else
        docker "$@"
    fi
}

docker_compose_cmd() {
    if $DOCKER_FRESHLY_INSTALLED && [ "$(id -u)" -ne 0 ]; then
        sudo docker compose "$@"
    else
        docker compose "$@"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
#  BANNIÈRE
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║        KOREV EVIDENCE — Installation Serveur             ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 1 : Vérifier / installer Docker
# ═══════════════════════════════════════════════════════════════════════════════
log_step 1 "Vérification de Docker..."

if command -v docker &> /dev/null && docker info &> /dev/null; then
    log_ok "Docker installé : $(docker --version | head -1)"
elif command -v docker &> /dev/null; then
    log_warn "Docker installé mais le daemon n'est pas accessible"
    log_warn "Tentative de démarrage du service Docker..."
    sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
    sleep 2
    if docker info &> /dev/null; then
        log_ok "Docker daemon démarré : $(docker --version | head -1)"
    else
        log_warn "Impossible de démarrer Docker — réinstallation..."
        curl -fsSL https://get.docker.com | sh
        DOCKER_FRESHLY_INSTALLED=true
        if [ "$(id -u)" -ne 0 ]; then
            sudo usermod -aG docker "$USER"
            log_warn "Groupe docker ajouté — sudo utilisé pour la suite"
        fi
        log_ok "Docker réinstallé : $(docker --version | head -1)"
    fi
else
    log_warn "Docker non trouvé — installation en cours..."
    curl -fsSL https://get.docker.com | sh
    DOCKER_FRESHLY_INSTALLED=true
    if [ "$(id -u)" -ne 0 ]; then
        sudo usermod -aG docker "$USER"
        log_warn "Groupe docker ajouté — sudo utilisé pour la suite de l'installation"
    fi
    log_ok "Docker installé : $(docker --version | head -1)"
fi

# Vérifier Docker Compose
if docker_compose_cmd version &> /dev/null; then
    log_ok "Docker Compose : $(docker_compose_cmd version --short 2>/dev/null || echo 'v2+')"
else
    if $DOCKER_FRESHLY_INSTALLED; then
        fail_exit "Docker Compose non disponible après installation. Vérifiez avec : sudo docker compose version"
    else
        fail_exit "Docker Compose v2 non disponible. Réinstallez Docker Engine."
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 2 : Vérifier / installer Git
# ═══════════════════════════════════════════════════════════════════════════════
log_step 2 "Vérification de Git..."

if command -v git &> /dev/null; then
    log_ok "Git installé : $(git --version)"
else
    log_warn "Git non trouvé — installation..."
    sudo apt-get update -qq && sudo apt-get install -y -qq git
    log_ok "Git installé"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3 : Cloner le dépôt
# ═══════════════════════════════════════════════════════════════════════════════
log_step 3 "Récupération du code source..."

# Détecter si on est déjà dans le repo
if [ -f "deploy/docker-compose.yml" ] && [ -f "deploy/Dockerfile.backend" ]; then
    PROJECT_ROOT="$(pwd)"
    log_ok "Dépôt détecté dans le répertoire courant"
    # Mettre à jour
    git pull --ff-only 2>/dev/null && log_ok "Code mis à jour (git pull)" || log_warn "git pull ignoré"
elif [ -d "$REPO_DIR" ] && [ -f "$REPO_DIR/deploy/docker-compose.yml" ]; then
    PROJECT_ROOT="$(pwd)/$REPO_DIR"
    log_ok "Dépôt existant trouvé dans ./$REPO_DIR"
    cd "$PROJECT_ROOT"
    git pull --ff-only 2>/dev/null && log_ok "Code mis à jour" || log_warn "git pull ignoré"
else
    log_warn "Clonage du dépôt..."
    git clone "$REPO_URL"
    PROJECT_ROOT="$(pwd)/$REPO_DIR"
    cd "$PROJECT_ROOT"
    log_ok "Dépôt cloné dans $PROJECT_ROOT"
fi

DEPLOY_DIR="$PROJECT_ROOT/deploy"

# Vérification finale
if [ ! -f "$DEPLOY_DIR/docker-compose.yml" ]; then
    fail_exit "docker-compose.yml introuvable dans $DEPLOY_DIR"
fi
if [ ! -f "$DEPLOY_DIR/Dockerfile.backend" ]; then
    fail_exit "Dockerfile.backend introuvable dans $DEPLOY_DIR"
fi
if [ ! -f "$DEPLOY_DIR/config/Caddyfile" ]; then
    fail_exit "Caddyfile introuvable dans $DEPLOY_DIR/config/Caddyfile"
fi
log_ok "Fichiers de déploiement vérifiés"

# ── Initialiser les sous-modules Git (MCP servers locaux) ──
if [ -f "$PROJECT_ROOT/.gitmodules" ] || [ -d "$PROJECT_ROOT/mcp_servers/semanticscholar/.git" ]; then
    log_info "Initialisation des sous-modules MCP..."
    cd "$PROJECT_ROOT"
    git submodule update --init --recursive 2>/dev/null \
        && log_ok "Sous-modules MCP initialisés" \
        || log_warn "git submodule update échoué (non fatal — les MCP locaux seront indisponibles)"
else
    log_info "Vérification des MCP servers locaux..."
    if [ -f "$PROJECT_ROOT/mcp_servers/semanticscholar/server.py" ]; then
        log_ok "MCP Semantic Scholar: présent"
    else
        log_warn "MCP Semantic Scholar: fichiers manquants (sous-module non initialisé)"
    fi
    if [ -f "$PROJECT_ROOT/mcp_servers/openalex/src/server.js" ]; then
        log_ok "MCP OpenAlex: présent"
    else
        log_warn "MCP OpenAlex: fichiers manquants (sous-module non initialisé)"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 4 : Configurer .env
# ═══════════════════════════════════════════════════════════════════════════════
log_step 4 "Configuration de l'environnement..."

ENV_FILE="$DEPLOY_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    log_ok "Fichier .env existant détecté"
else
    if [ -f "$DEPLOY_DIR/.env.example" ]; then
        cp "$DEPLOY_DIR/.env.example" "$ENV_FILE"
        log_ok "Fichier .env créé depuis .env.example"
    else
        fail_exit ".env.example introuvable dans $DEPLOY_DIR"
    fi
fi

# Vérifier la clé API
if grep -qE "^API_KEY_OPENROUTER=sk-or-v1-[A-Za-z0-9_-]{20,}$" "$ENV_FILE" 2>/dev/null; then
    log_ok "Clé API OpenRouter configurée (format valide)"
else
    echo ""
    echo -e "  ${YELLOW}══════════════════════════════════════════════════════════${NC}"
    echo -e "  ${YELLOW}  IMPORTANT : Configurez votre clé API avant de continuer${NC}"
    echo -e "  ${YELLOW}══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Éditez le fichier : $ENV_FILE"
    echo "  Remplissez au minimum :"
    echo ""
    echo "    API_KEY_OPENROUTER=sk-or-v1-votre-cle-ici"
    echo "    AUTH_PASSWORD=VotreMotDePasseFort123!"
    echo ""
    echo "  Obtenez une clé sur : https://openrouter.ai/keys"
    echo ""
    if [ -t 0 ]; then
        read -rp "  Appuyez sur Entrée quand c'est fait (ou Entrée pour continuer sans)... "
    else
        log_warn "Mode non-interactif détecté — pensez à configurer .env après l'installation"
    fi
fi

# Vérifier le mot de passe
if grep -qE "^AUTH_PASSWORD=XXXXX" "$ENV_FILE" 2>/dev/null || grep -qE "^AUTH_PASSWORD=$" "$ENV_FILE" 2>/dev/null; then
    log_warn "AUTH_PASSWORD non configuré — pensez à le définir dans .env"
else
    log_ok "AUTH_PASSWORD configuré"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 5 : Ouvrir les ports (firewall)
# ═══════════════════════════════════════════════════════════════════════════════
log_step 5 "Configuration du pare-feu..."

if command -v ufw &> /dev/null; then
    if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
        sudo ufw allow 22/tcp  >/dev/null 2>&1 && log_ok "Port 22 (SSH) confirmé ouvert"   || log_warn "Impossible d'ouvrir le port 22"
        sudo ufw allow 80/tcp  >/dev/null 2>&1 && log_ok "Port 80 (HTTP) ouvert"            || log_warn "Impossible d'ouvrir le port 80"
        sudo ufw allow 443/tcp >/dev/null 2>&1 && log_ok "Port 443 (HTTPS) ouvert"          || log_warn "Impossible d'ouvrir le port 443"
    else
        log_ok "ufw inactif — pas de règles à ajouter"
    fi
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-service=http  >/dev/null 2>&1 || true
    sudo firewall-cmd --permanent --add-service=https >/dev/null 2>&1 || true
    sudo firewall-cmd --reload >/dev/null 2>&1 || true
    log_ok "Ports 80/443 ouverts (firewalld)"
else
    log_ok "Aucun pare-feu détecté"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 6 : Construire l'image Docker
# ═══════════════════════════════════════════════════════════════════════════════
log_step 6 "Construction de l'image Docker (10-20 min la première fois)..."

cd "$DEPLOY_DIR"

if ! docker_compose_cmd config >/dev/null 2>&1; then
    fail_exit "Configuration Docker Compose invalide. Vérifiez .env et docker-compose.yml"
fi
log_ok "Configuration Docker Compose valide"

echo ""
echo -e "  ${BLUE}Téléchargement des dépendances et compilation...${NC}"
echo -e "  ${BLUE}Vous pouvez suivre la progression ci-dessous.${NC}"
echo ""

BUILD_START=$(date +%s)

if docker_compose_cmd build evidence-backend; then
    BUILD_END=$(date +%s)
    BUILD_DURATION=$(( BUILD_END - BUILD_START ))
    BUILD_MIN=$(( BUILD_DURATION / 60 ))
    BUILD_SEC=$(( BUILD_DURATION % 60 ))
    echo ""
    log_ok "Image construite en ${BUILD_MIN}m${BUILD_SEC}s"
else
    echo ""
    echo -e "  ${RED}Le build a échoué.${NC}"
    echo ""
    echo "  Causes fréquentes :"
    echo "    - Mémoire insuffisante (minimum 4 Go libres pendant le build)"
    echo "      Vérifiez : free -h"
    echo "    - Espace disque insuffisant (minimum 10 Go libres)"
    echo "      Vérifiez : df -h /"
    echo "    - Pas d'accès internet (proxy, DNS)"
    echo "      Vérifiez : curl -I https://pypi.org"
    echo ""
    echo "  Pour nettoyer et réessayer :"
    echo "    docker system prune -af"
    echo "    cd $(pwd) && docker compose build --no-cache evidence-backend"
    fail_exit "Échec du build Docker"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 7 : Démarrer les services
# ═══════════════════════════════════════════════════════════════════════════════
log_step 7 "Démarrage des services..."

# Arrêter les anciens conteneurs s'il y en a
docker_compose_cmd down 2>/dev/null || true

# Démarrer backend + Caddy (pas Samba par défaut)
if ! docker_compose_cmd up -d evidence-backend evidence-caddy; then
    echo ""
    echo "  Vérifiez les logs :"
    echo "    docker compose logs evidence-backend"
    echo "    docker compose logs evidence-caddy"
    fail_exit "Échec du démarrage des services"
fi

echo ""
echo -e "  ${BLUE}Attente du démarrage (health check, peut prendre 2-3 min)...${NC}"

MAX_WAIT=360
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    # Vérifier le health check via Caddy
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/healthz 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
    echo -n "."
done
echo ""

if [ $WAITED -ge $MAX_WAIT ]; then
    log_warn "Le service n'a pas répondu dans les ${MAX_WAIT}s"
    echo ""
    echo "  Sur un VPS, le premier démarrage peut prendre 4-6 minutes."
    echo "  Vérifiez avec :"
    echo "    cd deploy && docker compose ps"
    echo "    docker compose logs -f evidence-backend"
else
    log_ok "Health check OK (HTTP 200)"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 8 : Vérification finale
# ═══════════════════════════════════════════════════════════════════════════════
log_step 8 "Vérification finale..."

echo ""
docker_compose_cmd ps
echo ""

# Récupérer l'IP publique
SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || curl -s --max-time 5 icanhazip.com 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "VOTRE_IP")

# ═══════════════════════════════════════════════════════════════════════════════
#  RÉSULTAT
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║       KOREV EVIDENCE — Installation Terminée !           ║"
echo "  ║                                                          ║"
echo "  ╠══════════════════════════════════════════════════════════╣"
echo "  ║                                                          ║"
echo "  ║   Accès : http://$SERVER_IP"
echo "  ║                                                          ║"
echo "  ║   Login : voir AUTH_LOGIN / AUTH_PASSWORD dans .env      ║"
echo "  ║                                                          ║"
echo "  ╠══════════════════════════════════════════════════════════╣"
echo "  ║                                                          ║"
echo "  ║   Commandes utiles (depuis deploy/) :                    ║"
echo "  ║                                                          ║"
echo "  ║     État    : docker compose ps                          ║"
echo "  ║     Logs    : docker compose logs -f evidence-backend    ║"
echo "  ║     Stop    : docker compose down                        ║"
echo "  ║     Start   : docker compose up -d                       ║"
echo "  ║     Rebuild : docker compose build evidence-backend      ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "  Les clés API peuvent aussi être configurées depuis"
echo "  l'interface web : Settings (icône engrenage)."
echo ""
echo "  Configuration : $ENV_FILE"
echo "  Manuel complet : $PROJECT_ROOT/docs/MANUEL_INSTALLATION_CLIENT.md"
echo ""
