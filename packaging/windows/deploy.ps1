# Build and install Sticky Notes to C:\Program Files\StickyNotes (Windows one-stop deploy).
#   .\packaging\windows\deploy.ps1
#   .\packaging\windows\deploy.ps1 -BuildOnly
#   .\packaging\windows\deploy.ps1 -InstallOnly
param(
    [switch]$BuildOnly,
    [switch]$InstallOnly,
    [switch]$Elevated
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$InstallDir = Join-Path ${env:ProgramFiles} "StickyNotes"
$ExeName = "StickyNotes.exe"
$BuiltExe = Join-Path $Root "dist\$ExeName"
$InstalledExe = Join-Path $InstallDir $ExeName

function Show-Usage {
    @"
Usage: .\packaging\windows\deploy.ps1 [options]

Build Sticky Notes and install to C:\Program Files\StickyNotes\StickyNotes.exe

Options:
  -BuildOnly     Build dist\StickyNotes.exe only (no install)
  -InstallOnly   Install existing build (no rebuild; may prompt for admin)
  -Elevated      Internal flag used when re-launching with admin rights
"@
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Stop-StickyNotes {
    $proc = Get-Process -Name "StickyNotes" -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Stopping running Sticky Notes..."
        $proc | Stop-Process -Force
        Start-Sleep -Seconds 1
    }
}

function Install-StickyNotes {
    if (-not (Test-Path $BuiltExe)) {
        Write-Error "Build not found at $BuiltExe. Run: .\packaging\windows\deploy.ps1 -BuildOnly"
    }

    if (-not (Test-IsAdmin)) {
        Write-Host "Administrator approval required to install to Program Files..."
        $argList = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$PSCommandPath`"",
            "-InstallOnly",
            "-Elevated"
        )
        $proc = Start-Process powershell -Verb RunAs -ArgumentList $argList -Wait -PassThru
        if ($proc.ExitCode -ne 0) {
            exit $proc.ExitCode
        }
        return
    }

    Stop-StickyNotes

    Write-Host "Installing to $InstalledExe ..."
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Copy-Item -Path $BuiltExe -Destination $InstalledExe -Force

    Write-Host ""
    Write-Host "Deployed: $InstalledExe"
    Write-Host "Launch: Start-Process `"$InstalledExe`""
}

if ($BuildOnly -and $InstallOnly) {
    Write-Error "Use either -BuildOnly or -InstallOnly, not both."
}

if (-not $InstallOnly) {
    & (Join-Path $PSScriptRoot "build.ps1")
}

if (-not $BuildOnly) {
    Install-StickyNotes
}
