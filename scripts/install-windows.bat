@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  KOREV EVIDENCE - Installation Script (Windows)
REM  VERSION COMPLÈTE avec toutes les customisations
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM  Double-cliquez sur ce fichier pour installer et lancer Korev Evidence
REM  avec toutes les customisations : WebUI, typography, MCP servers, etc.
REM
REM ═══════════════════════════════════════════════════════════════════════════════

title Korev Evidence - Installation

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║          KOREV EVIDENCE - Installation Windows                ║
echo ║                Version complete customisee                    ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 1: Check Python
REM ───────────────────────────────────────────────────────────────────────────────
echo [1/6] Verification de Python...

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Python n'est pas installe.
    echo.
    echo Installez Python 3.11+ depuis:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Cochez "Add Python to PATH" lors de l'installation!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    Python %PYTHON_VERSION% detecte

REM Verify Python 3.11+ (strict check)
python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>nul
if errorlevel 1 (
    echo.
    echo ❌ Python 3.11 ou superieur requis ^(version actuelle: %PYTHON_VERSION%^)
    echo.
    echo Installez Python 3.11+ depuis:
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo ✓ Python %PYTHON_VERSION% OK ^(3.11+ requis^)
echo.

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 2: Create virtual environment
REM ───────────────────────────────────────────────────────────────────────────────
echo [2/6] Configuration de l'environnement virtuel...

if exist "venv" (
    echo ✓ Environnement virtuel existant
) else (
    echo Creation de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Echec de creation du venv
        pause
        exit /b 1
    )
    echo ✓ Environnement virtuel cree
)
echo.

REM Activate venv
call venv\Scripts\activate.bat

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 3: Install dependencies
REM ───────────────────────────────────────────────────────────────────────────────
echo [3/6] Installation des dependances (peut prendre plusieurs minutes)...
echo.

pip install --upgrade pip --quiet

if exist "requirements.txt" (
    echo Installation des dependances principales...
    pip install -r requirements.txt --quiet
    echo ✓ Dependances principales installees
)

if exist "requirements2.txt" (
    echo Installation des dependances secondaires...
    pip install -r requirements2.txt --quiet
    echo ✓ Dependances secondaires installees
)
echo.

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 4: Check .env file
REM ───────────────────────────────────────────────────────────────────────────────
echo [4/6] Verification de la configuration...

if exist ".env" (
    echo ✓ Fichier .env trouve
) else (
    echo ⚠️  Fichier .env non trouve.
    if exist ".env.example" (
        echo Copie de .env.example vers .env...
        copy ".env.example" ".env" >nul
        echo ✓ Fichier .env cree depuis le template
    ) else (
        echo Creation du fichier .env...
        (
            echo # Korev Evidence Configuration
            echo # Cle OpenRouter ^(requise^) - https://openrouter.ai/keys
            echo API_KEY_OPENROUTER=
            echo.
            echo # Port interface web
            echo WEB_UI_PORT=5050
            echo ANONYMIZED_TELEMETRY=false
        ) > .env
        echo ✓ Fichier .env cree
    )
    echo.
    echo    ════════════════════════════════════════════════════════
    echo    ⚠️  IMPORTANT: Editez .env et ajoutez vos cles API!
    echo    ════════════════════════════════════════════════════════
)
echo.

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 5: Install Playwright
REM ───────────────────────────────────────────────────────────────────────────────
echo [5/6] Installation de Playwright (navigation web)...

python -c "import playwright" >nul 2>&1
if not errorlevel 1 (
    playwright install chromium >nul 2>&1
    echo ✓ Playwright configure
) else (
    echo ⚠️  Playwright non disponible ^(optionnel^)
)
echo.

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 6: Launch Evidence
REM ───────────────────────────────────────────────────────────────────────────────
echo [6/6] Lancement de Korev Evidence...

set WEB_UI_PORT=5050

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║           ✓ INSTALLATION TERMINEE                             ║
echo ╠═══════════════════════════════════════════════════════════════╣
echo ║                                                               ║
echo ║  Korev Evidence demarre sur:                                  ║
echo ║  → http://localhost:5050                                      ║
echo ║                                                               ║
echo ║  Pour arreter: Fermez cette fenetre ou Ctrl+C                 ║
echo ║                                                               ║
echo ║  Pour relancer plus tard:                                     ║
echo ║  1. Ouvrez un terminal dans le dossier                        ║
echo ║  2. venv\Scripts\activate                                     ║
echo ║  3. python run_ui.py                                          ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Open browser after delay
start "" /b cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:5050"

REM Run Evidence
python run_ui.py

pause
