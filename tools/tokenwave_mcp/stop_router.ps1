$ErrorActionPreference = 'Stop'
$pidPath = Join-Path $PSScriptRoot 'router.pid'
if (-not (Test-Path -LiteralPath $pidPath)) { exit 0 }
$routerPid = Get-Content -LiteralPath $pidPath -Raw
if ($routerPid -match '^\d+$') {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$routerPid" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -match 'tools\.tokenwave_mcp\.server') {
        Stop-Process -Id ([int]$routerPid)
    }
}
Remove-Item -LiteralPath $pidPath -Force
