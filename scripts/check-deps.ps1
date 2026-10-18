[CmdletBinding()]
param([ValidateSet('pdf','latex','docx','html','epub','all')][string] $Format = 'pdf')
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root 'publish.ps1') -Action Check -Format $Format
exit $LASTEXITCODE
