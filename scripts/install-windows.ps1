#═══════════════════════════════════════════════════════════════════════════════
#  KOREV ORACLE - Installation Script (Windows PowerShell)
#═══════════════════════════════════════════════════════════════════════════════
#
#  Usage: 
#    1. Ouvrir PowerShell en tant qu'Administrateur
#    2. Exécuter: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#    3. Exécuter: .\install-windows.ps1
#
#  Ce script:
#  1. Vérifie que Docker Desktop est installé et lancé
#  2. Vérifie WSL2
#  3. Pré-télécharge l'image Docker
#  4. Vérifie/crée le fichier .env
#  5. Lance Oracle via docker-compose
#
#═══════════════════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

# Configuration
$ORACLE_PORT = if ($env:ORACLE_PORT) { $env:ORACLE_PORT } else { "50080" }
$DOCKER_IMAGE = "agent0ai/agent-zero:latest"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           KOREV ORACLE - Installation Windows                 ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

#───────────────────────────────────────────────────────────────────────────────
# Step 1: Check Docker
#───────────────────────────────────────────────────────────────────────────────
Write-Host "[1/6] Vérification de Docker..." -ForegroundColor Yellow

$dockerPath = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerPath) {
    Write-Host "❌ Docker n'est pas installé." -ForegroundColor Red
    Write-Host ""
    Write-Host "Installez Docker Desktop depuis: https://www.docker.com/products/docker-desktop/" -ForegroundColor White
    Write-Host "Assurez-vous d'activer WSL2 lors de l'installation." -ForegroundColor White
    Write-Host ""
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}

# Check if Docker daemon is running
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "✅ Docker installé et en cours d'exécution" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker n'est pas lancé." -ForegroundColor Red
    Write-Host ""
    Write-Host "Lancez Docker Desktop et attendez qu'il soit prêt (icône verte dans la barre des tâches)." -ForegroundColor White
    Write-Host "Puis relancez ce script." -ForegroundColor White
    Write-Host ""
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}

#───────────────────────────────────────────────────────────────────────────────
# Step 2: Check WSL2
#───────────────────────────────────────────────────────────────────────────────
Write-Host "[2/6] Vérification de WSL2..." -ForegroundColor Yellow

$wslPath = Get-Command wsl -ErrorAction SilentlyContinue
if ($wslPath) {
    try {
        $wslVersion = wsl --version 2>&1
        Write-Host "✅ WSL2 disponible" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  WSL2 peut ne pas être correctement configuré" -ForegroundColor Yellow
        Write-Host "   Docker Desktop fonctionne mieux avec WSL2." -ForegroundColor White
    }
} else {
    Write-Host "⚠️  WSL non détecté" -ForegroundColor Yellow
    Write-Host "   Pour de meilleures performances, installez WSL2:" -ForegroundColor White
    Write-Host "   wsl --install" -ForegroundColor White
}

#───────────────────────────────────────────────────────────────────────────────
# Step 3: Check docker-compose
#───────────────────────────────────────────────────────────────────────────────
Write-Host "[3/6] Vérification de docker-compose..." -ForegroundColor Yellow

$composeCmd = $null
try {
    docker compose version 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $composeCmd = "docker compose"
        Write-Host "✅ docker compose disponible" -ForegroundColor Green
    }
} catch {}

if (-not $composeCmd) {
    $dockerComposePath = Get-Command docker-compose -ErrorAction SilentlyContinue
    if ($dockerComposePath) {
        $composeCmd = "docker-compose"
        Write-Host "✅ docker-compose disponible" -ForegroundColor Green
    } else {
        Write-Host "❌ docker-compose n'est pas disponible." -ForegroundColor Red
        Write-Host "Docker Desktop devrait inclure docker-compose. Réinstallez Docker Desktop." -ForegroundColor White
        Read-Host "Appuyez sur Entrée pour quitter"
        exit 1
    }
}

#───────────────────────────────────────────────────────────────────────────────
# Step 4: Pre-pull Docker image
#───────────────────────────────────────────────────────────────────────────────
Write-Host "[4/6] Téléchargement de l'image Docker (peut prendre plusieurs minutes)..." -ForegroundColor Yellow

$imageExists = docker image inspect $DOCKER_IMAGE 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Image déjà présente localement" -ForegroundColor Green
} else {
    Write-Host "Téléchargement de $DOCKER_IMAGE..." -ForegroundColor White
    docker pull $DOCKER_IMAGE
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Échec du téléchargement de l'image" -ForegroundColor Red
        Read-Host "Appuyez sur Entrée pour quitter"
        exit 1
    }
    Write-Host "✅ Image téléchargée" -ForegroundColor Green
}

#───────────────────────────────────────────────────────────────────────────────
# Step 5: Check/Create .env file
#───────────────────────────────────────────────────────────────────────────────
Write-Host "[5/6] Vérification du fichier .env..." -ForegroundColor Yellow

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$EnvFile = Join-Path $ProjectRoot ".env"

if (Test-Path $EnvFile) {
    Write-Host "✅ Fichier .env trouvé" -ForegroundColor Green
    
    $envContent = Get-Content $EnvFile -Raw
    if ($envContent -match "API_KEY_OPENAI=sk-" -or $envContent -match "API_KEY_OPENROUTER=sk-") {
        Write-Host "✅ Clés API configurées" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Attention: Aucune clé API détectée dans .env" -ForegroundColor Yellow
        Write-Host "   Oracle a besoin d'au moins une clé API (OpenAI ou OpenRouter)." -ForegroundColor White
        Write-Host "   Éditez le fichier .env avant de continuer." -ForegroundColor White
    }
} else {
    Write-Host "⚠️  Fichier .env non trouvé. Création à partir du template..." -ForegroundColor Yellow
    
    $envTemplate = @"
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
"@
    
    $envTemplate | Out-File -FilePath $EnvFile -Encoding UTF8
    Write-Host "✅ Fichier .env créé" -ForegroundColor Green
    Write-Host "   ⚠️  IMPORTANT: Éditez $EnvFile et ajoutez vos clés API" -ForegroundColor Yellow
}

#───────────────────────────────────────────────────────────────────────────────
# Step 6: Launch Oracle
#───────────────────────────────────────────────────────────────────────────────
Write-Host "[6/6] Lancement d'Oracle..." -ForegroundColor Yellow

$DockerDir = Join-Path $ProjectRoot "docker\run"
$ComposeFile = Join-Path $DockerDir "docker-compose.yml"

if (-not (Test-Path $ComposeFile)) {
    Write-Host "❌ docker-compose.yml non trouvé dans $DockerDir" -ForegroundColor Red
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}

Set-Location $DockerDir

# Check if already running
$runningContainers = docker ps --format '{{.Names}}' 2>&1
if ($runningContainers -match "korev-oracle") {
    Write-Host "Oracle est déjà en cours d'exécution." -ForegroundColor Yellow
    Write-Host ""
    $restart = Read-Host "Voulez-vous le redémarrer? (o/n)"
    if ($restart -eq "o" -or $restart -eq "O") {
        if ($composeCmd -eq "docker compose") {
            docker compose down
            docker compose up -d
        } else {
            docker-compose down
            docker-compose up -d
        }
    }
} else {
    if ($composeCmd -eq "docker compose") {
        docker compose up -d
    } else {
        docker-compose up -d
    }
}

#───────────────────────────────────────────────────────────────────────────────
# Done
#───────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           ✅ INSTALLATION TERMINÉE                            ║" -ForegroundColor Green
Write-Host "╠═══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║                                                               ║" -ForegroundColor Green
Write-Host "║  Oracle est accessible sur:                                   ║" -ForegroundColor Green
Write-Host "║  → http://localhost:$ORACLE_PORT                              ║" -ForegroundColor Green
Write-Host "║                                                               ║" -ForegroundColor Green
Write-Host "║  Commandes utiles (dans PowerShell):                          ║" -ForegroundColor Green
Write-Host "║  • Logs:    docker logs -f korev-oracle                       ║" -ForegroundColor Green
Write-Host "║  • Stop:    docker stop korev-oracle                          ║" -ForegroundColor Green
Write-Host "║  • Start:   docker start korev-oracle                         ║" -ForegroundColor Green
Write-Host "║  • Restart: docker restart korev-oracle                       ║" -ForegroundColor Green
Write-Host "║                                                               ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Open browser
$openBrowser = Read-Host "Ouvrir Oracle dans le navigateur? (o/n)"
if ($openBrowser -eq "o" -or $openBrowser -eq "O") {
    Start-Process "http://localhost:$ORACLE_PORT"
}

Write-Host ""
Read-Host "Appuyez sur Entrée pour quitter"
