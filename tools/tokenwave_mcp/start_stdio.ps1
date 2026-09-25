$ErrorActionPreference = 'Stop'

# Codex sanitizes the environment inherited by stdio MCP children. Read only
# the named per-user credential; never enumerate or print the environment.
if (-not $env:OPENAI_API_KEY) {
    $env:OPENAI_API_KEY = [Environment]::GetEnvironmentVariable(
        'OPENAI_API_KEY',
        [EnvironmentVariableTarget]::User
    )
}
if (-not $env:OPENAI_API_KEY) {
    throw 'TokenWave credential is unavailable to the MCP process.'
}

$repositoryRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $repositoryRoot
python -m tools.tokenwave_mcp.server
