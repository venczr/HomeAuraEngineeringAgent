param([int]$RefreshSeconds=2)
$ErrorActionPreference='SilentlyContinue'
$root=Resolve-Path (Join-Path $PSScriptRoot '..\\..')
$control=Join-Path $root 'dev\\autonomous'
$pidPath=Join-Path $control 'supervisor.pid'
$heartbeatPath=Join-Path $control 'supervisor_heartbeat.json'
$statePath=Join-Path $control 'state.json'
$eventsPath=Join-Path $control 'supervisor_events.jsonl'
$stderrPath=Join-Path $control 'supervisor.stderr.log'

while($true){
  Clear-Host
  $heartbeat=$null; $state=$null; $owned=$null
  if(Test-Path $heartbeatPath){$heartbeat=Get-Content $heartbeatPath -Raw|ConvertFrom-Json}
  if(Test-Path $statePath){$state=Get-Content $statePath -Raw|ConvertFrom-Json}
  if(Test-Path $pidPath){
    $ownedPid=(Get-Content $pidPath -Raw).Trim()
    $owned=Get-Process -Id ([int]$ownedPid) -ErrorAction SilentlyContinue
  }
  Write-Host ('HomeAura Supervisor Monitor  '+(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor Cyan
  Write-Host ('Process:    '+$(if($owned){"RUNNING PID=$($owned.Id)"}else{'STOPPED / STALE PID'}))
  Write-Host ('Heartbeat:  '+$(if($heartbeat){"$($heartbeat.status)  $($heartbeat.timestamp)"}else{'MISSING'}))
  Write-Host ('Task:       '+$(if($heartbeat.current_task){$heartbeat.current_task}else{'none'}))
  Write-Host ('Next:       '+$(if($state.NEXT_TASKS){$state.NEXT_TASKS -join ', '}else{'none'}))
  Write-Host ('Wall clock: '+$state.WALL_CLOCK_STATUS)
  Write-Host ('Stderr:     '+$(if(Test-Path $stderrPath){(Get-Item $stderrPath).Length}else{0})+' bytes')
  Write-Host ''
  Write-Host 'Recent events:' -ForegroundColor Yellow
  if(Test-Path $eventsPath){Get-Content $eventsPath -Tail 8}
  Write-Host ''
  Write-Host 'Press Ctrl+C to close monitor; supervisor continues running.' -ForegroundColor DarkGray
  Start-Sleep -Seconds ([Math]::Max(1,$RefreshSeconds))
}
