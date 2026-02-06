@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  KOREV EVIDENCE - Script de mise a jour (Windows)
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM  Met a jour les dependances et relance Evidence
REM  Usage: Double-cliquez sur ce fichier
REM
REM ═══════════════════════════════════════════════════════════════════════════════

title Korev Evidence - Mise a jour

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║          KOREV EVIDENCE - Mise a jour Windows                 ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 1: Check venv exists
REM ───────────────────────────────────────────────────────────────────────────────
echo [1/4] Verification de l'environnement...

if not exist "venv" (
    echo.
    echo ❌ Environnement virtuel non trouve.
    echo    Executez d'abord install-windows.bat
    echo.
    pause
    exit /b 1
)

echo ✓ Environnement virtuel trouve
echo.

REM Activate venv
call venv\Scripts\activate.bat

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 2: Git pull (if git repo)
REM ───────────────────────────────────────────────────────────────────────────────
echo [2/4] Mise a jour du code source...

where git >nul 2>&1
if not errorlevel 1 (
    if exist ".git" (
        echo    Recuperation des mises a jour depuis Git...
        git pull --rebase 2>nul
        if errorlevel 1 (
            echo ⚠️  Git pull echoue ^(modifications locales?^)
            echo    Continuons avec la version actuelle...
        ) else (
            echo ✓ Code source mis a jour
        )
    ) else (
        echo ⚠️  Pas un depot Git, mise a jour manuelle requise
    )
) else (
    echo ⚠️  Git non installe, mise a jour manuelle requise
)
echo.

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 3: Update dependencies
REM ───────────────────────────────────────────────────────────────────────────────
echo [3/4] Mise a jour des dependances...

pip install --upgrade pip --quiet

if exist "requirements.txt" (
    echo    Installation des dependances principales...
    pip install -r requirements.txt --upgrade --quiet
    echo ✓ Dependances principales mises a jour
)

if exist "requirements2.txt" (
    echo    Installation des dependances secondaires...
    pip install -r requirements2.txt --upgrade --quiet
    echo ✓ Dependances secondaires mises a jour
)
echo.

REM ───────────────────────────────────────────────────────────────────────────────
REM Step 4: Verify critical dependencies
REM ───────────────────────────────────────────────────────────────────────────────
echo [4/4] Verification des dependances critiques...

python -c "import argon2; print('   argon2-cffi:', argon2.__version__)" 2>nul
if errorlevel 1 (
    echo ⚠️  argon2-cffi manquant, installation...
    pip install argon2-cffi --quiet
)

python -c "import redis; print('   redis:', redis.__version__)" 2>nul
if errorlevel 1 (
    echo ⚠️  redis manquant, installation...
    pip install redis --quiet
)

python -c "import flask; print('   flask:', flask.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ Flask non installe - erreur critique
    pause
    exit /b 1
)

echo ✓ Dependances critiques OK
echo.

REM ───────────────────────────────────────────────────────────────────────────────
REM Done
REM ───────────────────────────────────────────────────────────────────────────────
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║           ✓ MISE A JOUR TERMINEE                              ║
echo ╠═══════════════════════════════════════════════════════════════╣
echo ║                                                               ║
echo ║  Pour lancer Korev Evidence:                                  ║
echo ║  → Double-cliquez sur install-windows.bat                     ║
echo ║                                                               ║
echo ║  OU manuellement:                                             ║
echo ║  1. venv\Scripts\activate                                     ║
echo ║  2. python run_ui.py                                          ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

set /p LAUNCH="Voulez-vous lancer Evidence maintenant? (O/N): "
if /i "%LAUNCH%"=="O" (
    echo.
    echo Lancement de Korev Evidence...
    echo → http://localhost:5050
    echo.
    start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5050"
    python run_ui.py
)

pause
