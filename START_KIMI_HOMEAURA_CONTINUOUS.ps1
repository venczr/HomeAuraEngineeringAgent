[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$kimi = 'C:\Users\zahar\AppData\Roaming\npm\kimi.cmd'
$workspace = 'C:\AI\HomeAuraEngineeringAgent'
$agentFile = 'C:\AI\HomeAuraEngineeringAgent\agent-control\HOMEAURA_AUTONOMY_BOOTSTRAP_20260729_V5\KIMI_HOMEAURA_PRIMARY_AGENT_V2.md'
$candidateRoot = 'C:\AI\HomeAuraPreauthCandidates'
$coordinationRoot = 'C:\Users\zahar\AppData\Local\HomeAuraOrchestrator\runtime\coordination'

foreach ($requiredPath in @($kimi, $workspace, $agentFile, $candidateRoot, $coordinationRoot)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required path is absent: $requiredPath"
    }
}

$priorEffort = [Environment]::GetEnvironmentVariable('KIMI_MODEL_THINKING_EFFORT', 'Process')

try {
    $env:KIMI_MODEL_THINKING_EFFORT = 'high'
    Set-Location -LiteralPath $workspace

    & $kimi `
        --auto `
        --model 'k3-256k' `
        --agent-file $agentFile `
        --add-dir $workspace `
        --add-dir $candidateRoot `
        --add-dir $coordinationRoot
}
finally {
    if ($null -eq $priorEffort) {
        Remove-Item Env:KIMI_MODEL_THINKING_EFFORT -ErrorAction SilentlyContinue
    }
    else {
        $env:KIMI_MODEL_THINKING_EFFORT = $priorEffort
    }
}
