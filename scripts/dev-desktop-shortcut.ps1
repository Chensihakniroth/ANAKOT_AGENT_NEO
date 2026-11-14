<#
.SYNOPSIS
    Create a Desktop shortcut that launches an Anakot dev build.

.DESCRIPTION
    Used by scripts/dev-install.sh --shortcut. The shortcut points at a generated
    .cmd launcher rather than at electron.exe, because a .lnk cannot carry
    environment variables and the dev app needs both ANAKOT_HOME (it reads that from
    its own process env, never from a .env) and the bundled Node/pnpm on PATH.

.PARAMETER CmdPath
    Path to the generated .cmd launcher.

.PARAMETER Name
    Shortcut name, without the .lnk extension.

.PARAMETER OutDir
    Where to write the shortcut. Defaults to the user's Desktop.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$CmdPath,
    [string]$Name = 'Anakot Dev',
    [string]$OutDir
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $CmdPath)) {
    Write-Host "[x] launcher not found: $CmdPath" -ForegroundColor Red
    exit 1
}

if (-not $OutDir) {
    $OutDir = [Environment]::GetFolderPath('Desktop')
}
if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$link = Join-Path $OutDir "$Name.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = (Resolve-Path -LiteralPath $CmdPath).Path
$shortcut.WorkingDirectory = Split-Path -Parent (Resolve-Path -LiteralPath $CmdPath).Path
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$shortcut.Description = 'Anakot (dev build)'
$shortcut.Save()

Write-Host "==> shortcut: $link" -ForegroundColor Cyan