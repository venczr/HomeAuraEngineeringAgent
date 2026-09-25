param([int]$MaxAttempts=0)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'start.ps1') -MaxAttempts $MaxAttempts -Ufh
