<#
.SYNOPSIS
Generate a Windows-agent continuation and acceptance report.
.DESCRIPTION
Writes ignored Markdown and JSON reports beneath build/handoff. Does not install tools, run acceptance, or clean output.
#>
[CmdletBinding()]
param()
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root 'publish.ps1') -Action Handoff
exit $LASTEXITCODE
