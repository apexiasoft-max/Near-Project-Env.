param([string]$Version = "0.1.0-mvp")

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ReleaseRoot = Join-Path $ProjectRoot "release"
$Stage = Join-Path $ReleaseRoot "NearProjectEnvironment-$Version"

& (Join-Path $ProjectRoot "scripts\run_release_gate.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m PyInstaller --noconfirm --clean `
    --distpath (Join-Path $ProjectRoot "dist-release") `
    --workpath (Join-Path $ProjectRoot "build-release") `
    (Join-Path $ProjectRoot "packaging\npe.spec")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "dist-release\NearProjectEnvironment.exe") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "packaging\install.ps1") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "packaging\release-manifest.json") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "packaging\requirements.lock") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "docs\13-operator-runbook.md") -Destination $Stage

$Files = Get-ChildItem -LiteralPath $Stage -Recurse -File | ForEach-Object {
    [ordered]@{
        path = $_.FullName.Substring($Stage.Length).TrimStart('\', '/').Replace('\', '/')
        sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()
        size_bytes = $_.Length
    }
}
[ordered]@{ version = $Version; files = @($Files) } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $Stage "checksums.json") -Encoding utf8

$Archive = Join-Path $ReleaseRoot "NearProjectEnvironment-$Version.zip"
if (Test-Path -LiteralPath $Archive) { Remove-Item -LiteralPath $Archive -Force }
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Archive -CompressionLevel Optimal
Write-Host "Release package: $Archive"
