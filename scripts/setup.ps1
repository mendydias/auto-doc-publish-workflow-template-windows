<# Creates only a project-local virtual environment and installs pinned project dependencies. #>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py.exe -ErrorAction SilentlyContinue }
if (-not $python) { throw 'Python 3.11+ not found. Install Python independently; this script does not install system software.' }
$venv = Join-Path $root '.venv'
if (-not (Test-Path -LiteralPath $venv)) {
    if ($python.Name -ieq 'py.exe') { & $python.Source -3 -m venv $venv }
    else { & $python.Source -m venv $venv }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$venvPython = Join-Path $venv 'Scripts/python.exe'
& $venvPython -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
