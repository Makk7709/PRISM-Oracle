@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  KOREV EVIDENCE - Script de desinstallation (Windows)
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM  Supprime l'environnement virtuel et les fichiers temporaires
REM  NE SUPPRIME PAS: le code source, .env, ni les donnees utilisateur
REM
REM ═══════════════════════════════════════════════════════════════════════════════

title Korev Evidence - Desinstallation

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║          KOREV EVIDENCE - Desinstallation Windows             ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

echo Ce script va supprimer:
echo.
echo   ✓ venv/              ^(environnement virtuel, ~2-5 GB^)
echo   ✓ __pycache__/       ^(cache Python^)
echo   ✓ .pytest_cache/     ^(cache tests^)
echo   ✓ *.pyc              ^(fichiers compiles^)
echo   ✓ logs/              ^(fichiers log^)
echo   ✓ tmp/               ^(fichiers temporaires^)
echo.
echo Ce script NE supprime PAS:
echo.
echo   ✗ .env               ^(votre configuration^)
echo   ✗ Code source        ^(fichiers .py, .html, etc.^)
echo   ✗ data/              ^(vos donnees^)
echo   ✗ memory/            ^(memoire agent^)
echo.

set /p CONFIRM="Voulez-vous continuer? (O/N): "
if /i not "%CONFIRM%"=="O" (
    echo.
    echo Desinstallation annulee.
    pause
    exit /b 0
)

echo.
echo ───────────────────────────────────────────────────────────────────
echo Suppression en cours...
echo ───────────────────────────────────────────────────────────────────
echo.

REM Remove virtual environment
if exist "venv" (
    echo Suppression de venv/...
    rmdir /s /q "venv" 2>nul
    if exist "venv" (
        echo ⚠️  Impossible de supprimer venv/ completement
        echo    Fermez tous les terminaux Python et reessayez
    ) else (
        echo ✓ venv/ supprime
    )
) else (
    echo ✓ venv/ n'existe pas
)

REM Remove Python cache
echo Suppression des caches Python...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)
echo ✓ __pycache__/ supprime

REM Remove pytest cache
if exist ".pytest_cache" (
    rmdir /s /q ".pytest_cache" 2>nul
    echo ✓ .pytest_cache/ supprime
)

REM Remove .pyc files
del /s /q *.pyc 2>nul
echo ✓ Fichiers .pyc supprimes

REM Remove logs
if exist "logs" (
    rmdir /s /q "logs" 2>nul
    echo ✓ logs/ supprime
)

REM Remove tmp
if exist "tmp" (
    for /f %%f in ('dir /b "tmp" 2^>nul ^| find /c /v ""') do set FILE_COUNT=%%f
    if not "%FILE_COUNT%"=="0" (
        del /q "tmp\*" 2>nul
    )
    echo ✓ tmp/ nettoye
)

REM Remove coverage files
if exist ".coverage" (
    del /q ".coverage" 2>nul
    echo ✓ .coverage supprime
)

echo.
echo ───────────────────────────────────────────────────────────────────
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║           ✓ DESINSTALLATION TERMINEE                          ║
echo ╠═══════════════════════════════════════════════════════════════╣
echo ║                                                               ║
echo ║  Pour reinstaller:                                            ║
echo ║  → Double-cliquez sur install-windows.bat                     ║
echo ║                                                               ║
echo ║  Pour supprimer completement:                                 ║
echo ║  → Supprimez le dossier KOREV_Oracle manuellement             ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

pause
