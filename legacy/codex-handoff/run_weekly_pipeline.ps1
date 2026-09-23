param(
    [datetime]$RunDate = (Get-Date),
    [switch]$SkipNetworkCollection
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$workDir = Join-Path $projectRoot 'work'
$outputDir = Join-Path $projectRoot 'outputs'
$sitePublicDir = Join-Path $workDir 'nuclear-literature-site\public'
$stateDir = Join-Path $projectRoot 'automation-state'
$logDir = Join-Path $projectRoot 'logs'
$pythonExe = 'C:\Program Files\Python310\python.exe'
$nodeExe = 'C:\Program Files\nodejs\node.exe'

$daysSinceMonday = (([int]$RunDate.DayOfWeek + 6) % 7)
$runDay = $RunDate.Date.AddDays(-$daysSinceMonday)
$periodEnd = $runDay.AddDays(-1)
$periodStart = $runDay.AddDays(-7)
$previousEnd = $periodEnd.AddDays(-7)
$previousStart = $periodStart.AddDays(-7)

$runDateText = $runDay.ToString('yyyy-MM-dd')
$periodStartText = $periodStart.ToString('yyyy-MM-dd')
$periodEndText = $periodEnd.ToString('yyyy-MM-dd')
$previousStartText = $previousStart.ToString('yyyy-MM-dd')
$previousEndText = $previousEnd.ToString('yyyy-MM-dd')

New-Item -ItemType Directory -Force -Path $outputDir, $stateDir, $logDir | Out-Null
$logPath = Join-Path $logDir "weekly-pipeline-$runDateText.log"
$statusPath = Join-Path $stateDir 'latest-run.json'
$startedAt = Get-Date

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    "[$(Get-Date -Format o)] START $Name" | Tee-Object -FilePath $logPath -Append
    & $Action 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
    "[$(Get-Date -Format o)] OK $Name" | Tee-Object -FilePath $logPath -Append
}

try {
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw "Python not found: $pythonExe" }
    if (-not (Test-Path -LiteralPath $nodeExe)) { throw "Node not found: $nodeExe" }

    if (-not $SkipNetworkCollection) {
        Invoke-Step 'Collect current period metadata' {
            & $pythonExe (Join-Path $workDir 'collect_metadata.py') --start $periodStartText --end $periodEndText --output (Join-Path $workDir 'articles.json')
        }
        Invoke-Step 'Collect comparison period metadata' {
            & $pythonExe (Join-Path $workDir 'collect_previous_period.py') --start $previousStartText --end $previousEndText --output (Join-Path $workDir 'articles_previous.json')
        }
        Invoke-Step 'Translate titles' {
            & $pythonExe (Join-Path $workDir 'translate_titles.py')
        }
    }

    Invoke-Step 'Update SQLite database' {
        & $pythonExe (Join-Path $workDir 'update_weekly_database.py') --start $periodStartText --end $periodEndText --run-date $runDateText
    }
    if (-not $SkipNetworkCollection) {
        Invoke-Step 'Complete missing country metadata' {
            & $pythonExe (Join-Path $workDir 'enrich_countries.py')
        }
    }

    $env:NUCLEAR_RUN_DATE = $runDateText
    $env:NUCLEAR_PERIOD_START = $periodStartText
    $env:NUCLEAR_PERIOD_END = $periodEndText
    $env:NUCLEAR_PREVIOUS_START = $previousStartText
    $env:NUCLEAR_PREVIOUS_END = $previousEndText

    Invoke-Step 'Build dashboard HTML' {
        & $pythonExe (Join-Path $workDir 'build_digest.py')
    }
    Invoke-Step 'Build email HTML' {
        & $pythonExe (Join-Path $workDir 'build_email_digest.py')
    }
    Invoke-Step 'Build Excel database' {
        & $nodeExe (Join-Path $workDir 'build_literature_workbook.mjs')
    }

    $dashboardPath = Join-Path $outputDir "nuclear-literature-digest-$runDateText.html"
    $emailPath = Join-Path $outputDir "nuclear-literature-email-$runDateText.html"
    $excelPath = Join-Path $outputDir 'nuclear-literature-database.xlsx'
    foreach ($requiredPath in @($dashboardPath, $emailPath, $excelPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath)) { throw "Required output missing: $requiredPath" }
        if ((Get-Item -LiteralPath $requiredPath).Length -eq 0) { throw "Required output is empty: $requiredPath" }
    }
    Copy-Item -LiteralPath $dashboardPath -Destination (Join-Path $sitePublicDir 'dashboard.html') -Force

    $articleCount = (Get-Content -Raw -Encoding UTF8 (Join-Path $workDir 'articles.json') | ConvertFrom-Json).Count
    $status = [ordered]@{
        status = 'success'
        run_date = $runDateText
        period_start = $periodStartText
        period_end = $periodEndText
        article_count = $articleCount
        dashboard_path = $dashboardPath
        email_path = $emailPath
        excel_path = $excelPath
        site_source_path = (Join-Path $sitePublicDir 'dashboard.html')
        dashboard_url = 'https://nuclear-literature-dashboard.ssrmin.chatgpt.site'
        recipient = 'hysms@hanyang.ac.kr'
        started_at = $startedAt.ToString('o')
        finished_at = (Get-Date).ToString('o')
        log_path = $logPath
    }
    $status | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    $status | ConvertTo-Json -Depth 5
}
catch {
    $status = [ordered]@{
        status = 'failed'
        run_date = $runDateText
        period_start = $periodStartText
        period_end = $periodEndText
        error = $_.Exception.Message
        started_at = $startedAt.ToString('o')
        finished_at = (Get-Date).ToString('o')
        log_path = $logPath
    }
    $status | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    $status | ConvertTo-Json -Depth 5 | Tee-Object -FilePath $logPath -Append
    exit 1
}
