# Studio/studio-setup.ps1 — Windows setup for the Studio addon
# Usage: .\Studio\studio-setup.ps1

Write-Host "[Studio Setup] Installing Studio dependencies..." -ForegroundColor Cyan

$RequirementsFile = Join-Path $PSScriptRoot "requirements.txt"

pip install -r $RequirementsFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[Studio Setup] Done. Run the Studio with:" -ForegroundColor Green
    Write-Host "  python Studio\studio.py" -ForegroundColor White
} else {
    Write-Host "[Studio Setup] pip install failed." -ForegroundColor Red
    exit 1
}
