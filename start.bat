@echo off
setlocal EnableDelayedExpansion
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

:: Verifica backend di cattura opzionali (WGC / DXGI)
python -c "import windows_capture" >nul 2>&1
set HAS_WGC=%errorlevel%
python -c "import dxcam" >nul 2>&1
set HAS_DXCAM=%errorlevel%
if "%HAS_WGC%"=="0" (
    echo  [OK] Cattura schermo: WGC
) else if "%HAS_DXCAM%"=="0" (
    echo  [OK] Cattura schermo: DXGI ^(dxcam^)
) else (
    echo  [WARN] Nessun backend veloce installato: uso mss ^(piu lento, no fullscreen esclusivo^).
    echo         Per migliorare: pip install dxcam
)

:: Verifica porta web (web_port in config\settings.json, default 8001)
set WEBPORT=8001
if exist config\settings.json (
    for /f %%p in ('python -c "import json;print(json.load(open('config/settings.json')).get('web_port',8001))" 2^>nul') do set WEBPORT=%%p
)
set PORT_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:"[0-9]:%WEBPORT% .*LISTENING"') do set PORT_PID=%%a
if defined PORT_PID (
    set PORT_PROC=sconosciuto
    for /f "tokens=1 delims=," %%n in ('tasklist /FI "PID eq %PORT_PID%" /NH /FO CSV 2^>nul') do set PORT_PROC=%%~n
    echo.
    echo  [ATTENZIONE] La porta %WEBPORT% e' gia' in uso da: !PORT_PROC! ^(PID !PORT_PID!^).
    echo  Probabilmente EDAmbilight e' gia' in esecuzione ^(controlla la system tray^).
    echo.
    choice /c SN /m " Chiudere quel processo e continuare"
    if errorlevel 2 (
        echo  Avvio annullato.
        pause
        exit /b 1
    )
    taskkill /PID %PORT_PID% /F >nul 2>&1
    if errorlevel 1 (
        echo  [ERRORE] Impossibile chiudere il processo. Chiudilo a mano e riprova.
        pause
        exit /b 1
    )
    timeout /t 2 /nobreak >nul
    echo  [OK] Porta %WEBPORT% liberata
) else (
    echo  [OK] Porta %WEBPORT% libera
)

echo.
echo  ------------------------------------------------
echo  Avvio in corso...
echo  Browser: http://localhost:%WEBPORT%
echo  ------------------------------------------------
echo.

python src\main.py

echo.
echo  Applicazione terminata.
pause
