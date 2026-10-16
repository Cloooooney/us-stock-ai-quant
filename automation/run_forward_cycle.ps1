<#
.SYNOPSIS
    Scheduled entry point for the forward-tracking cycle (Windows).

.DESCRIPTION
    Registered by install_task.ps1 to run every weekday afternoon. The monthly
    cycle runs only on calendar days 1-10, when month-end signals, next-session
    fills and holding-period results become due; the tracker is idempotent, so
    extra runs record nothing twice. Research jobs listed in
    automation/research_jobs.json run on any weekday until their output exists.

    Each run:
      1. refuses to touch a working tree with uncommitted changes to tracked files;
      2. switches to main and updates it, so merged code is picked up;
      3. installs requirements and runs data_pipeline.run_monthly_cycle;
      4. writes automation/status.json and, if a ledger or report changed or the
         run failed, commits and pushes them to GitHub.

    Logs are kept in automation/logs/ (not committed).

.PARAMETER Force
    Run even outside calendar days 1-10 (for a manual test).
#>
param([switch]$Force)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Repo
$env:PYTHONIOENCODING = 'utf-8'
$Python = Join-Path $Repo '.venv\Scripts\python.exe'
$LogDir = Join-Path $Repo 'automation\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("cycle_{0}.log" -f (Get-Date -Format 'yyyy-MM-dd_HHmmss'))

function Write-Log([string]$Message) {
    $line = '{0} {1}' -f (Get-Date -Format s), $Message
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
    Write-Output $line
}

# Native tools write progress to stderr; judge them by exit code only.
function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    Write-Log ("> {0} {1}" -f $Exe, ($Arguments -join ' '))
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object { Write-Log ("  {0}" -f $_) }
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw ("{0} exited with code {1}" -f $Exe, $code) }
}

function Write-Status([string]$Result, [string]$Step) {
    Invoke-Native $Python @('-m', 'automation.status', '--result', $Result, '--step', $Step, '--log', $Log)
}

function Publish([string]$Result, [string[]]$Extra = @()) {
    $outputs = @('paper_trading/v5_ledger.jsonl', 'paper_trading/v6_ledger.jsonl', 'paper_trading/v7_ledger.jsonl',
                 'paper_trading/alpaca_paper_ledger.jsonl', 'paper_trading/signals',
                 'reports/v5_forward', 'reports/v6_forward', 'reports/v7_forward') + $Extra |
        Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $Repo $_)) }
    if ($outputs) { Invoke-Native 'git' (@('add', '--') + $outputs) }
    $changed = [bool](& git diff --cached --name-only)
    if (-not $changed -and $Result -eq 'success') {
        Write-Log 'No forward record changes; nothing to publish.'
        return
    }
    Invoke-Native 'git' @('add', '--', 'automation/status.json')
    $message = 'Forward record update {0} ({1})' -f (Get-Date -Format 'yyyy-MM-dd'), $Result
    Invoke-Native 'git' @('commit', '-m', $message)
    Invoke-Native 'git' @('pull', '--rebase', 'origin', 'main')
    Invoke-Native 'git' @('push', 'origin', 'main')
}

# Research jobs (automation/research_jobs.json) run once, on any weekday, until their output exists.
function Get-PendingJobs {
    $file = Join-Path $Repo 'automation\research_jobs.json'
    if (-not (Test-Path -LiteralPath $file)) { return @() }
    $jobs = Get-Content -LiteralPath $file -Raw -Encoding UTF8 | ConvertFrom-Json
    return @($jobs | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Repo $_.done_when)) })
}

$Due = $Force -or ((Get-Date).Day -le 10)
$step = 'preflight'
$extra = @()
try {
    if (-not (Test-Path -LiteralPath $Python)) { throw "Python environment not found at $Python" }
    # status.json is rewritten every run and only committed when something changed.
    $dirty = @(& git status --porcelain --untracked-files=no) | Where-Object { $_ -notmatch 'automation/status\.json$' }
    if ($dirty) { throw ("Uncommitted changes to tracked files; not touching the repository:`n{0}" -f ($dirty -join "`n")) }

    $step = 'update_code'
    Invoke-Native 'git' @('checkout', 'main')
    # --rebase keeps any forward-record commit that an earlier run could not push.
    Invoke-Native 'git' @('pull', '--rebase', 'origin', 'main')
    $jobs = @(Get-PendingJobs)  # @() keeps a single job as an array in Windows PowerShell 5.1
    if (-not $Due -and $jobs.Count -eq 0) {
        Write-Log 'Outside calendar days 1-10 and no research jobs pending; nothing is due.'
        exit 0
    }
    Invoke-Native $Python @('-m', 'pip', 'install', '--quiet', '-r', 'requirements.txt')

    if ($Due) {
        $step = 'monthly_cycle'
        Invoke-Native $Python @('-m', 'data_pipeline.run_monthly_cycle')
    }
    foreach ($job in $jobs) {
        $step = 'research:' + $job.name
        $extra += @($job.publish)
        Invoke-Native $Python @('-m', $job.module)
    }

    $step = 'publish'
    Write-Status 'success' 'run'
    Publish 'success' $extra
    Write-Log 'Run finished.'
} catch {
    Write-Log ("FAILED during {0}: {1}" -f $step, $_)
    if ($step -eq 'preflight') { exit 1 }  # never commit on top of the user's own changes
    try {
        Write-Status 'failed' $step
        Publish 'failed' $extra
    } catch {
        Write-Log ("Could not publish the failure status: {0}" -f $_)
    }
    exit 1
}
