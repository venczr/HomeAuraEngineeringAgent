$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$artifact = Join-Path $root 'reports\tmp\autonomous_codex_turn_smoke.json'
$turnA = Join-Path $root 'reports\tmp\autonomous_codex_turn_a.txt'
$turnB = Join-Path $root 'reports\tmp\autonomous_codex_turn_b.txt'

$promptA = @'
Autonomous supervisor smoke TURN A. Perform only this safe bounded development task: run Python compilation for tools/tokenwave_mcp/router.py and server.py. Write reports/tmp/codex_turn_a_checkpoint.json containing task, verified boolean, and UTC timestamp. Do not edit product code. End after checkpoint.
'@
$outputA = & codex exec --approve-for-me --skip-git-repo-check -C $root -o $turnA $promptA 2>&1
$sessionLine = $outputA | Where-Object { $_ -match '^session id:' } | Select-Object -First 1
if (-not $sessionLine) { throw 'TURN A did not return a session id.' }
$sessionId = ($sessionLine -replace '^session id:\s*','').Trim()
if (-not (Test-Path (Join-Path $root 'reports\tmp\codex_turn_a_checkpoint.json'))) { throw 'TURN A checkpoint missing.' }

$promptB = @'
Autonomous supervisor smoke TURN B. Restore from reports/tmp/codex_turn_a_checkpoint.json, then perform a different safe task: run pytest -q tests/test_tokenwave_router.py. Write reports/tmp/codex_turn_b_checkpoint.json containing restored_from, verified boolean, test result, and UTC timestamp. Do not edit product code. End after checkpoint.
'@
& codex exec resume --skip-git-repo-check -o $turnB $sessionId $promptB | Out-Null
if (-not (Test-Path (Join-Path $root 'reports\tmp\codex_turn_b_checkpoint.json'))) { throw 'TURN B checkpoint missing.' }

$result = [ordered]@{
    session_id = $sessionId
    turn_a = Get-Content (Join-Path $root 'reports\tmp\codex_turn_a_checkpoint.json') -Raw | ConvertFrom-Json
    turn_b = Get-Content (Join-Path $root 'reports\tmp\codex_turn_b_checkpoint.json') -Raw | ConvertFrom-Json
}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $artifact
$result | ConvertTo-Json -Depth 6
