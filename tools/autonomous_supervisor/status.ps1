$root=Resolve-Path (Join-Path $PSScriptRoot '..\..');$pidPath=Join-Path $root 'dev\autonomous\supervisor.pid';$heartbeat=Join-Path $root 'dev\autonomous\supervisor_heartbeat.json'
if(!(Test-Path $pidPath)){Write-Output 'STOPPED';exit 1};$ownedPid=(Get-Content $pidPath -Raw).Trim();$owned=Get-Process -Id $ownedPid -ErrorAction SilentlyContinue
$heartbeatState=$null;if(Test-Path $heartbeat){$heartbeatState=Get-Content $heartbeat -Raw|ConvertFrom-Json}
if(!$owned -or $owned.ProcessName -notmatch '^python' -or !$heartbeatState -or [string]$heartbeatState.pid -ne [string]$ownedPid){Write-Output "STALE PID=$ownedPid";exit 2}
Write-Output "RUNNING PID=$ownedPid";Get-Content $heartbeat
