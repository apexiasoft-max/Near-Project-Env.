# Sprint 1 Project Lifecycle Evidence

## Delivered increment

- validated project name, latitude, longitude, radius and absolute output path;
- persistent `draft`, `running`, `paused`, `completed` and `cancelled` states;
- explicit transition rules for Start, Pause, Resume, Complete and Cancel;
- required-dependency preflight with component-specific failure messages;
- persistent project/building/job dashboard in the desktop application;
- versioned API project query and lifecycle commands;
- server-sent project progress snapshots;
- SQLite migration compatible with existing workstation data.

## Automated verification

- 18 unit/integration tests passed;
- restart recovery, invalid transitions, failed preflight and invalid input paths are covered;
- Ruff passed;
- strict mypy passed;
- PyInstaller Windows build passed;
- packaged worker smoke test passed.

## Live workstation acceptance

- Project: `PRJ-E461CC87` (`Sprint 1 Lifecycle Acceptance`)
- Sequence: `draft -> running -> paused -> application restart -> running -> cancelled`
- Dashboard counts after restart: one building, one job, zero completed jobs.
- Output path: `C:/ProgramData/NearProjectEnvironment/acceptance-output`
- No lifecycle state or project metadata was lost across restart.

## Safe-checkpoint contract

Pause and Cancel update persistent project intent at command boundaries. Workers must inspect project
status before claiming a new job or beginning the next external stage. In-flight third-party calls are
not terminated destructively; the new status takes effect at the following stage boundary.
