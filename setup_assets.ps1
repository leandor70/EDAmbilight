<#
.SYNOPSIS
    Copia gli asset statici (CSS, font, immagini) da EDLogReader a EDAmbilight.
    Da eseguire una volta dopo il clone, o ogni volta che il progetto principale
    aggiorna i file di stile.

.USAGE
    cd D:\Lavori\Claude\EDAmbilight
    .\setup_assets.ps1
#>

$src  = "$PSScriptRoot\..\EDLogReader\web"
$dest = "$PSScriptRoot\web"

if (-not (Test-Path $src)) {
    Write-Error "EDLogReader non trovato in: $src"
    Write-Host "Modifica la variabile `$src` con il percorso corretto."
    exit 1
}

# CSS
Write-Host "Copio CSS..."
Copy-Item "$src\css\tailwind.min.css" "$dest\css\" -Force
Copy-Item "$src\css\fonts.css"        "$dest\css\" -Force

# Font WOFF2
Write-Host "Copio fonts..."
Copy-Item "$src\fonts\*.woff2" "$dest\fonts\" -Force

# Immagini di sfondo (opzionale)
$bgSrc  = "$src\images\backgrounds"
$bgDest = "$dest\images\backgrounds"
if (Test-Path $bgSrc) {
    Write-Host "Copio sfondi..."
    Copy-Item "$bgSrc\*.jpg" "$bgDest\" -Force -ErrorAction SilentlyContinue
    Copy-Item "$bgSrc\*.png" "$bgDest\" -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[OK] Asset copiati. EDAmbilight e' pronto."
