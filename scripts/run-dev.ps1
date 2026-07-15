$ErrorActionPreference = "Stop"
$python = Resolve-Path ".\.venv\Scripts\python.exe"
& $python -m npe.main
