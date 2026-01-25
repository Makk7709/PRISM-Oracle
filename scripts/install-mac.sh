#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#  KOREV ORACLE - Installation Script (macOS)
#═══════════════════════════════════════════════════════════════════════════════
#
#  Usage: ./install-mac.sh
#
#  Ce script:
#  1. Vérifie que Docker est installé et lancé
#  2. Pré-télécharge l'image Docker
#  3. Vérifie/crée le fichier .env
#  4. Lance Oracle via docker-compose
#
#═══════════════════════════════════════════════════════════════════════════════

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ORACLE_PORT="${ORACLE_PORT:-50080}"
DOCKER_IMAGE="agent0ai/agent-zero:latest"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           KOREV ORACLE - Installation macOS                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

#───────────────────────────────────────────────────────────────────────────────
# Step 1: Check Docker
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Vérification de Docker...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker n'est pas installé.${NC}"
    echo ""
    echo "Installez Docker Desktop depuis: https://www.docker.com/products/docker-desktop/"
    echo "Puis relancez ce script."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker n'est pas lancé.${NC}"
    echo ""
    echo "Lancez Docker Desktop et attendez qu'il soit prêt (icône verte)."
    echo "Puis relancez ce script."
    exit 1
fi

DOCKER_VERSION=$(docker --version)
echo -e "${GREEN}✅ Docker installé: ${DOCKER_VERSION}${NC}"

#───────────────────────────────────────────────────────────────────────────────
# Step 2: Check docker-compose
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Vérification de docker-compose...${NC}"

if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}❌ docker-compose n'est pas disponible.${NC}"
    echo "Docker Desktop inclut normalement docker-compose."
    exit 1
fi

echo -e "${GREEN}✅ docker-compose disponible${NC}"

#───────────────────────────────────────────────────────────────────────────────
# Step 3: Pre-pull Docker image
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Téléchargement de l'image Docker (peut prendre quelques minutes)...${NC}"

if docker image inspect "$DOCKER_IMAGE" &> /dev/null; then
    echo -e "${GREEN}✅ Image déjà présente localement${NC}"
else
    echo "Téléchargement de $DOCKER_IMAGE..."
    docker pull "$DOCKER_IMAGE"
    echo -e "${GREEN}✅ Image téléchargée${NC}"
fi

#───────────────────────────────────────────────────────────────────────────────
# Step 4: Check/Create .env file
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/5] Vérification du fichier .env...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ Fichier .env trouvé${NC}"
    
    # Check for required API keys
    if grep -q "API_KEY_OPENAI=sk-" "$ENV_FILE" || grep -q "API_KEY_OPENROUTER=sk-" "$ENV_FILE"; then
        echo -e "${GREEN}✅ Clés API configurées${NC}"
    else
        echo -e "${YELLOW}⚠️  Attention: Aucune clé API détectée dans .env${NC}"
        echo "   Oracle a besoin d'au moins une clé API (OpenAI ou OpenRouter)."
        echo "   Éditez le fichier .env avant de continuer."
    fi
else
    echo -e "${YELLOW}⚠️  Fichier .env non trouvé. Création à partir du template...${NC}"
    
    cat > "$ENV_FILE" << 'ENVFILE'
# Korev Oracle Configuration
# ==========================
# Remplissez au moins UNE clé API (OpenAI ou OpenRouter)

# Runtime ID (généré automatiquement)
KOREV_PERSISTENT_RUNTIME_ID=

# API Keys - Remplissez au moins une
API_KEY_OPENAI=
API_KEY_OPENROUTER=
API_KEY_ANTHROPIC=
API_KEY_GOOGLE=
API_KEY_MISTRAL=

# Configuration
WEB_UI_PORT=5050
DEFAULT_USER_TIMEZONE=Europe/Paris
ANONYMIZED_TELEMETRY=false
ENVFILE
    
    echo -e "${GREEN}✅ Fichier .env créé${NC}"
    echo -e "${YELLOW}   ⚠️  IMPORTANT: Éditez $ENV_FILE et ajoutez vos clés API${NC}"
fi

#───────────────────────────────────────────────────────────────────────────────
# Step 5: Launch Oracle
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Lancement d'Oracle...${NC}"

DOCKER_DIR="$PROJECT_ROOT/docker/run"

if [ ! -f "$DOCKER_DIR/docker-compose.yml" ]; then
    echo -e "${RED}❌ docker-compose.yml non trouvé dans $DOCKER_DIR${NC}"
    exit 1
fi

cd "$DOCKER_DIR"

# Check if already running
if docker ps --format '{{.Names}}' | grep -q "korev-oracle"; then
    echo -e "${YELLOW}Oracle est déjà en cours d'exécution.${NC}"
    echo ""
    read -p "Voulez-vous le redémarrer? (o/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        $COMPOSE_CMD down
        $COMPOSE_CMD up -d
    fi
else
    $COMPOSE_CMD up -d
fi

#───────────────────────────────────────────────────────────────────────────────
# Done
#───────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           ✅ INSTALLATION TERMINÉE                            ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                               ║"
echo "║  Oracle est accessible sur:                                   ║"
echo "║  → http://localhost:$ORACLE_PORT                              ║"
echo "║                                                               ║"
echo "║  Commandes utiles:                                            ║"
echo "║  • Logs:    docker logs -f korev-oracle                       ║"
echo "║  • Stop:    docker stop korev-oracle                          ║"
echo "║  • Start:   docker start korev-oracle                         ║"
echo "║  • Restart: docker restart korev-oracle                       ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
