[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$resolver = Join-Path $root 'Resolve-HomeAuraModelRoute.ps1'
$quota = Join-Path $root 'tests\quota-green.json'
$failures = [System.Collections.Generic.List[string]]::new()
$passed = 0

function Merge-RouteParameters {
    param(
        [hashtable] $Base,
        [hashtable] $Override
    )

    $merged = @{}
    foreach ($key in $Base.Keys) {
        $merged[$key] = $Base[$key]
    }
    foreach ($key in $Override.Keys) {
        $merged[$key] = $Override[$key]
    }
    return $merged
}

function Assert-Route {
    param(
        [string] $Name,
        [hashtable] $Parameters,
        [hashtable] $Expected
    )

    $route = & $resolver @Parameters -OutputFormat Object
    foreach ($key in $Expected.Keys) {
        if ($route.$key -ne $Expected[$key]) {
            $script:failures.Add("$Name expected $key=$($Expected[$key]) but got $($route.$key)")
            return
        }
    }
    $script:passed++
}

$base = @{
    QuotaStatePath = $quota
    ContextPercent = 0
    ActiveWriter = 'none'
    NoVideo = $true
    ContextPruned = $true
    EstimatedInputTokens = 40000
    ExpectedOutputTokens = 12000
    EstimatedAtomicCostPercent = 10
}

Assert-Route 'local-no-model' (Merge-RouteParameters $base @{
    TaskClass = 'local_deterministic'
}) @{
    launch_allowed = $true
    agent = 'local'
    model = 'none'
}

Assert-Route 'kimi-routine-low' (Merge-RouteParameters $base @{
    TaskClass = 'routine_code'
    PreferredAgent = 'auto'
}) @{
    launch_allowed = $true
    agent = 'kimi'
    model = 'k3-256k'
    effort = 'low'
}

Assert-Route 'kimi-security-high' (Merge-RouteParameters $base @{
    TaskClass = 'security_critical'
    PreferredAgent = 'kimi'
}) @{
    launch_allowed = $true
    agent = 'kimi'
    model = 'k3-256k'
    effort = 'high'
}

Assert-Route 'kimi-1m-measured' (Merge-RouteParameters $base @{
    TaskClass = 'complex_code'
    PreferredAgent = 'kimi'
    EstimatedInputTokens = 230000
    ExpectedOutputTokens = 20000
    KimiOneMillionEntitled = $true
}) @{
    launch_allowed = $true
    agent = 'kimi'
    model = 'k3'
    effort = 'high'
}

Assert-Route 'codex-mechanical-luna' (Merge-RouteParameters $base @{
    TaskClass = 'mechanical'
    PreferredAgent = 'codex'
}) @{
    launch_allowed = $true
    agent = 'codex'
    model = 'gpt-5.6-luna'
    effort = 'low'
}

Assert-Route 'codex-complex-terra' (Merge-RouteParameters $base @{
    TaskClass = 'complex_code'
    PreferredAgent = 'codex'
}) @{
    launch_allowed = $true
    agent = 'codex'
    model = 'gpt-5.6-terra'
    effort = 'high'
}

Assert-Route 'codex-security-sol' (Merge-RouteParameters $base @{
    TaskClass = 'security_critical'
    PreferredAgent = 'codex'
}) @{
    launch_allowed = $true
    agent = 'codex'
    model = 'gpt-5.6-sol'
    effort = 'high'
}

Assert-Route 'claude-review-opus' (Merge-RouteParameters $base @{
    TaskClass = 'independent_review'
    PreferredAgent = 'claude'
    FrozenBytes = $true
    ReviewRisk = 'stage_gate'
}) @{
    launch_allowed = $true
    agent = 'claude'
    model = 'opus'
    effort = 'high'
}

Assert-Route 'claude-review-requires-freeze' (Merge-RouteParameters $base @{
    TaskClass = 'independent_review'
    PreferredAgent = 'claude'
    FrozenBytes = $false
    ReviewRisk = 'ordinary'
}) @{
    launch_allowed = $false
    disposition = 'REVIEW_BLOCKED'
}

Assert-Route 'writer-lease-conflict' (Merge-RouteParameters $base @{
    TaskClass = 'routine_code'
    PreferredAgent = 'codex'
    ActiveWriter = 'kimi'
}) @{
    launch_allowed = $false
    disposition = 'WRITER_LEASE_CONFLICT'
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

[pscustomobject][ordered]@{
    schema = 'homeaura.model-router-test-receipt.v1'
    passed = $passed
    failed = 0
    provider_requests = 0
    credential_reads = 0
} | ConvertTo-Json
