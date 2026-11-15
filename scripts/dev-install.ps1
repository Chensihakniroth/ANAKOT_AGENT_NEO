<#
.SYNOPSIS
    Run the Anakot dev installer from PowerShell on Windows.

.DESCRIPTION
    scripts/dev-install.sh is a bash script and PowerShell cannot execute it. Git for Windows
    installs a bash next to git, but only `git.exe`'s directory is reliably on PATH, so `bash`
    on its own is often "not recognized" even though git works. This wrapper finds bash from the
    git install and forwards the options in PowerShell spelling.

    Prerequisites are git, uv, and -- for -Js, -Desktop and -Pack -- Node 26 or newer with pnpm.
    They are resolved and reported together before any work starts, so a missing tool costs seconds
    and names its own install line instead of surfacing twenty minutes later. Node 26 no longer
    bundles corepack, which is why pnpm is a prerequisite in its own right on a fresh machine.
    -Check reports what is missing and changes nothing; -Tools installs the missing pieces first.

    If PowerShell refuses to load this file ("running scripts is disabled on this system"), the
    execution policy is blocking it, not the script — run either of these instead:

        powershell -ExecutionPolicy Bypass -File .\scripts\dev-install.ps1 -Desktop
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned     # once, then this works normally

.EXAMPLE
    .\scripts\dev-install.ps1 -Check        # what is this machine missing? nothing is changed
    .\scripts\dev-install.ps1 -Pack -Tools  # install any missing prerequisite, then package the app
    .\scripts\dev-install.ps1 -Run
    .\scripts\dev-install.ps1 -Dir D:\anakot-dev -Ref update/upstream-2026-11-15 -Js -SeedHome
    .\scripts\dev-install.ps1 -Desktop      # install JS deps, then build and open the desktop app
#>
[CmdletBinding()]
param(
    [switch]$Run,
    [switch]$Desktop,
    [switch]$Shortcut,
    [switch]$Pack,
    [switch]$Js,
    [switch]$SeedHome,
    [switch]$Check,
    [switch]$Tools,
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

function Get-ToolPath {
    # PATH first, then the well-known install locations: winget and `npm -g` only refresh PATH for
    # the *next* shell, so a run that installs a tool and carries on has to find it by path.
    param([string]$Name, [string[]]$Candidates = @())
    $onPath = Get-Command $Name -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    foreach ($c in $Candidates) { if ($c -and (Test-Path -LiteralPath $c)) { return $c } }
    return $null
}

function Get-NodeMajor {
    param([string]$Exe)
    if (-not $Exe) { return 0 }
    try {
        $raw = & $Exe --version 2>$null
        if (-not $raw) { return 0 }
        return [int]("$raw".TrimStart('v').Split('.')[0])
    } catch { return 0 }
}

function Get-BundledTool {
    # Anakot stages its own node/pnpm under ...\anakot\tools, and the staged copy is the version
    # the locks were written with. A machine that already has the app needs no system install --
    # without this, -Tools sees the *system* node (often an older one) and adds another.
    param([string]$Pattern)
    foreach ($root in @((Join-Path $env:LOCALAPPDATA 'anakot\tools'),
                        (Join-Path $env:USERPROFILE '.anakot\tools'))) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $hit = Get-ChildItem -Path (Join-Path $root $Pattern) -ErrorAction SilentlyContinue |
               Sort-Object Name -Descending | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

function Get-PnpmPin {
    # The repo pins its toolchain exactly: pm/lock.json carries packages.pnpm.version and a pnpm
    # preinstall guard refuses to run under any other version, so `npm install -g pnpm` (latest) is
    # the wrong install -- it fails inside `pnpm install` after the JS step has already started.
    $lock = Join-Path $PSScriptRoot '..\pm\lock.json'
    if (-not (Test-Path -LiteralPath $lock)) { return $null }
    try { return (Get-Content -LiteralPath $lock -Raw | ConvertFrom-Json).packages.pnpm.version }
    catch { return $null }
}

function Get-PnpmVersion {
    param([string]$Exe)
    if (-not $Exe) { return '' }
    try { $v = & $Exe --version 2>$null; return "$v".Trim() } catch { return '' }
}

function Install-WingetPackage {
    param([string]$Id, [string]$Label)
    Write-Host "    $Label" -ForegroundColor Cyan
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host "    [x] winget not available -- install $Id yourself, then re-run" -ForegroundColor Red
        return
    }
    winget install --id $Id -e --source winget --accept-package-agreements --accept-source-agreements
}

function Install-Prerequisites {
    Write-Host '==> installing missing prerequisites' -ForegroundColor Cyan

    $git = Get-ToolPath 'git.exe' @((Join-Path $env:ProgramFiles 'Git\cmd\git.exe'))
    if (-not $git) { Install-WingetPackage 'Git.Git' 'git (also provides the bash this runs in)' }

    $node = Get-ToolPath 'node.exe' @((Get-BundledTool 'node-*\node.exe'),
                                      (Join-Path $env:ProgramFiles 'nodejs\node.exe'))
    if ((Get-NodeMajor $node) -lt 26) {
        Install-WingetPackage 'OpenJS.NodeJS' 'Node.js 26+ (the JS tree requires it)'
        $node = Join-Path $env:ProgramFiles 'nodejs\node.exe'
    }

    $pin = Get-PnpmPin
    $pnpm = Get-ToolPath 'pnpm.cmd' @((Get-BundledTool 'pnpm-*\pnpm.exe'),
                                      (Get-BundledTool 'pnpm-*\pnpm.cmd'),
                                      (Join-Path $env:APPDATA 'npm\pnpm.cmd'),
                                      (Join-Path $env:ProgramFiles 'nodejs\pnpm.cmd'))
    if ($pnpm -and $pin -and (Get-PnpmVersion $pnpm) -ne $pin) {
        Write-Host "    pnpm $(Get-PnpmVersion $pnpm) does not match the repo pin $pin" -ForegroundColor Yellow
        $pnpm = $null
    }
    if (-not $pnpm) {
        $npm = Get-ToolPath 'npm.cmd' @((Join-Path $env:ProgramFiles 'nodejs\npm.cmd'))
        if ($npm) {
            $spec = if ($pin) { "pnpm@$pin" } else { 'pnpm' }
            Write-Host "    $spec" -ForegroundColor Cyan
            & $npm install -g $spec
        } else {
            Write-Host '    [x] npm not found -- install Node.js before pnpm' -ForegroundColor Red
        }
    }

    $uv = Get-ToolPath 'uv.exe' @((Join-Path $env:USERPROFILE '.local\bin\uv.exe'))
    if (-not $uv) {
        Write-Host '    uv' -ForegroundColor Cyan
        powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    }

    Write-Host ''
}

if ($Tools) { Install-Prerequisites }

$bash = Find-Bash
if (-not $bash) {
    Write-Host '[x] could not locate bash.exe.' -ForegroundColor Red
    Write-Host '    Install Git for Windows (winget install --id Git.Git), then re-run this.' -ForegroundColor Red
    if (-not $Tools) { Write-Host '    Or re-run it with -Tools and it will install git first.' -ForegroundColor Yellow }
    exit 1
}

$script = Join-Path $PSScriptRoot 'dev-install.sh'
if (-not (Test-Path -LiteralPath $script)) {
    Write-Host "[x] expected the installer at $script" -ForegroundColor Red
    exit 1
}

# --check resolves the whole toolchain, prints it and exits before reading or writing anything, so
# it is safe to run on a machine you are not ready to install on.
$bashArgs = @($script)
if ($Check)    { $bashArgs += '--check' }
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
