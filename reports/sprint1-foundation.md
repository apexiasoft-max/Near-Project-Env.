# Sprint 1 Foundation Increment

Date: 2026-07-15  
Linear: APE-40 / APE-64

## Delivered

- modular `domain/application/infrastructure/api/desktop/worker/shared` package
  boundaries;
- local SQLite database with WAL, foreign keys, and idempotent migrations;
- loopback-only FastAPI health endpoint;
- persistent runtime paths including browser profile, traces, projects,
  downloads, logs, and worker state;
- worker process with atomic heartbeat;
- PySide6 desktop health screen;
- one Windows launcher that starts UI, API, and worker;
- PyInstaller development EXE;
- development setup/run scripts.

## Verification

- 8 automated tests pass;
- Ruff passes;
- strict mypy passes for `src/npe`;
- packaged Worker exits successfully in `--once` mode;
- packaged API responds on `127.0.0.1:8765`;
- complete packaged launcher starts UI, API, and Worker;
- live packaged Health result: database, disk, worker, browser profile, and
  Blender all `ok`;
- development EXE size: 54,695,223 bytes.

## Security boundary

- configuration rejects non-loopback API hosts;
- browser profile is outside Git;
- no web password, cookie, token, or session file is stored in the database;
- build output and local runtime data are ignored by Git.

## Known development-package limitation

The Sprint 1 development EXE uses a console bootloader for transparent startup
diagnostics. A final no-console installer is deferred to the packaging/release
Feature after the application workflow is stable.
