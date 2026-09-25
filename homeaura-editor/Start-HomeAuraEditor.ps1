$ErrorActionPreference = "Stop"

$editorRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $editorRoot
$runtimeRoot = Join-Path $editorRoot ".runtime"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

if (-not (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "agent.api:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $runtimeRoot "api.stdout.log") `
        -RedirectStandardError (Join-Path $runtimeRoot "api.stderr.log")
}

if (-not (Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev") `
        -WorkingDirectory $editorRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $runtimeRoot "editor.stdout.log") `
        -RedirectStandardError (Join-Path $runtimeRoot "editor.stderr.log")
}

$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 250
    $apiReady = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
    $editorReady = Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue
} until (($apiReady -and $editorReady) -or (Get-Date) -ge $deadline)

if (-not ($apiReady -and $editorReady)) {
    throw "HomeAura Editor не запустился за 30 секунд. Проверьте журналы в $runtimeRoot."
}

Start-Process "http://127.0.0.1:3000"
