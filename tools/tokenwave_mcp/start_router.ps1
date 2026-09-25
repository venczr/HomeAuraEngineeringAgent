$ErrorActionPreference = 'Stop'
if (-not $env:OPENAI_API_KEY) { throw 'TokenWave credential environment is unavailable.' }
$pidPath = Join-Path $PSScriptRoot 'router.pid'
$existing = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $owner = Get-Process -Id $existing.OwningProcess -ErrorAction SilentlyContinue
    if ($owner) { Set-Content -LiteralPath $pidPath -Value $owner.Id -NoNewline }
    exit 0
}
$previous = $env:HOMEAURA_TOKENWAVE_MCP_HTTP
$env:HOMEAURA_TOKENWAVE_MCP_HTTP = '1'
try {
    $process = Start-Process -FilePath 'python' -ArgumentList @('-m','tools.tokenwave_mcp.server') -WorkingDirectory (Resolve-Path (Join-Path $PSScriptRoot '..\..')) -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath $pidPath -Value $process.Id -NoNewline
} finally {
    $env:HOMEAURA_TOKENWAVE_MCP_HTTP = $previous
}
for ($i=0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 200
    if (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) { exit 0 }
}
throw 'HomeAura TokenWave MCP did not start within 6 seconds.'
