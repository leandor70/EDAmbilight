@echo off
setlocal
cd /d "%~dp0"
title EDAmbilight
color 0B

cls
echo.
echo  ================================================
echo   EDAmbilight  --  Screen Ambient Lighting
echo  ================================================
echo.

:: Verifica Python
echo  Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERRORE] Python non trovato nel PATH.
    echo  Installa Python 3.9+ da https://python.org
    echo  e assicurati di spuntare "Add to PATH".
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK] %%v

:: Verifica dipendenze
echo  Checking dependencies...
python -c "import eel, numpy, mss" >nul 2>&1
if errorlevel 1 (
    echo  [WARN] Dipendenze mancanti. Installo requirements.txt...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  [ERRORE] Installazione dipendenze fallita.
        echo  Prova manualmente: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
)
echo  [OK] Dependencies OK

echo.
echo  ------------------------------------------------
echo  Avvio in corso...
echo  Browser: http://localhost:8001
echo  ------------------------------------------------
echo.

python src\main.py

echo.
echo  Applicazione terminata.
pause
