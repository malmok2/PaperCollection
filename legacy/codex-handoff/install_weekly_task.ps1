$ErrorActionPreference = 'Stop'

$taskName = 'Codex Nuclear Literature Weekly'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pipelinePath = Join-Path $projectRoot 'run_weekly_pipeline.ps1'

if (-not (Test-Path -LiteralPath $pipelinePath)) {
    throw "Pipeline script not found: $pipelinePath"
}

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $pipelinePath + '"'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At '08:00'
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -RunOnlyIfNetworkAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Collect nuclear engineering papers, update SQLite/Excel, and stage dashboard/email HTML before the Monday 09:00 digest.' `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $taskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
[pscustomobject]@{
    TaskName = $task.TaskName
    State = $task.State
    NextRunTime = $taskInfo.NextRunTime
    Pipeline = $pipelinePath
} | Format-List

Write-Host 'Installation complete. Keep the computer signed in and connected to the internet on Monday morning.' -ForegroundColor Green
