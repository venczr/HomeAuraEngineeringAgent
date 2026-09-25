$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$env:KIMI_LOOP_MAX_STEPS_PER_TURN = '32'
$env:KIMI_LOOP_MAX_RETRIES_PER_STEP = '2'
$env:KIMI_CODE_BACKGROUND_MAX_RUNNING_TASKS = '1'
$env:KIMI_CODE_AGENT_SWARM_MAX_CONCURRENCY = '1'
$env:KIMI_CODE_BACKGROUND_KEEP_ALIVE_ON_EXIT = '0'
$env:KIMI_MODEL_MAX_COMPLETION_TOKENS = '32768'

$workRoot = 'C:\AI\HomeAuraEngineeringAgent'
$resumePrompt = Join-Path $workRoot 'KIMI_REV009_RESUME_20260730T2311.txt'
$quotaPolicy = Join-Path $workRoot 'KIMI_QUOTA_EFFICIENCY_POLICY_V1.txt'

if (-not (Test-Path -LiteralPath $resumePrompt -PathType Leaf)) {
    throw "Missing resume prompt: $resumePrompt"
}
if (-not (Test-Path -LiteralPath $quotaPolicy -PathType Leaf)) {
    throw "Missing quota policy: $quotaPolicy"
}

$kimiCommand = Get-Command 'kimi' -ErrorAction Stop
Set-Location -LiteralPath $workRoot

Write-Host 'Starting a NEW Kimi session. Do not use --continue.'
Write-Host 'Select/verify model kimi-code/k3-256k with HIGH effort in /model.'
Write-Host 'Run /usage before sending the resume instruction.'
Write-Host "Then send: Read $quotaPolicy and $resumePrompt completely, then execute the resume prompt under the quota policy."

& $kimiCommand.Source --afk
