# Near Project Environment

Local Windows application for producing traceable, meter-scaled FBX models of
buildings around an unbuilt project location.

## Development startup

```powershell
.\scripts\setup-dev.ps1
.\scripts\run-dev.ps1
```

The local API binds only to `127.0.0.1`. Browser credentials and profiles stay
outside the repository. Hunyuan model download is an accepted manual,
non-blocking step in the MVP.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Sprint evidence and technical product documents are under `docs/` and
`spikes/`.

