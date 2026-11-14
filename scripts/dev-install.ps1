<#
.SYNOPSIS
    Run the Anakot dev installer from PowerShell on Windows.

.DESCRIPTION
    scripts/dev-install.sh is a bash script and PowerShell cannot execute it. Git for Windows
    installs a bash next to git, but only `git.exe`'s directory is reliably on PATH, so `bash`
    on its own is often "not recognized" even though git works. This wrapper finds bash from the
    git install and forwards the options in PowerShell spelling.

    If PowerShell refuses to load this file ("running scripts is disabled on this system"), the
    execution policy is blocking it, not the script — run either of these instead:

        powershell -ExecutionPolicy Bypass -File .\scripts\dev-install.ps1 -Desktop
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned     # once, then this works normally

.EXAMPLE
    .\scripts\dev-install.ps1 -Run
    .\scripts\dev-install.ps1 -Dir D:\anakot-dev -Ref update/upstream-2026-11-14 -Js -SeedHome
    .\scripts\dev-install.ps1 -Desktop      # install JS deps, then build and open the desktop app
    .\scripts\dev-install.ps1 -Pack         # install JS deps, then package the desktop app (no launch)
#>
[CmdletBinding()]
param(
    [switch]$Run,
    [switch]$Desktop,
    [switch]$Shortcut,
    [switch]$Pack,
    [switch]$Js,
    [switch]$SeedHome,
    [string]$Dir,
    [string]$Ref,
    [string]$HomePath
)

$ErrorActionPreference = 'Stop'

function Find-Bash {
    $candidates = @()
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        # ...\Git\cmd\git.exe -> ...\Git\bin\bash.exe
        $candidates += Join-Path (Split-Path (Split-Path $git.Source)) 'bin\bash.exe'
    }
    $candidates += @(
        (Join-Path $env:ProgramFiles 'Git\bin\bash.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Git\bin\bash.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe')
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return $c }
    }
    return $null
}

$bash = Find-Bash
if (-not $bash) {
    Write-Host '[x] could not locate bash.exe.' -ForegroundColor Red
    Write-Host '    Install Git for Windows (winget install --id Git.Git), then re-run this.' -ForegroundColor Red
    exit 1
}

$script = Join-Path $PSScriptRoot 'dev-install.sh'
if (-not (Test-Path -LiteralPath $script)) {
    Write-Host "[x] expected the installer at $script" -ForegroundColor Red
    exit 1
}

$bashArgs = @($script)
if ($Ref)      { $bashArgs += @('--ref',  $Ref) }
if ($Dir)      { $bashArgs += @('--dir',  $Dir) }
if ($HomePath) { $bashArgs += @('--home', $HomePath) }
if ($Js)       { $bashArgs += '--js' }
if ($Desktop)  { $bashArgs += '--run-desktop' }
if ($Shortcut) { $bashArgs += '--shortcut' }
if ($Pack)     { $bashArgs += '--pack' }
if ($SeedHome) { $bashArgs += '--seed-home' }
if ($Run)      { $bashArgs += '--run' }

Write-Host "==> bash: $bash" -ForegroundColor Cyan
& $bash @bashArgs
exit $LASTEXITCODE
