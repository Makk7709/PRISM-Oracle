#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#  KOREV EVIDENCE — Deploiement Docker One-Click (macOS / Linux)
#═══════════════════════════════════════════════════════════════════════════════
#
#  Usage:
#    chmod +x deploy-docker.sh
#    ./deploy-docker.sh
#
#  Prerequis: Docker Desktop installe et lance
#
#  Ce script:
#    1. Verifie Docker Desktop
#    2. Configure le fichier .env
#    3. Construit l'image KOREV Evidence
#    4. Demarre le container
#    5. Verifie que tout fonctionne
#    6. Ouvre le navigateur
#
#═══════════════════════════════════════════════════════════════════════════════

set -e

# ─── Couleurs ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Configuration ────────────────────────────────────────────────────────────
EVIDENCE_PORT="${EVIDENCE_PORT:-50080}"
IMAGE_NAME="korev-evidence:local"
CONTAINER_NAME="korev-evidence"

# ─── Repertoires ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# ─── Fonctions utilitaires ────────────────────────────────────────────────────
log_step()    { echo -e "\n${BLUE}${BOLD}[$1/7]${NC} ${BOLD}$2${NC}"; }
log_ok()      { echo -e "  ${GREEN}OK${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}!!${NC} $1"; }
log_fail()    { echo -e "  ${RED}ERREUR${NC} $1"; }

fail_and_exit() {
    log_fail "$1"
    echo ""
    echo -e "${RED}Installation interrompue.${NC}"
    echo "Consultez https://docs.docker.com/get-docker/ pour l'aide."
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════
#  BANNIERE
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}${BOLD}"
echo "  ╔═══════════════════════════════════════════════════════════════╗"
echo "  ║                                                               ║"
echo "  ║            KOREV EVIDENCE — Deploiement Docker                ║"
echo "  ║                    Installation One-Click                     ║"
echo "  ║                                                               ║"
echo "  ╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 1 : Verifier Docker Desktop
# ═══════════════════════════════════════════════════════════════════════════════
log_step 1 "Verification de Docker Desktop..."

# Verifier que docker est installe
if ! command -v docker &> /dev/null; then
    fail_and_exit "Docker n'est pas installe."
fi
log_ok "Docker installe: $(docker --version 2>/dev/null | head -1)"

# Verifier que docker compose est disponible
if ! docker compose version &> /dev/null 2>&1; then
    if ! command -v docker-compose &> /dev/null; then
        fail_and_exit "Docker Compose n'est pas disponible."
    fi
fi
log_ok "Docker Compose disponible"

# Verifier que le daemon Docker tourne
if ! docker info &> /dev/null 2>&1; then
    echo ""
    log_fail "Docker Desktop n'est pas lance."
    echo ""
    echo -e "  ${YELLOW}Lancez Docker Desktop puis relancez ce script.${NC}"
    echo ""
    # Tenter d'ouvrir Docker Desktop sur macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  Tentative d'ouverture de Docker Desktop..."
        open -a "Docker" 2>/dev/null || true
        echo "  Attendez que Docker Desktop soit pret, puis relancez:"
        echo "    ./scripts/deploy-docker.sh"
    fi
    exit 1
fi
log_ok "Docker Desktop est en cours d'execution"

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 2 : Verifier le DockerfileLocal
# ═══════════════════════════════════════════════════════════════════════════════
log_step 2 "Verification des fichiers du projet..."

if [ ! -f "$PROJECT_ROOT/DockerfileLocal" ]; then
    fail_and_exit "DockerfileLocal introuvable dans $PROJECT_ROOT"
fi
log_ok "DockerfileLocal present"

if [ ! -f "$PROJECT_ROOT/docker/run/docker-compose.yml" ]; then
    fail_and_exit "docker-compose.yml introuvable"
fi
log_ok "docker-compose.yml present"

if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
    fail_and_exit "requirements.txt introuvable"
fi
log_ok "requirements.txt present"

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3 : Configurer le fichier .env
# ═══════════════════════════════════════════════════════════════════════════════
log_step 3 "Configuration du fichier .env..."

ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    log_ok "Fichier .env existant detecte"

    # Verifier la cle API
    if grep -qE "API_KEY_OPENROUTER=.{10,}" "$ENV_FILE" 2>/dev/null; then
        log_ok "Cle API OpenRouter configuree"
    elif grep -q "API_KEY_OPENROUTER=" "$ENV_FILE" 2>/dev/null; then
        log_warn "Cle API OpenRouter VIDE — Evidence demarre mais ne pourra pas repondre"
        echo -e "  ${YELLOW}Editez .env et ajoutez votre cle API_KEY_OPENROUTER${NC}"
    fi
else
    log_warn "Fichier .env absent — creation depuis le template"
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        log_ok "Fichier .env cree depuis .env.example"
    else
        cat > "$ENV_FILE" << 'ENVEOF'
# ═══════════════════════════════════════════════════════════════════════════════
# KOREV EVIDENCE — Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Cle API principale (REQUISE) — https://openrouter.ai/keys
API_KEY_OPENROUTER=

# Port de l'interface web
WEB_UI_PORT=5050

# Fuseau horaire
DEFAULT_USER_TIMEZONE=Europe/Paris

# Telemetrie
ANONYMIZED_TELEMETRY=false
ENVEOF
        log_ok "Fichier .env cree avec les valeurs par defaut"
    fi
    echo ""
    echo -e "  ${YELLOW}════════════════════════════════════════════════════════${NC}"
    echo -e "  ${YELLOW}  IMPORTANT: Editez .env et ajoutez votre cle API!    ${NC}"
    echo -e "  ${YELLOW}  → API_KEY_OPENROUTER=votre-cle-ici                   ${NC}"
    echo -e "  ${YELLOW}════════════════════════════════════════════════════════${NC}"
    echo ""
    read -p "  Appuyez sur Entree quand c'est fait (ou Entree pour continuer)... "
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 4 : Verifier les conflits de port
# ═══════════════════════════════════════════════════════════════════════════════
log_step 4 "Verification du port $EVIDENCE_PORT..."

if lsof -Pi :$EVIDENCE_PORT -sTCP:LISTEN -t &> /dev/null; then
    log_warn "Le port $EVIDENCE_PORT est deja utilise"
    echo "  Un autre service utilise ce port."
    echo "  Options:"
    echo "    1. Arretez le service existant"
    echo "    2. Changez le port: EVIDENCE_PORT=50081 ./scripts/deploy-docker.sh"
    echo ""
    read -p "  Continuer quand meme ? (o/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Oo]$ ]]; then
        exit 1
    fi
else
    log_ok "Port $EVIDENCE_PORT disponible"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 5 : Stopper l'ancien container si existant
# ═══════════════════════════════════════════════════════════════════════════════
log_step 5 "Nettoyage des containers existants..."

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_warn "Container existant detecte — arret et suppression..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    log_ok "Ancien container supprime"
else
    log_ok "Aucun container existant"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 6 : Construire l'image Docker
# ═══════════════════════════════════════════════════════════════════════════════
log_step 6 "Construction de l'image Docker (peut prendre 10-20 min)..."

echo ""
echo -e "  ${BLUE}Telechargement de l'image de base + installation des dependances...${NC}"
echo -e "  ${BLUE}Vous pouvez suivre la progression ci-dessous.${NC}"
echo ""

BUILD_START=$(date +%s)

if docker build -f DockerfileLocal -t "$IMAGE_NAME" . ; then
    BUILD_END=$(date +%s)
    BUILD_DURATION=$(( BUILD_END - BUILD_START ))
    BUILD_MIN=$(( BUILD_DURATION / 60 ))
    BUILD_SEC=$(( BUILD_DURATION % 60 ))
    echo ""
    log_ok "Image construite en ${BUILD_MIN}m${BUILD_SEC}s"
else
    echo ""
    fail_and_exit "Echec de la construction de l'image Docker"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 7 : Demarrer le container
# ═══════════════════════════════════════════════════════════════════════════════
log_step 7 "Demarrage de KOREV Evidence..."

# Creer le dossier de donnees persistantes
mkdir -p "$PROJECT_ROOT/docker/run/data"

# Demarrer via docker-compose
cd "$PROJECT_ROOT/docker/run"
EVIDENCE_PORT=$EVIDENCE_PORT docker compose up -d

# Attendre que le service soit pret
echo ""
echo -e "  ${BLUE}Waiting for KOREV Evidence to start...${NC}"

MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        # Try to reach the service
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$EVIDENCE_PORT" 2>/dev/null | grep -q "200\|302\|301"; then
            break
        fi
    else
        # Container stopped — something went wrong
        log_fail "Le container s'est arrete de maniere inattendue"
        echo "  Consultez les logs: docker logs $CONTAINER_NAME"
        exit 1
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo -n "."
done
echo ""

if [ $WAITED -ge $MAX_WAIT ]; then
    log_warn "Le service n'a pas repondu dans les $MAX_WAIT secondes"
    echo "  Il se peut qu'il soit encore en train de demarrer."
    echo "  Verifiez les logs: docker logs $CONTAINER_NAME"
else
    log_ok "KOREV Evidence est operationnel"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  RESULTAT FINAL
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔═══════════════════════════════════════════════════════════════╗"
echo "  ║                                                               ║"
echo "  ║       KOREV EVIDENCE — Installation Terminee                  ║"
echo "  ║                                                               ║"
echo "  ╠═══════════════════════════════════════════════════════════════╣"
echo "  ║                                                               ║"
echo "  ║   Acces:  http://localhost:$EVIDENCE_PORT                          ║"
echo "  ║                                                               ║"
echo "  ║   Commandes utiles:                                           ║"
echo "  ║     Logs:    docker logs -f $CONTAINER_NAME              ║"
echo "  ║     Stop:    docker stop $CONTAINER_NAME                 ║"
echo "  ║     Start:   docker start $CONTAINER_NAME                ║"
echo "  ║     Remove:  docker compose -f docker/run/docker-compose.yml down  ║"
echo "  ║                                                               ║"
echo "  ╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Ouvrir le navigateur
if [[ "$OSTYPE" == "darwin"* ]]; then
    sleep 2
    open "http://localhost:$EVIDENCE_PORT" 2>/dev/null || true
elif command -v xdg-open &> /dev/null; then
    sleep 2
    xdg-open "http://localhost:$EVIDENCE_PORT" 2>/dev/null || true
fi
