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

    [Parameter(Mandatory)]
    [string] $TaskPromptFile,

    [string] $Workspace = 'C:\AI\HomeAuraEngineeringAgent',

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

    [switch] $Launch
)

$ErrorActionPreference = 'Stop'
$routerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$resolver = Join-Path $routerRoot 'Resolve-HomeAuraModelRoute.ps1'
$commonPolicy = Join-Path $routerRoot '00_COMMON_ROUTING_POLICY.md'
$agentPromptMap = @{
    codex  = Join-Path $routerRoot '02_CODEX_ROUTER_PROMPT.md'
    kimi   = Join-Path $routerRoot '03_KIMI_ROUTER_PROMPT.md'
    claude = Join-Path $routerRoot '04_CLAUDE_ROUTER_PROMPT.md'
}

$resolvedTaskPrompt = (Resolve-Path -LiteralPath $TaskPromptFile).Path
$resolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
$resolvedQuota = (Resolve-Path -LiteralPath $QuotaStatePath).Path

$routeParams = @{
    TaskClass              = $TaskClass
    PreferredAgent         = $PreferredAgent
    QuotaStatePath         = $resolvedQuota
    ContextPercent         = $ContextPercent
    EstimatedInputTokens   = $EstimatedInputTokens
    ExpectedOutputTokens   = $ExpectedOutputTokens
    EstimatedAtomicCostPercent = $EstimatedAtomicCostPercent
    ActiveWriter           = $ActiveWriter
    ReviewRisk             = $ReviewRisk
    OutputFormat           = 'Object'
    WriterLeaseReleased    = $WriterLeaseReleased
    NoVideo                = $NoVideo
    ContextPruned          = $ContextPruned
    KimiOneMillionEntitled = $KimiOneMillionEntitled
    FrozenBytes            = $FrozenBytes
}

$route = & $resolver @routeParams
$agentPrompt = if ($route.agent -eq 'local') { $commonPolicy } else { $agentPromptMap[$route.agent] }
$bootstrap = @"
Read these files completely in order:
1. $commonPolicy
2. $agentPrompt
3. $resolvedTaskPrompt

Use this fixed route for exactly one atomic task:
agent=$($route.agent)
model=$($route.model)
effort=$($route.effort)
task_class=$($route.task_class)

Do not resume historical sessions. Continue only within the authority of the task prompt and stop at its next genuine gate.
"@

$plan = [pscustomobject][ordered]@{
    schema = 'homeaura.routed-session-launch-plan.v1'
    route = $route
    workspace = $resolvedWorkspace
    task_prompt_file = $resolvedTaskPrompt
    bootstrap = $bootstrap
    launch_requested = [bool]$Launch
    visible_powershell = $true
}

if (-not $route.launch_allowed) {
    $plan | ConvertTo-Json -Depth 10
    if ($Launch) {
        throw "Route is not launchable: $($route.disposition)"
    }
    return
}

if ($route.agent -eq 'local') {
    $plan | ConvertTo-Json -Depth 10
    return
}

function Quote-PowerShellLiteral {
    param([string] $Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Resolve-CmdPath {
    param([string] $Name)
    $command = Get-Command "$Name.cmd" -ErrorAction Stop | Select-Object -First 1
    return $command.Path
}

$cliPath = Resolve-CmdPath $route.agent
$commandParts = [System.Collections.Generic.List[string]]::new()

if ($route.agent -eq 'codex') {
    $invoke = @(
        '& ' + (Quote-PowerShellLiteral $cliPath)
        '-C ' + (Quote-PowerShellLiteral $resolvedWorkspace)
        '-m ' + (Quote-PowerShellLiteral $route.model)
        '-c ' + (Quote-PowerShellLiteral ('model_reasoning_effort="' + $route.effort + '"'))
        (Quote-PowerShellLiteral $bootstrap)
    ) -join ' '
    $commandParts.Add($invoke)
} elseif ($route.agent -eq 'kimi') {
    $commandParts.Add('$env:KIMI_MODEL_THINKING_EFFORT = ' + (Quote-PowerShellLiteral $route.effort))
    $commandParts.Add('Set-Clipboard -Value ' + (Quote-PowerShellLiteral $bootstrap))
    $commandParts.Add("Write-Host 'HomeAura bootstrap copied to clipboard. Paste it into Kimi once with Ctrl+V, then press Enter.' -ForegroundColor Cyan")
    $commandParts.Add(
        'try { & ' + (Quote-PowerShellLiteral $cliPath) +
        ' --auto --model ' + (Quote-PowerShellLiteral $route.model) +
        ' } finally { Remove-Item Env:KIMI_MODEL_THINKING_EFFORT -ErrorAction SilentlyContinue }'
    )
} elseif ($route.agent -eq 'claude') {
    $invokeParts = [System.Collections.Generic.List[string]]::new()
    $invokeParts.Add('& ' + (Quote-PowerShellLiteral $cliPath))
    $invokeParts.Add('--model ' + (Quote-PowerShellLiteral $route.model))
    if ($route.effort -ne 'not_applicable') {
        $invokeParts.Add('--effort ' + (Quote-PowerShellLiteral $route.effort))
    }
    $invokeParts.Add('--permission-mode plan')
    $invokeParts.Add('--allowedTools ' + (Quote-PowerShellLiteral 'Read,Glob,Grep'))
    $invokeParts.Add((Quote-PowerShellLiteral $bootstrap))
    $commandParts.Add(($invokeParts -join ' '))
}

$sessionCommand = $commandParts -join '; '
$plan | Add-Member -NotePropertyName session_command_preview -NotePropertyValue $sessionCommand

if (-not $Launch) {
    $plan | ConvertTo-Json -Depth 10
    return
}

$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($sessionCommand))
$powershellPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

Start-Process `
    -FilePath $powershellPath `
    -WorkingDirectory $resolvedWorkspace `
    -ArgumentList @('-NoProfile', '-NoExit', '-EncodedCommand', $encoded) `
    -WindowStyle Normal | Out-Null

$plan | Add-Member -NotePropertyName launched -NotePropertyValue $true
$plan | ConvertTo-Json -Depth 10
