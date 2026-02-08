#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#  KOREV EVIDENCE - Installation Script (macOS/Linux)
#  VERSION COMPLÈTE avec toutes les customisations
#═══════════════════════════════════════════════════════════════════════════════
#
#  Usage: ./install-evidence-mac.sh
#
#  Ce script installe la vraie version KOREV Evidence (pas la version générique)
#  avec toutes les customisations : WebUI, typography, MCP servers, etc.
#
#═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
EVIDENCE_PORT="${EVIDENCE_PORT:-5050}"
PYTHON_MIN_VERSION="3.10"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           KOREV EVIDENCE - Installation macOS/Linux             ║"
echo "║                 Version complète customisée                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

#───────────────────────────────────────────────────────────────────────────────
# Step 1: Check Python
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Vérification de Python...${NC}"

# Try different Python commands
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD=$cmd
            echo -e "${GREEN}✅ Python trouvé: $($cmd --version)${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ Python 3.10+ requis mais non trouvé.${NC}"
    echo ""
    echo "Installez Python 3.11+ depuis:"
    echo "  - https://www.python.org/downloads/"
    echo "  - ou via Homebrew: brew install python@3.11"
    exit 1
fi

#───────────────────────────────────────────────────────────────────────────────
# Step 2: Check/Create virtual environment
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/6] Configuration de l'environnement virtuel...${NC}"

VENV_DIR="$PROJECT_ROOT/venv"

if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}✅ Environnement virtuel existant trouvé${NC}"
else
    echo "Création de l'environnement virtuel..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ Environnement virtuel créé${NC}"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

#───────────────────────────────────────────────────────────────────────────────
# Step 3: Install dependencies
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/6] Installation des dépendances (peut prendre plusieurs minutes)...${NC}"

# Upgrade pip
pip install --upgrade pip --quiet

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installation des dépendances principales..."
    pip install -r requirements.txt --quiet 2>&1 | grep -v "already satisfied" || true
    echo -e "${GREEN}✅ Dépendances principales installées${NC}"
fi

if [ -f "requirements2.txt" ]; then
    echo "Installation des dépendances secondaires..."
    pip install -r requirements2.txt --quiet 2>&1 | grep -v "already satisfied" || true
    echo -e "${GREEN}✅ Dépendances secondaires installées${NC}"
fi

#───────────────────────────────────────────────────────────────────────────────
# Step 4: Check .env file
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/6] Vérification de la configuration...${NC}"

ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ Fichier .env trouvé${NC}"
    
    # Check for OpenRouter key
    if grep -q "API_KEY_OPENROUTER=sk-" "$ENV_FILE"; then
        echo -e "${GREEN}✅ Clé OpenRouter configurée${NC}"
    else
        echo -e "${YELLOW}⚠️  Attention: Clé OpenRouter non configurée${NC}"
        echo "   Éditez $ENV_FILE et ajoutez votre clé OpenRouter"
    fi
else
    echo -e "${YELLOW}⚠️  Fichier .env non trouvé.${NC}"
    
    # Use .env.example if available
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        echo "Copie de .env.example vers .env..."
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        echo -e "${GREEN}✅ Fichier .env créé depuis le template${NC}"
    else
        echo "Création du fichier .env..."
        cat > "$ENV_FILE" << 'ENVFILE'
# KOREV Evidence Configuration
# Clé OpenRouter (requise) - https://openrouter.ai/keys
API_KEY_OPENROUTER=

# Port interface web
WEB_UI_PORT=5050
ANONYMIZED_TELEMETRY=false
ENVFILE
        echo -e "${GREEN}✅ Fichier .env créé${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Éditez .env et ajoutez vos clés API!${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
fi

#───────────────────────────────────────────────────────────────────────────────
# Step 5: Install Playwright (for browser automation)
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/6] Installation de Playwright (navigation web)...${NC}"

# Check if playwright is installed
if python -c "import playwright" 2>/dev/null; then
    echo "Installation des navigateurs Playwright..."
    playwright install chromium --quiet 2>/dev/null || playwright install chromium || true
    echo -e "${GREEN}✅ Playwright configuré${NC}"
else
    echo -e "${YELLOW}⚠️  Playwright non disponible (optionnel)${NC}"
fi

#───────────────────────────────────────────────────────────────────────────────
# Step 6: Launch Evidence
#───────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[6/6] Lancement de KOREV Evidence...${NC}"

# Set port
export WEB_UI_PORT=$EVIDENCE_PORT

echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           ✅ INSTALLATION TERMINÉE                            ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                               ║"
echo "║  KOREV Evidence va démarrer sur:                                ║"
echo "║  → http://localhost:$EVIDENCE_PORT                              ║"
echo "║                                                               ║"
echo "║  Pour arrêter: Ctrl+C                                         ║"
echo "║                                                               ║"
echo "║  Pour relancer plus tard:                                     ║"
echo "║  cd $(basename $PROJECT_ROOT)                                 ║"
echo "║  source venv/bin/activate                                     ║"
echo "║  python run_ui.py                                             ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Wait a moment then open browser
(sleep 5 && open "http://localhost:$EVIDENCE_PORT" 2>/dev/null || xdg-open "http://localhost:$EVIDENCE_PORT" 2>/dev/null) &

# Run Evidence
python run_ui.py
