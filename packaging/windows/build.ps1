# Build StickyNotes.exe (Windows). Run from repo root:
#   .\packaging\windows\build.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    python -m venv $Venv
}

& $VenvPython -m pip install --upgrade pip -q
& $VenvPython -m pip install -r requirements-windows.txt -q

if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }

& $VenvPython -m PyInstaller packaging/windows/sticky_notes.spec

Write-Host "Built: $Root\dist\StickyNotes.exe"
