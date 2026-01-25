@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  KOREV ORACLE - Installation Script (Windows Batch)
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM  Double-cliquez sur ce fichier pour lancer l'installation.
REM
REM ═══════════════════════════════════════════════════════════════════════════════

title Korev Oracle - Installation

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║           KOREV ORACLE - Installation Windows                 ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Check Docker
echo [1/4] Verification de Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Docker n'est pas installe.
    echo.
    echo Installez Docker Desktop depuis: https://www.docker.com/products/docker-desktop/
    echo Puis relancez ce script.
    echo.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Docker n'est pas lance.
    echo.
    echo Lancez Docker Desktop et attendez qu'il soit pret.
    echo Puis relancez ce script.
    echo.
    pause
    exit /b 1
)

echo ✓ Docker OK
echo.

REM Pull image
echo [2/4] Telechargement de l'image Docker...
echo (Cela peut prendre plusieurs minutes la premiere fois)
echo.
docker pull korevai/korev-oracle-base:latest
if errorlevel 1 (
    echo.
    echo ❌ Echec du telechargement
    pause
    exit /b 1
)
echo.
echo ✓ Image OK
echo.

REM Check .env
echo [3/4] Verification du fichier .env...
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "ENV_FILE=%PROJECT_ROOT%\.env"

if not exist "%ENV_FILE%" (
    echo.
    echo ⚠️  Fichier .env non trouve.
    echo.
    echo Creez un fichier .env dans le dossier racine avec vos cles API.
    echo Exemple:
    echo   API_KEY_OPENAI=sk-votre-cle
    echo   API_KEY_OPENROUTER=sk-votre-cle
    echo.
    echo Puis relancez ce script.
    pause
    exit /b 1
)
echo ✓ .env OK
echo.

REM Launch
echo [4/4] Lancement d'Oracle...
cd /d "%PROJECT_ROOT%\docker\run"

docker compose up -d
if errorlevel 1 (
    docker-compose up -d
)

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║           ✓ INSTALLATION TERMINEE                             ║
echo ╠═══════════════════════════════════════════════════════════════╣
echo ║                                                               ║
echo ║  Oracle est accessible sur:                                   ║
echo ║  → http://localhost:50080                                     ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

set /p OPEN_BROWSER="Ouvrir dans le navigateur? (o/n): "
if /i "%OPEN_BROWSER%"=="o" (
    start http://localhost:50080
)

echo.
pause
