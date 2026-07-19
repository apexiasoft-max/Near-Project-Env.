param(
    [Parameter(Mandatory = $false)]
    [string]$SourceRoot = $PSScriptRoot,
    [Parameter(Mandatory = $false)]
    [string]$InstallRoot = "$env:LOCALAPPDATA\NearProjectEnvironment",
    [switch]$SkipPrerequisiteCheck
)

$ErrorActionPreference = "Stop"
$SourceRoot = (Resolve-Path -LiteralPath $SourceRoot).Path
$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
$ManifestPath = Join-Path $SourceRoot "checksums.json"
if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "checksums.json is missing" }

$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
foreach ($File in $Manifest.files) {
    $Path = Join-Path $SourceRoot $File.path
    if (-not (Test-Path -LiteralPath $Path)) { throw "Release file missing: $($File.path)" }
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower()
    if ($Actual -ne $File.sha256) { throw "Checksum mismatch: $($File.path)" }
}

$Parent = Split-Path -Parent $InstallRoot
New-Item -ItemType Directory -Force -Path $Parent | Out-Null
$Backup = "$InstallRoot.previous"
if (Test-Path -LiteralPath $Backup) { Remove-Item -LiteralPath $Backup -Recurse -Force }
if (Test-Path -LiteralPath $InstallRoot) { Move-Item -LiteralPath $InstallRoot -Destination $Backup }

try {
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    foreach ($File in $Manifest.files) {
        $Target = Join-Path $InstallRoot $File.path
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
        Copy-Item -LiteralPath (Join-Path $SourceRoot $File.path) -Destination $Target
    }
    $Executable = Join-Path $InstallRoot "NearProjectEnvironment.exe"
    if (-not $SkipPrerequisiteCheck) {
        & $Executable --component prerequisites
        if ($LASTEXITCODE -ne 0) { throw "Prerequisite verification failed" }
    }
    & $Executable --component upgrade
    if ($LASTEXITCODE -ne 0) { throw "Database backup/migration failed" }
    if (Test-Path -LiteralPath $Backup) { Remove-Item -LiteralPath $Backup -Recurse -Force }
} catch {
    if (Test-Path -LiteralPath $InstallRoot) {
        Remove-Item -LiteralPath $InstallRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $Backup) {
        Move-Item -LiteralPath $Backup -Destination $InstallRoot
    }
    throw
}

Write-Host "Near Project Environment installed successfully at $InstallRoot"
