<#
.SYNOPSIS
    Register the weekday Windows scheduled task that runs run_forward_cycle.ps1.

.DESCRIPTION
    Run once from the repository root:

        powershell -ExecutionPolicy Bypass -File automation\install_task.ps1

    The task runs as the current user at 2:30 PM local time on weekdays, after
    the US market close. If the computer is off or asleep at that time, it runs
    as soon as possible afterwards. Running this script again replaces the task.

.PARAMETER Time
    Local start time, default 2:30PM.

.PARAMETER Remove
    Unregister the task instead.
#>
param([string]$Time = '2:30PM', [switch]$Remove)

$ErrorActionPreference = 'Stop'
$TaskName = 'us-stock-ai-quant forward cycle'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Removed scheduled task '$TaskName'."
    exit 0
}

$Repo = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $PSScriptRoot 'run_forward_cycle.ps1'
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $Script) -WorkingDirectory $Repo
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $Time
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description 'Forward-tracking cycle for V5 and V6 (records signals, fills, and period results).' -Force | Out-Null

Write-Output "Registered '$TaskName' for weekdays at $Time."
Write-Output "Test it now with:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Output "Logs: $(Join-Path $Repo 'automation\logs')"
