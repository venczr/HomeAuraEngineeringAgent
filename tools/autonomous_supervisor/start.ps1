param([int]$MaxAttempts=0,[double]$Hours=0,[string]$OnlyTask='',[switch]$Ufh)
$ErrorActionPreference='Stop'
$root=Resolve-Path (Join-Path $PSScriptRoot '..\..');$control=Join-Path $root 'dev\autonomous';$pidPath=Join-Path $control 'supervisor.pid'
New-Item -ItemType Directory -Path $control -Force|Out-Null
if(Test-Path $pidPath){$ownedPid=(Get-Content $pidPath -Raw).Trim();$owned=Get-CimInstance Win32_Process -Filter "ProcessId=$ownedPid" -ErrorAction SilentlyContinue;if($owned -and $owned.CommandLine -match 'tools\.autonomous_supervisor\.cli run'){Write-Output "RUNNING PID=$ownedPid";exit 0};Remove-Item $pidPath -Force}
$launcherArgs=@();$launcherArgs += @('--hours', "$Hours");if($MaxAttempts -gt 0){$launcherArgs += @('--max-attempts', "$MaxAttempts")};if($OnlyTask){$launcherArgs += @('--only-task',$OnlyTask)};if($Ufh){$launcherArgs += @('--ufh')};$ownedPid=& python -m tools.autonomous_supervisor.detached_launcher @launcherArgs
if($LASTEXITCODE -ne 0 -or -not $ownedPid){throw 'Detached supervisor launch failed'}
Set-Content $pidPath $ownedPid -NoNewline;Write-Output "STARTED PID=$ownedPid"
