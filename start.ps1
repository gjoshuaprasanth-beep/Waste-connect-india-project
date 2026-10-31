# WasteConnect India - Application Launcher
$nodePath = "C:\Users\PRASANTH\.gemini\antigravity\scratch\node-v20.18.0-win-x64"
if (Test-Path "$nodePath\node.exe") {
    $env:PATH = "$nodePath;" + $env:PATH
}

$env:PORT = "5000"
$env:RUN_SERVER = "true"

Write-Host "===============================================================" -ForegroundColor Green
Write-Host " WasteConnect India - B2B Healthcare & Industrial Waste Platform" -ForegroundColor Green
Write-Host " Bio-Medical Waste (2016) & Hazardous Waste Rules (2016)" -ForegroundColor Green
Write-Host " URL: http://localhost:5000" -ForegroundColor Cyan
Write-Host " Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host "===============================================================" -ForegroundColor Green

node server/index.js
