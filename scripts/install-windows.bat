@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  KOREV EVIDENCE — Installation Windows (Docker Desktop)
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM  Double-cliquez sur ce fichier pour deployer KOREV Evidence.
REM
REM  Prerequis :
REM    1. Docker Desktop installe et lance
REM    2. Git installe (https://git-scm.com/download/win)
REM
REM  Ce script :
REM    1. Verifie Docker Desktop et Git
REM    2. Clone ou met a jour le depot
REM    3. Configure le fichier .env
REM    4. Construit l'image Docker (~15 min)
REM    5. Demarre backend + Caddy
REM    6. Ouvre le navigateur
REM
REM ═══════════════════════════════════════════════════════════════════════════════

title KOREV Evidence - Installation

echo.
echo  ==============================================================
echo.
echo        KOREV EVIDENCE — Installation Windows
echo.
echo  ==============================================================
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 1 : Verifier Docker Desktop
REM ═══════════════════════════════════════════════════════════════════════════════
echo [1/7] Verification de Docker Desktop...

where docker >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERREUR: Docker n'est pas installe.
    echo.
    echo   Installez Docker Desktop depuis :
    echo     https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)
echo   OK Docker installe

docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERREUR: Docker Desktop n'est pas lance.
    echo   Lancez Docker Desktop, attendez qu'il soit pret, puis relancez ce script.
    echo.
    pause
    exit /b 1
)
echo   OK Docker Desktop en cours d'execution

docker compose version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERREUR: Docker Compose non disponible.
    echo   Mettez a jour Docker Desktop.
    echo.
    pause
    exit /b 1
)
echo   OK Docker Compose disponible
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 2 : Verifier Git
REM ═══════════════════════════════════════════════════════════════════════════════
echo [2/7] Verification de Git...

where git >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERREUR: Git n'est pas installe.
    echo.
    echo   Installez Git depuis :
    echo     https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)
echo   OK Git installe
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 3 : Cloner ou mettre a jour le depot
REM ═══════════════════════════════════════════════════════════════════════════════
echo [3/7] Recuperation du code source...

if exist "deploy\docker-compose.yml" (
    echo   Depot detecte dans le repertoire courant
    git pull 2>nul
    echo   OK Code mis a jour
) else if exist "PRISM-Oracle\deploy\docker-compose.yml" (
    echo   Depot existant trouve dans PRISM-Oracle\
    cd PRISM-Oracle
    git pull 2>nul
    echo   OK Code mis a jour
) else (
    echo   Clonage du depot...
    git clone https://github.com/Makk7709/PRISM-Oracle.git
    if errorlevel 1 (
        echo   ERREUR: Impossible de cloner le depot
        pause
        exit /b 1
    )
    cd PRISM-Oracle
    echo   OK Depot clone
)

if not exist "deploy\docker-compose.yml" (
    echo   ERREUR: deploy\docker-compose.yml introuvable
    pause
    exit /b 1
)
if not exist "deploy\Dockerfile.backend" (
    echo   ERREUR: deploy\Dockerfile.backend introuvable
    pause
    exit /b 1
)
echo   OK Fichiers de deploiement verifies
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 4 : Configurer .env
REM ═══════════════════════════════════════════════════════════════════════════════
echo [4/7] Configuration de l'environnement...

cd deploy

if exist ".env" (
    echo   OK Fichier .env existant detecte
) else (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo   OK Fichier .env cree depuis .env.example
    ) else (
        echo   ERREUR: .env.example introuvable dans deploy\
        pause
        exit /b 1
    )
)

findstr /R "^API_KEY_OPENROUTER=.\{10,\}" .env >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ════════════════════════════════════════════════════════════
    echo     IMPORTANT : Configurez votre cle API avant de continuer
    echo   ════════════════════════════════════════════════════════════
    echo.
    echo   Ouvrez le fichier : deploy\.env
    echo   Remplissez au minimum :
    echo.
    echo     API_KEY_OPENROUTER=sk-or-v1-votre-cle-ici
    echo     AUTH_PASSWORD=VotreMotDePasseFort123!
    echo.
    echo   Obtenez une cle sur : https://openrouter.ai/keys
    echo.
    echo   Appuyez sur une touche quand c'est fait...
    pause >nul
)
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 5 : Construire l'image Docker
REM ═══════════════════════════════════════════════════════════════════════════════
echo [5/7] Construction de l'image Docker (10-20 min la premiere fois)...
echo.
echo   Telechargement des dependances et compilation...
echo.

docker compose build evidence-backend
if errorlevel 1 (
    echo.
    echo   ERREUR: Le build a echoue.
    echo.
    echo   Causes frequentes :
    echo     - Docker Desktop : Settings ^> Resources ^> augmenter RAM a 8 Go+
    echo     - Espace disque insuffisant
    echo     - Pas de connexion internet
    echo.
    echo   Pour nettoyer et reessayer :
    echo     docker system prune -af
    echo     docker compose build --no-cache evidence-backend
    echo.
    pause
    exit /b 1
)
echo.
echo   OK Image construite
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 6 : Demarrer les services
REM ═══════════════════════════════════════════════════════════════════════════════
echo [6/7] Demarrage des services...

docker compose down >nul 2>&1
docker compose up -d evidence-backend evidence-caddy
if errorlevel 1 (
    echo.
    echo   ERREUR: Echec du demarrage des services
    echo   Verifiez les logs : docker compose logs evidence-backend
    echo.
    pause
    exit /b 1
)

echo.
echo   Attente du demarrage (60s max)...

set WAITED=0
:healthcheck_loop
if %WAITED% GEQ 90 goto healthcheck_timeout
timeout /t 3 /nobreak >nul
set /a WAITED+=3
curl -s -o nul -w "%%{http_code}" http://localhost/healthz 2>nul | findstr "200" >nul 2>&1
if not errorlevel 1 goto healthcheck_ok
echo|set /p=.
goto healthcheck_loop

:healthcheck_timeout
echo.
echo   ! Le service n'a pas repondu dans les 90s
echo   Il peut encore etre en cours de demarrage.
echo   Verifiez : docker compose ps
echo   Logs : docker compose logs -f evidence-backend
goto step7

:healthcheck_ok
echo.
echo   OK Health check reussi (HTTP 200)

REM ═══════════════════════════════════════════════════════════════════════════════
REM  STEP 7 : Verification finale
REM ═══════════════════════════════════════════════════════════════════════════════
:step7
echo.
echo [7/7] Verification finale...
echo.
docker compose ps
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  RESULTAT
REM ═══════════════════════════════════════════════════════════════════════════════
echo.
echo  ==============================================================
echo.
echo       KOREV EVIDENCE — Installation Terminee !
echo.
echo  ==============================================================
echo.
echo   Acces : http://localhost
echo.
echo   Login : voir AUTH_LOGIN / AUTH_PASSWORD dans deploy\.env
echo.
echo   Commandes utiles (depuis deploy\) :
echo     Etat    : docker compose ps
echo     Logs    : docker compose logs -f evidence-backend
echo     Stop    : docker compose down
echo     Start   : docker compose up -d
echo     Rebuild : docker compose build evidence-backend
echo.
echo   Les cles API peuvent aussi etre configurees depuis
echo   l'interface web : Settings (icone engrenage).
echo.
echo  ==============================================================
echo.

start "" "http://localhost"

pause
