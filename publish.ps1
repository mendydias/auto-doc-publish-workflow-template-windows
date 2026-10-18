<#
.SYNOPSIS
Build or manage academic Markdown publications.
.DESCRIPTION
PowerShell front end for the shared Python publisher. Paths resolve from this script, not the caller's directory.
.PARAMETER Action
Check, Build (default), Lint, Test, Watch, Clean, or Handoff.
.PARAMETER Document
Document manifest name, default example.
.PARAMETER Profile
Structural profile: article, report, or thesis.
.PARAMETER Typography
Typography preset: default, academic, or compact.
.PARAMETER Format
pdf (default), latex, docx, html, epub, or all.
.EXAMPLE
pwsh -NoProfile -File .\publish.ps1 -Action Build -Document example -Profile article -Typography academic -Format pdf
#>
[CmdletBinding()]
param(
    [ValidateSet('Check','Build','Lint','Test','Watch','Clean','Handoff')]
    [string] $Action = 'Build',
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]*$')]
    [string] $Document = 'example',
    [ValidateSet('article','report','thesis')]
    [string] $Profile = 'article',
    [ValidateSet('default','academic','compact')]
    [string] $Typography = 'default',
    [ValidateSet('pdf','latex','docx','html','epub','all')]
    [string] $Format = 'pdf'
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$venvPython = Join-Path $root '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $python = $venvPython }
else {
    $python = $null
    foreach ($candidate in @('python.exe','python3.exe','py.exe')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) { $python = $command.Source; break }
    }
    if (-not $python) { [Console]::Error.WriteLine('Python 3.11+ not found. Create .venv or install Python; no software was installed.'); exit 2 }
    if ([IO.Path]::GetFileName($python) -ieq 'py.exe') { $pythonArgs = @('-3','-m','tools.publishing') }
    else { $pythonArgs = @('-m','tools.publishing') }
}
if (-not $pythonArgs) { $pythonArgs = @('-m','tools.publishing') }
$arguments = @($pythonArgs) + @('--action',$Action,'--document',$Document,'--profile',$Profile,'--typography',$Typography,'--format',$Format)
Push-Location -LiteralPath $root
try {
    & $python @arguments
    $nativeExit = $LASTEXITCODE
    if ($null -eq $nativeExit) { $nativeExit = 1 }
} finally { Pop-Location }
exit $nativeExit
