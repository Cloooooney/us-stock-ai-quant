<#
.SYNOPSIS
    Scheduled entry point for the forward-tracking cycle (Windows).

.DESCRIPTION
    Registered by install_task.ps1 to run every weekday afternoon. It does real
    work only on calendar days 1-10, when month-end signals, next-session fills
    and holding-period results become due; the tracker is idempotent, so extra
    runs record nothing twice.

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

function Publish([string]$Result) {
    $outputs = @('paper_trading/v5_ledger.jsonl', 'paper_trading/v6_ledger.jsonl', 'paper_trading/signals',
                 'reports/v5_forward', 'reports/v6_forward') | Where-Object { Test-Path -LiteralPath (Join-Path $Repo $_) }
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

if (-not $Force -and (Get-Date).Day -gt 10) {
    Write-Log 'Outside calendar days 1-10; nothing is due.'
    exit 0
}

$step = 'preflight'
try {
    if (-not (Test-Path -LiteralPath $Python)) { throw "Python environment not found at $Python" }
    # status.json is rewritten every run and only committed when something changed.
    $dirty = @(& git status --porcelain --untracked-files=no) | Where-Object { $_ -notmatch 'automation/status\.json$' }
    if ($dirty) { throw ("Uncommitted changes to tracked files; not touching the repository:`n{0}" -f ($dirty -join "`n")) }

    $step = 'update_code'
    Invoke-Native 'git' @('checkout', 'main')
    # --rebase keeps any forward-record commit that an earlier run could not push.
    Invoke-Native 'git' @('pull', '--rebase', 'origin', 'main')
    Invoke-Native $Python @('-m', 'pip', 'install', '--quiet', '-r', 'requirements.txt')

    $step = 'monthly_cycle'
    Invoke-Native $Python @('-m', 'data_pipeline.run_monthly_cycle')

    $step = 'publish'
    Write-Status 'success' 'monthly_cycle'
    Publish 'success'
    Write-Log 'Run finished.'
} catch {
    Write-Log ("FAILED during {0}: {1}" -f $step, $_)
    if ($step -eq 'preflight') { exit 1 }  # never commit on top of the user's own changes
    try {
        Write-Status 'failed' $step
        Publish 'failed'
    } catch {
        Write-Log ("Could not publish the failure status: {0}" -f $_)
    }
    exit 1
}
