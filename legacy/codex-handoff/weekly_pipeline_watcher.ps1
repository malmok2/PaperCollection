$ErrorActionPreference = 'Continue'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pipelinePath = Join-Path $projectRoot 'run_weekly_pipeline.ps1'
$stateDir = Join-Path $projectRoot 'automation-state'
$statusPath = Join-Path $stateDir 'latest-run.json'
$pidPath = Join-Path $stateDir 'watcher.pid'
$watcherLog = Join-Path $projectRoot 'logs\weekly-watcher.log'

New-Item -ItemType Directory -Force -Path $stateDir, (Split-Path -Parent $watcherLog) | Out-Null

if (Test-Path -LiteralPath $pidPath) {
    $existingPid = Get-Content -LiteralPath $pidPath -ErrorAction SilentlyContinue
    if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        exit 0
    }
}
$PID | Set-Content -LiteralPath $pidPath -Encoding ascii

$nextAttempt = Get-Date
try {
    while ($true) {
        $now = Get-Date
        $daysSinceMonday = (([int]$now.DayOfWeek + 6) % 7)
        $scheduledMonday = $now.Date.AddDays(-$daysSinceMonday)
        $scheduledTime = $scheduledMonday.AddHours(8)
        $completed = $false
        if (Test-Path -LiteralPath $statusPath) {
            try {
                $latest = Get-Content -Raw -Encoding UTF8 -LiteralPath $statusPath | ConvertFrom-Json
                $completed = ($latest.status -eq 'success' -and $latest.run_date -eq $scheduledMonday.ToString('yyyy-MM-dd'))
            }
            catch {
                $completed = $false
            }
        }
        if ($now -ge $scheduledTime -and -not $completed -and $now -ge $nextAttempt) {
            "[$(Get-Date -Format o)] Starting weekly pipeline for $($scheduledMonday.ToString('yyyy-MM-dd'))" | Add-Content -LiteralPath $watcherLog -Encoding UTF8
            & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $pipelinePath -RunDate $scheduledMonday.ToString('yyyy-MM-dd') 2>&1 | Add-Content -LiteralPath $watcherLog -Encoding UTF8
            if ($LASTEXITCODE -eq 0) {
                "[$(Get-Date -Format o)] Weekly pipeline completed" | Add-Content -LiteralPath $watcherLog -Encoding UTF8
            }
            else {
                "[$(Get-Date -Format o)] Weekly pipeline failed; retry scheduled in one hour" | Add-Content -LiteralPath $watcherLog -Encoding UTF8
                $nextAttempt = (Get-Date).AddHours(1)
            }
        }
        Start-Sleep -Seconds 60
    }
}
finally {
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}
