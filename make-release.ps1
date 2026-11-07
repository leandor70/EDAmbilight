# make-release.ps1 — Build and package EDAmbilight for GitHub Releases.
#
#   .\make-release.ps1 -Version "1.0.0"
#
# Produces: EDAmbilight-v1.0.0.zip  (ready to attach to a GitHub Release)
param(
    [Parameter(Mandatory)][string]$Version,
    [switch]$SkipBuild
)

Set-Location $PSScriptRoot
$zipName = "EDAmbilight-v$Version.zip"

if (-not $SkipBuild) {
    Write-Host "Building exe..." -ForegroundColor Cyan
    .\build.ps1
    if ($LASTEXITCODE -ne 0) { Write-Error "Build failed"; exit 1 }
}

if (-not (Test-Path "dist\EDAmbilight\EDAmbilight.exe")) {
    Write-Error "dist\EDAmbilight\EDAmbilight.exe not found. Run without -SkipBuild or run build.ps1 first."
    exit 1
}

# Every page linked from the sidebar must be in the package (a page deleted from
# the working tree once shipped two releases with a dead Preview link).
$navPages = [regex]::Matches((Get-Content "web\js\navigation.js" -Raw), "href:\s*'([^']+\.html)'") |
    ForEach-Object { $_.Groups[1].Value }
$missing = @($navPages + "index.html", "loading.html" | Sort-Object -Unique |
    Where-Object { -not (Test-Path "dist\EDAmbilight\web\$_") })
if ($missing.Count -gt 0) {
    Write-Error "Pages missing from dist\EDAmbilight\web: $($missing -join ', '). Restore them and run build.ps1 again."
    exit 1
}

# Create a clean staging area
$stage = "dist\_release_stage\EDAmbilight"
Remove-Item -Recurse -Force "dist\_release_stage" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $stage | Out-Null

# Copy distributable content
Copy-Item -Recurse "dist\EDAmbilight\*" $stage
Copy-Item "README.md"    $stage
Copy-Item "CHANGELOG.md" $stage
Copy-Item "LICENSE"      $stage
Copy-Item "NOTICE.md"    $stage
Copy-Item "THIRD-PARTY.md" $stage
Copy-Item -Recurse "licenses" $stage

# Default config (no personal settings)
New-Item -ItemType Directory -Force "$stage\config" | Out-Null
@'
{
  "openrgb_host": "localhost",
  "openrgb_port": 6742
}
'@ | Set-Content "$stage\config\settings.json" -Encoding UTF8

# Create zip
Remove-Item $zipName -ErrorAction SilentlyContinue
Compress-Archive -Path "dist\_release_stage\EDAmbilight" -DestinationPath $zipName
Remove-Item -Recurse -Force "dist\_release_stage"

Write-Host ""
Write-Host "Release package ready: $zipName" -ForegroundColor Green
Write-Host "Attach this file to the GitHub Release for v$Version."
