$ErrorActionPreference = "Stop"
$Python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

& $Python -m ruff check src tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m mypy src/npe
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m pytest tests/unit -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m pytest tests/integration tests/contract tests/e2e tests/security -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Release quality gate passed."
