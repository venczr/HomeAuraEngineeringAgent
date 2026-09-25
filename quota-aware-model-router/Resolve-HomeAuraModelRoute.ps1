[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet(
        'local_deterministic',
        'mechanical',
        'routine_code',
        'complex_code',
        'security_critical',
        'independent_review',
        'owner_gate'
    )]
    [string] $TaskClass,

    [ValidateSet('auto', 'codex', 'kimi', 'claude')]
    [string] $PreferredAgent = 'auto',

    [Parameter(Mandatory)]
    [string] $QuotaStatePath,

    [ValidateRange(0, 100)]
    [int] $ContextPercent = 0,

    [ValidateRange(0, 1048576)]
    [int] $EstimatedInputTokens = 0,

    [ValidateRange(0, 131072)]
    [int] $ExpectedOutputTokens = 8000,

    [ValidateRange(0, 100)]
    [double] $EstimatedAtomicCostPercent = 10,

    [ValidateSet('none', 'codex', 'kimi')]
    [string] $ActiveWriter = 'none',

    [switch] $WriterLeaseReleased,
    [switch] $NoVideo,
    [switch] $ContextPruned,
    [switch] $KimiOneMillionEntitled,
    [switch] $FrozenBytes,

    [ValidateSet('mechanical', 'ordinary', 'security', 'stage_gate')]
    [string] $ReviewRisk = 'ordinary',

    [ValidateSet('Json', 'Object')]
    [string] $OutputFormat = 'Json'
)

$ErrorActionPreference = 'Stop'

function New-RouteResult {
    param(
        [bool] $Allowed,
        [string] $Disposition,
        [string] $Agent,
        [string] $Model,
        [string] $Effort,
        [string] $QuotaBand,
        [bool] $RequiresCheckpoint,
        [bool] $RequiresNewSession,
        [string[]] $Reasons
    )

    [pscustomobject][ordered]@{
        schema               = 'homeaura.model-route-decision.v1'
        task_class           = $TaskClass
        launch_allowed       = $Allowed
        disposition          = $Disposition
        agent                = $Agent
        model                = $Model
        effort               = $Effort
        quota_band           = $QuotaBand
        context_percent      = $ContextPercent
        requires_checkpoint  = $RequiresCheckpoint
        requires_new_session = $RequiresNewSession
        active_writer        = $ActiveWriter
        writer_lease_released = [bool]$WriterLeaseReleased
        estimated_input_tokens = $EstimatedInputTokens
        expected_output_tokens = $ExpectedOutputTokens
        estimated_atomic_cost_percent = $EstimatedAtomicCostPercent
        reasons              = @($Reasons)
        prohibited_defaults  = @(
            'mid_session_model_switch',
            'automatic_provider_retry',
            'paid_fallback',
            'simultaneous_writers',
            'self_acceptance',
            'kimi_highspeed',
            'codex_ultra',
            'claude_fable_max_ultracode'
        )
    }
}

function Get-QuotaBand {
    param(
        [object] $ProviderState,
        [double] $AtomicCostPercent
    )

    if ($null -eq $ProviderState) {
        return 'RED'
    }

    if ([bool]$ProviderState.limit_signal) {
        return 'RED'
    }

    $remaining = $ProviderState.effective_remaining_percent
    if ($null -eq $remaining) {
        return 'RED'
    }

    $value = [double]$remaining
    if ($value -lt 15 -or $value -lt $AtomicCostPercent) {
        return 'RED'
    }
    if ($value -lt 30 -or $value -lt (2 * $AtomicCostPercent)) {
        return 'AMBER'
    }
    return 'GREEN'
}

function Select-Writer {
    param(
        [string] $Preferred,
        [string] $CodexBand,
        [string] $KimiBand
    )

    $order = if ($Preferred -eq 'codex') {
        @('codex', 'kimi')
    } elseif ($Preferred -eq 'kimi' -or $Preferred -eq 'auto') {
        @('kimi', 'codex')
    } else {
        @()
    }

    foreach ($candidate in $order) {
        $band = if ($candidate -eq 'codex') { $CodexBand } else { $KimiBand }
        if ($band -eq 'GREEN') {
            return $candidate
        }
    }
    return ''
}

$resolvedQuotaPath = (Resolve-Path -LiteralPath $QuotaStatePath).Path
$quota = Get-Content -LiteralPath $resolvedQuotaPath -Raw | ConvertFrom-Json
if ($quota.schema -ne 'homeaura.quota-state.v1') {
    throw "Unsupported quota state schema: $($quota.schema)"
}

$observed = [DateTimeOffset]::Parse($quota.observed_at_local)
$staleMinutes = [int]$quota.stale_after_minutes
$isStale = ([DateTimeOffset]::Now - $observed).TotalMinutes -gt $staleMinutes

$codexBand = if ($isStale) { 'RED' } else { Get-QuotaBand $quota.providers.codex $EstimatedAtomicCostPercent }
$kimiBand = if ($isStale) { 'RED' } else { Get-QuotaBand $quota.providers.kimi $EstimatedAtomicCostPercent }
$claudeBand = if ($isStale) { 'RED' } else { Get-QuotaBand $quota.providers.claude $EstimatedAtomicCostPercent }

if ($TaskClass -in @('local_deterministic', 'owner_gate')) {
    $result = New-RouteResult `
        -Allowed $true `
        -Disposition 'LOCAL_ONLY_NO_MODEL' `
        -Agent 'local' `
        -Model 'none' `
        -Effort 'not_applicable' `
        -QuotaBand 'NOT_APPLICABLE' `
        -RequiresCheckpoint $false `
        -RequiresNewSession $false `
        -Reasons @('Known deterministic work does not require model quota.')
} elseif ($TaskClass -eq 'independent_review') {
    $reasons = [System.Collections.Generic.List[string]]::new()
    if (-not $FrozenBytes) {
        $reasons.Add('Independent review requires frozen exact bytes.')
    }
    if ($ActiveWriter -ne 'none') {
        $reasons.Add('Independent review requires no active writer.')
    }
    if ($claudeBand -ne 'GREEN') {
        $reasons.Add("Claude quota is $claudeBand; review requires GREEN capacity.")
    }
    $claudeRemaining = [double]$quota.providers.claude.effective_remaining_percent
    $reviewReserveRequired = (2 * $EstimatedAtomicCostPercent) + 20
    if ($claudeRemaining -lt $reviewReserveRequired) {
        $reasons.Add("Claude review requires $reviewReserveRequired% estimated capacity including a second pass and 20% reserve; reported remaining is $claudeRemaining%.")
    }

    $model = switch ($ReviewRisk) {
        'mechanical' { 'haiku' }
        'ordinary'   { 'sonnet' }
        'security'   { 'opus' }
        'stage_gate' { 'opus' }
    }
    $effort = if ($model -eq 'haiku') { 'not_applicable' } else { 'high' }
    $allowed = $reasons.Count -eq 0
    $result = New-RouteResult `
        -Allowed $allowed `
        -Disposition $(if ($allowed) { 'START_FRESH_READ_ONLY_REVIEW' } else { 'REVIEW_BLOCKED' }) `
        -Agent 'claude' `
        -Model $model `
        -Effort $effort `
        -QuotaBand $claudeBand `
        -RequiresCheckpoint $false `
        -RequiresNewSession $true `
        -Reasons $reasons.ToArray()
} else {
    if ($PreferredAgent -eq 'claude') {
        $result = New-RouteResult `
            -Allowed $false `
            -Disposition 'ROLE_CONFLICT' `
            -Agent 'none' `
            -Model 'none' `
            -Effort 'not_applicable' `
            -QuotaBand 'RED' `
            -RequiresCheckpoint $true `
            -RequiresNewSession $false `
            -Reasons @('Claude is reviewer-only and cannot be selected as writer.')
    } else {
        $writer = Select-Writer -Preferred $PreferredAgent -CodexBand $codexBand -KimiBand $kimiBand
        if ([string]::IsNullOrWhiteSpace($writer)) {
            $result = New-RouteResult `
                -Allowed $false `
                -Disposition 'BLOCKED_CAPACITY' `
                -Agent 'none' `
                -Model 'none' `
                -Effort 'not_applicable' `
                -QuotaBand 'RED' `
                -RequiresCheckpoint $true `
                -RequiresNewSession $false `
                -Reasons @("No writer has GREEN quota. Codex=$codexBand; Kimi=$kimiBand.")
        } elseif ($ActiveWriter -ne 'none' -and $ActiveWriter -ne $writer -and -not $WriterLeaseReleased) {
            $result = New-RouteResult `
                -Allowed $false `
                -Disposition 'WRITER_LEASE_CONFLICT' `
                -Agent $writer `
                -Model 'unresolved' `
                -Effort 'unresolved' `
                -QuotaBand $(if ($writer -eq 'codex') { $codexBand } else { $kimiBand }) `
                -RequiresCheckpoint $true `
                -RequiresNewSession $false `
                -Reasons @("Active writer is $ActiveWriter; its lease must be checkpointed and released before routing to $writer.")
        } else {
            $model = ''
            $effort = ''
            $reasons = [System.Collections.Generic.List[string]]::new()
            $allowed = $true

            if ($writer -eq 'codex') {
                switch ($TaskClass) {
                    'mechanical'        { $model = 'gpt-5.6-luna';  $effort = 'low' }
                    'routine_code'      { $model = 'gpt-5.6-terra'; $effort = 'medium' }
                    'complex_code'      { $model = 'gpt-5.6-terra'; $effort = 'high' }
                    'security_critical' { $model = 'gpt-5.6-sol';   $effort = 'high' }
                }
                $contextCheckpoint = $ContextPercent -ge 50
                $newSession = $true
                if ($ContextPercent -ge 75) {
                    $reasons.Add('Old Codex session is at or above the hard context boundary; use only the verified checkpoint.')
                }
            } else {
                $effort = if ($TaskClass -in @('complex_code', 'security_critical')) { 'high' } else { 'low' }
                $conservativeTotal = $EstimatedInputTokens + $ExpectedOutputTokens + 16000
                $fits256k = (
                    $NoVideo -and
                    $EstimatedInputTokens -le 200000 -and
                    (262144 - $EstimatedInputTokens) -ge 40000 -and
                    $conservativeTotal -le 262144
                )

                if ($fits256k) {
                    $model = 'k3-256k'
                } elseif (
                    $KimiOneMillionEntitled -and
                    $NoVideo -and
                    $ContextPruned -and
                    ($EstimatedInputTokens + $ExpectedOutputTokens + 40000) -le 1000000
                ) {
                    $model = 'k3'
                    $reasons.Add('Selected 1M only because the measured pruned task does not conservatively fit k3-256k.')
                } else {
                    $allowed = $false
                    $model = 'none'
                    $reasons.Add('Task does not conservatively fit k3-256k and lacks all prerequisites for k3 1M; split or prune scope.')
                }

                $contextCheckpoint = $ContextPercent -ge 25
                $newSession = $true
                if ($ContextPercent -ge 35) {
                    $reasons.Add('Do not resume the old Kimi session; start from a selective checkpoint.')
                }
            }

            $result = New-RouteResult `
                -Allowed $allowed `
                -Disposition $(if ($allowed) { 'START_FRESH_WRITER_SESSION' } else { 'SCOPE_SPLIT_REQUIRED' }) `
                -Agent $writer `
                -Model $model `
                -Effort $effort `
                -QuotaBand $(if ($writer -eq 'codex') { $codexBand } else { $kimiBand }) `
                -RequiresCheckpoint $contextCheckpoint `
                -RequiresNewSession $newSession `
                -Reasons $reasons.ToArray()
        }
    }
}

if ($isStale) {
    $result.reasons = @($result.reasons) + 'Quota telemetry is stale; refresh 06_QUOTA_STATE_CURRENT.json.'
}

if ($OutputFormat -eq 'Object') {
    return $result
}

$result | ConvertTo-Json -Depth 8
