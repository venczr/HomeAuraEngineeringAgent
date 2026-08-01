$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PreviousLocation = Get-Location
$PreviousPythonUtf8 = $env:PYTHONUTF8
$PreviousOutputEncoding = [Console]::OutputEncoding

try {
    Set-Location $Root

    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    $env:PYTHONUTF8 = "1"

    Write-Host ""
    Write-Host "HomeAura Engineering Agent API"
    Write-Host "Адрес: http://127.0.0.1:8765"
    Write-Host "Документация: http://127.0.0.1:8765/docs"
    Write-Host ""

    & ".\.venv\Scripts\python.exe" `
        -m uvicorn `
        agent.api:app `
        --host 127.0.0.1 `
        --port 8765 `
        --reload
}
finally {
    [Console]::OutputEncoding = $PreviousOutputEncoding
    $env:PYTHONUTF8 = $PreviousPythonUtf8
    Set-Location $PreviousLocation
}
