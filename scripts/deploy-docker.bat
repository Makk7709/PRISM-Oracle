@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  KOREV EVIDENCE — Deploiement Docker One-Click (Windows)
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM  Double-cliquez sur ce fichier pour deployer KOREV Evidence via Docker.
REM
REM  Prerequis: Docker Desktop installe et lance
REM
REM  Ce script:
REM    1. Verifie Docker Desktop
REM    2. Configure le fichier .env
REM    3. Construit l'image KOREV Evidence
REM    4. Demarre le container
REM    5. Ouvre le navigateur
REM
REM ═══════════════════════════════════════════════════════════════════════════════

title KOREV Evidence - Deploiement Docker

echo.
echo  ===============================================================
echo    KOREV EVIDENCE — Deploiement Docker
echo    Installation One-Click
echo  ===============================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 1 : Verifier Docker Desktop
REM ═══════════════════════════════════════════════════════════════════════════════
echo [1/6] Verification de Docker Desktop...

where docker >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERREUR: Docker n'est pas installe.
    echo.
    echo   Installez Docker Desktop depuis:
    echo     https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)
echo   OK Docker installe

REM Verifier que Docker tourne
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERREUR: Docker Desktop n'est pas lance.
    echo.
    echo   Lancez Docker Desktop puis relancez ce script.
    echo.
    pause
    exit /b 1
)
echo   OK Docker Desktop en cours d'execution
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 2 : Verifier les fichiers du projet
REM ═══════════════════════════════════════════════════════════════════════════════
echo [2/6] Verification des fichiers du projet...

if not exist "DockerfileLocal" (
    echo   ERREUR: DockerfileLocal introuvable
    echo   Assurez-vous d'executer ce script depuis le dossier korev-evidence
    pause
    exit /b 1
)
echo   OK DockerfileLocal present

if not exist "docker\run\docker-compose.yml" (
    echo   ERREUR: docker-compose.yml introuvable
    pause
    exit /b 1
)
echo   OK docker-compose.yml present
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 3 : Configurer le fichier .env
REM ═══════════════════════════════════════════════════════════════════════════════
echo [3/6] Configuration du fichier .env...

if exist ".env" (
    echo   OK Fichier .env existant detecte
) else (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo   OK Fichier .env cree depuis .env.example
    ) else (
        (
            echo # KOREV EVIDENCE - Configuration
            echo # Cle API principale ^(REQUISE^) - https://openrouter.ai/keys
            echo API_KEY_OPENROUTER=
            echo.
            echo # Port interface web
            echo WEB_UI_PORT=5050
            echo ANONYMIZED_TELEMETRY=false
        ) > .env
        echo   OK Fichier .env cree
    )
    echo.
    echo   ════════════════════════════════════════════════════════
    echo   IMPORTANT: Editez .env et ajoutez votre cle API!
    echo   API_KEY_OPENROUTER=votre-cle-ici
    echo   ════════════════════════════════════════════════════════
    echo.
    pause
)
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 4 : Stopper l'ancien container si existant
REM ═══════════════════════════════════════════════════════════════════════════════
echo [4/6] Nettoyage des containers existants...

docker stop korev-evidence >nul 2>&1
docker rm korev-evidence >nul 2>&1
echo   OK Nettoyage effectue
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 5 : Construire l'image Docker
REM ═══════════════════════════════════════════════════════════════════════════════
echo [5/6] Construction de l'image Docker (peut prendre 10-20 min)...
echo.
echo   Telechargement de l'image de base + installation des dependances...
echo   Vous pouvez suivre la progression ci-dessous.
echo.

docker build -f DockerfileLocal -t korev-evidence:local .
if errorlevel 1 (
    echo.
    echo   ERREUR: Echec de la construction de l'image Docker
    echo   Verifiez que Docker Desktop est lance et que vous avez Internet.
    pause
    exit /b 1
)
echo.
echo   OK Image korev-evidence:local construite
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 6 : Demarrer le container
REM ═══════════════════════════════════════════════════════════════════════════════
echo [6/6] Demarrage de KOREV Evidence...

REM Creer le dossier de donnees
if not exist "docker\run\data" mkdir "docker\run\data"

cd docker\run
docker compose up -d
if errorlevel 1 (
    echo.
    echo   ERREUR: Echec du demarrage du container
    echo   Verifiez les logs: docker logs korev-evidence
    pause
    exit /b 1
)

echo.
echo   Waiting for KOREV Evidence to start...

REM Attendre quelques secondes
timeout /t 10 /nobreak >nul

echo.
echo   OK KOREV Evidence demarre

cd /d "%PROJECT_ROOT%"

REM ═══════════════════════════════════════════════════════════════════════════════
REM  RESULTAT FINAL
REM ═══════════════════════════════════════════════════════════════════════════════
echo.
echo  ===============================================================
echo.
echo    KOREV EVIDENCE — Installation Terminee
echo.
echo    Acces:  http://localhost:50080
echo.
echo    Commandes utiles:
echo      Logs:    docker logs -f korev-evidence
echo      Stop:    docker stop korev-evidence
echo      Start:   docker start korev-evidence
echo      Remove:  docker compose -f docker/run/docker-compose.yml down
echo.
echo  ===============================================================
echo.

REM Ouvrir le navigateur
start "" "http://localhost:50080"

pause
