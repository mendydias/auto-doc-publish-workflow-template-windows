<#
.SYNOPSIS
Bootstrap the Windows publishing toolchain with WinGet.
.NOTES
Compatible with Windows PowerShell 5.1. This script never changes execution
policy and never elevates itself.
#>
[CmdletBinding()]
param(
    [switch] $NonInteractive,
    [switch] $AcceptAgreements
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$diagnostics = Join-Path $root 'build/setup'
New-Item -ItemType Directory -Force -Path $diagnostics | Out-Null
$log = Join-Path $diagnostics ('setup-{0}.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
Start-Transcript -Path $log -Force | Out-Null
try {
    $ci = ($env:CI -match '^(1|true|yes)$')
    $unattended = $NonInteractive -or $ci -or ($env:SETUP_NON_INTERACTIVE -match '^(1|true|yes)$')
    $agreementsAccepted = $AcceptAgreements -or ($env:SETUP_ACCEPT_AGREEMENTS -match '^(1|true|yes)$')
    if ($env:OS -ne 'Windows_NT') { throw 'setup.ps1 supports Windows only.' }
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'A 64-bit Windows installation is required.' }
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'WinGet was not found. Install or update App Installer from Microsoft Store, then rerun setup.ps1.' }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $admin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    Write-Host "WinGet: $($winget.Source)"
    Write-Host "Administrator: $admin"
    if ($unattended -and -not $agreementsAccepted) {
        throw 'Unattended setup requires -AcceptAgreements (or SETUP_ACCEPT_AGREEMENTS=1). No packages were installed.'
    }
    if ($unattended -and $admin) {
        throw 'Run unattended setup as a standard user; this script will not install machine-wide packages or elevate.'
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) {
        $arguments = @('install','--id','Python.Python.3.12','--exact','--scope','user','--silent')
        if ($agreementsAccepted) { $arguments += @('--accept-package-agreements','--accept-source-agreements') }
        if ($unattended) { $arguments += '--disable-interactivity' }
        & $winget.Source @arguments
        if ($LASTEXITCODE -ne 0) { throw "WinGet failed to install Python (exit $LASTEXITCODE). See $log" }
    } else {
        Write-Host "Reusing Python at $($python.Source)"
    }
    Write-Host "Bootstrap completed. Diagnostics: $log"
} catch {
    [Console]::Error.WriteLine("SETUP FAILED: $($_.Exception.Message)")
    [Console]::Error.WriteLine("Diagnostics: $log")
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
