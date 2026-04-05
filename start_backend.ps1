$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Starting finance backend on http://127.0.0.1:8000" -ForegroundColor Cyan
python -m app.server
