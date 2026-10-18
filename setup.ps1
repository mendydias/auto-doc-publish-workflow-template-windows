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

    $packages = @(
        @{ Id = 'Python.Python.3.12'; Command = 'python.exe' },
        @{ Id = 'Microsoft.PowerShell'; Command = 'pwsh.exe' },
        @{ Id = 'JohnMacFarlane.Pandoc'; Command = 'pandoc.exe' },
        @{ Id = 'MiKTeX.MiKTeX'; Command = 'lualatex.exe' },
        @{ Id = 'StrawberryPerl.StrawberryPerl'; Command = 'perl.exe' }
    )
    foreach ($package in $packages) {
        $existing = Get-Command $package.Command -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "Reusing $($package.Id): $($existing.Source)"
            continue
        }
        $arguments = @('install','--id',$package.Id,'--exact','--scope','user','--silent')
        if ($agreementsAccepted) { $arguments += @('--accept-package-agreements','--accept-source-agreements') }
        if ($unattended) { $arguments += '--disable-interactivity' }
        & $winget.Source @arguments
        if ($LASTEXITCODE -ne 0) { throw "WinGet failed to install $($package.Id) (exit $LASTEXITCODE). See $log" }
    }

    $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:ProgramFiles\MiKTeX\miktex\bin\x64;$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64;$env:LOCALAPPDATA\Programs\PowerShell\7;$env:Path"
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) { throw 'Python installation completed but python.exe is not discoverable; restart the terminal and rerun setup.' }
    $venv = Join-Path $root '.venv'
    $venvPython = Join-Path $venv 'Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $python.Source -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create project virtual environment (exit $LASTEXITCODE)." }
    }
    & $venvPython -m pip install --disable-pip-version-check -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw "Pinned Python dependencies could not be installed (exit $LASTEXITCODE)." }
    Write-Host "Toolchain provisioning completed. Diagnostics: $log"
} catch {
    [Console]::Error.WriteLine("SETUP FAILED: $($_.Exception.Message)")
    [Console]::Error.WriteLine("Diagnostics: $log")
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
