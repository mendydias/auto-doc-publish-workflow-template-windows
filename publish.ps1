<#
.SYNOPSIS
Build or manage academic Markdown publications.
.DESCRIPTION
PowerShell front end for the shared Python publisher. Paths resolve from this script, not the caller's directory.
.PARAMETER Action
Check, Build (default), Lint, Validate, Package, Test, Watch, Clean, or Handoff.
.PARAMETER Document
Document manifest name, default example.
.PARAMETER Profile
Publication profile; defaults to the selected document manifest.
.PARAMETER Typography
Typography preset: default, academic, or compact.
.PARAMETER Venue
Venue requirements identifier; defaults to the document manifest.
.PARAMETER Format
pdf (default), latex, docx, html, epub, or all.
.EXAMPLE
pwsh -NoProfile -File .\publish.ps1 -Action Build -Document example -Profile article -Typography academic -Format pdf
#>
[CmdletBinding()]
param(
    [ValidateSet('Check','Build','Lint','Validate','Package','Test','Watch','Clean','Handoff')]
    [string] $Action,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]*$')]
    [string] $Document,
    [string] $Profile,
    [string] $Typography,
    [string] $Venue,
    [ValidateSet('pdf','latex','docx','html','epub','all')]
    [string] $Format,
    [switch] $NonInteractive
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$venvPython = Join-Path $root '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $python = $venvPython }
else {
    $python = $null
    foreach ($candidate in @('python.exe','python3.exe','py.exe')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        if ($candidate -eq 'py.exe') { & $command.Source -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' 2>$null }
        else { & $command.Source -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' 2>$null }
        if ($LASTEXITCODE -eq 0) { $python = $command.Source; break }
    }
    if (-not $python) { [Console]::Error.WriteLine('Python 3.11+ not found. Create .venv or install Python; no software was installed.'); exit 2 }
    if ([IO.Path]::GetFileName($python) -ieq 'py.exe') { $pythonArgs = @('-3','-m','tools.publishing') }
    else { $pythonArgs = @('-m','tools.publishing') }
}
if (-not $pythonArgs) { $pythonArgs = @('-m','tools.publishing') }
$arguments = @($pythonArgs)
if ($PSBoundParameters.ContainsKey('Action')) { $arguments += @('--action',$Action) }
if ($PSBoundParameters.ContainsKey('Document')) { $arguments += @('--document',$Document) }
if ($PSBoundParameters.ContainsKey('Format')) { $arguments += @('--format',$Format) }
if ($PSBoundParameters.ContainsKey('Profile')) { $arguments += @('--profile',$Profile) }
if ($PSBoundParameters.ContainsKey('Typography')) { $arguments += @('--typography',$Typography) }
if ($PSBoundParameters.ContainsKey('Venue')) { $arguments += @('--venue',$Venue) }
if ($NonInteractive) { $arguments += '--non-interactive' }
Push-Location -LiteralPath $root
try {
    & $python @arguments
    $nativeExit = $LASTEXITCODE
    if ($null -eq $nativeExit) { $nativeExit = 1 }
} finally { Pop-Location }
exit $nativeExit
