<#
.SYNOPSIS
    One command from a blank Windows VM to a working, packaged Anakot dev build on the Desktop.

.DESCRIPTION
    Everything the manual sequence needed, in order, without stopping to ask:
      1. git -- installed through winget when missing, then always called by absolute path, because
         waiting for a PATH refresh is what makes the next step fail on a fresh box
      2. the checkout -- cloned, or re-pointed at the pushed ref when it is already there
      3. scripts/dev-install.ps1 -Tools -Pack -SeedHome -- missing tools, lock identity, the Python
         env, JS deps, the Electron binary, the packaged app, and the Desktop icon

    Safe to re-run: every step is either idempotent or converges on the pushed ref. Ignored paths
    (.venv, node_modules, the dev home) survive the update, so a re-run costs the changed code.

.PARAMETER Dir
    Where the dev checkout lives. Defaults to %USERPROFILE%\anakot-dev.

.PARAMETER Ref
    Branch or tag to build. Defaults to main.

.PARAMETER HomePath
    Dev profile home. Defaults to %USERPROFILE%\anakot-dev-home, and is never the live profile.

.PARAMETER NoPack
    Stop after the dev install: no JS deps, no packaged app, no Desktop icon.

.PARAMETER NoSeed
    Do not copy the live profile's config.yaml/.env into the dev home.

.EXAMPLE
    # from a blank VM, one line (the ref appears twice so the fetched script and the build agree):
    powershell -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create((irm 'https://raw.githubusercontent.com/Chensihakniroth/ANAKOT_AGENT_NEO/update/upstream-2026-11-15/scripts/dev-bootstrap.ps1'))) -Ref update/upstream-2026-11-15"

.EXAMPLE
    # already have the checkout? run it in place, same result:
    .\scripts\dev-bootstrap.ps1 -Ref update/upstream-2026-11-15
#>
[CmdletBinding()]
param(
    [string]$Dir,
    [string]$Ref = 'main',
    [string]$HomePath,
    [switch]$NoPack,
    [switch]$NoSeed
)

$ErrorActionPreference = 'Stop'
$repoUrl = 'https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO.git'

function Get-ToolPath {
    # PATH first, then the standard install locations: a winget install lands after this session's
    # PATH was built, so the only reliable way to use it is by path.
    param([string]$Name, [string[]]$Candidates = @())
    $onPath = Get-Command $Name -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    foreach ($c in $Candidates) { if ($c -and (Test-Path -LiteralPath $c)) { return $c } }
    return $null
}

function Install-WingetPackage {
    param([string]$Id, [string]$Label)
    Write-Host "==> installing $Label" -ForegroundColor Cyan
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is not available on this machine -- install $Id yourself, then re-run"
    }
    winget install --id $Id -e --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] winget exited $LASTEXITCODE for $Id -- check the output above" -ForegroundColor Yellow
    }
}

# ── 1. git: everything after this needs it, including the bash the installer runs in ──────────────
$git = Get-ToolPath 'git.exe' @(
    (Join-Path $env:ProgramFiles 'Git\cmd\git.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Git\cmd\git.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe')
)
if (-not $git) {
    Install-WingetPackage 'Git.Git' 'Git for Windows (also provides the bash the installer runs in)'
    $git = Join-Path $env:ProgramFiles 'Git\cmd\git.exe'
    if (-not (Test-Path -LiteralPath $git)) {
        throw "git was installed but is not at $git -- open a new window and run this script again"
    }
}
Write-Host "==> git: $git" -ForegroundColor Cyan

# ── 2. the checkout ───────────────────────────────────────────────────────────────────────────────
if (-not $Dir) { $Dir = Join-Path $env:USERPROFILE 'anakot-dev' }
if (Test-Path -LiteralPath (Join-Path $Dir '.git')) {
    Write-Host "==> moving $Dir to origin/$Ref" -ForegroundColor Cyan
    & $git -C $Dir fetch --quiet --depth 1 origin $Ref
    if ($LASTEXITCODE -ne 0) { throw "could not fetch $Ref from $repoUrl" }
    # Discards local commits and tracked edits on purpose: this tree is a build target, not a place
    # to work. .venv, node_modules and the dev home are ignored, so they survive.
    & $git -C $Dir reset --hard FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw "could not move the checkout to $Ref" }
    Write-Host ("==> at {0}" -f (& $git -C $Dir rev-parse --short HEAD)) -ForegroundColor Cyan
} else {
    Write-Host "==> cloning $Ref into $Dir" -ForegroundColor Cyan
    & $git clone --depth 1 --branch $Ref $repoUrl $Dir
    if ($LASTEXITCODE -ne 0) { throw "could not clone $Ref" }
}

$installer = Join-Path $Dir 'scripts\dev-install.ps1'
if (-not (Test-Path -LiteralPath $installer)) { throw "expected the installer at $installer" }

# ── 3. tools, locks, env, JS deps, Electron, pack, Desktop icon ───────────────────────────────────
$forward = @('-Tools')
if (-not $NoSeed) { $forward += '-SeedHome' }
if (-not $NoPack) { $forward += @('-Js', '-Pack') }
if ($HomePath) { $forward += @('-HomePath', $HomePath) }

Write-Host "==> dev-install.ps1 $($forward -join ' ')" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $installer @forward
exit $LASTEXITCODE
