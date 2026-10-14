# Build EDAmbilight.exe — PyInstaller onedir + web/ accanto all'exe.
#
#   .\build.ps1            build windowed (senza console)
#   .\build.ps1 -Console   build con console (debug)
#
# Output: dist\EDAmbilight\EDAmbilight.exe
param([switch]$Console)

Set-Location $PSScriptRoot

$pyiArgs = @(
    '--noconfirm', '--clean',
    '--name', 'EDAmbilight',
    '--collect-data', 'eel',
    '--hidden-import', 'bottle_websocket',
    '--collect-all', 'dxcam',
    '--hidden-import', 'comtypes',
    '--workpath', 'build',
    '--distpath', 'dist',
    '--specpath', 'build'
)
if (-not $Console)         { $pyiArgs += '--noconsole' }
if (Test-Path 'icon.ico')  { $pyiArgs += @('--icon', (Resolve-Path 'icon.ico').Path) }
$pyiArgs += 'src\main.py'

pyinstaller @pyiArgs
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed"; exit 1 }

# web/ deve stare accanto all'exe: get_base_dir() in frozen mode punta
# alla cartella dell'eseguibile (e così config/ e log/ restano scrivibili).
Copy-Item -Recurse -Force 'web' 'dist\EDAmbilight\web'

Write-Host ""
Write-Host "Build completata: dist\EDAmbilight\EDAmbilight.exe" -ForegroundColor Green
Write-Host "Distribuisci l'intera cartella dist\EDAmbilight (config/ viene creata al primo avvio)."
