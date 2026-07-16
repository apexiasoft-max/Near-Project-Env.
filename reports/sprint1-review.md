# Sprint 1 Review

## Sprint outcome

The Windows application now provides a real one-building Hunyuan-to-FBX walking skeleton,
persistent project lifecycle controls, a restart-safe dashboard and three auditable approval gates.

## Delivered evidence

- Browser Adapter: five mapped uploads, three accepted views, automatic generation start.
- Manual MVP download boundary followed by direct-FBX Blender normalization and re-import.
- Project lifecycle: Draft, Running, Paused, Completed and Cancelled with preflight.
- Dashboard and server-sent progress snapshots survive restart.
- Immutable Map/Reference/View revisions, approvals, batch exceptions and targeted invalidation.
- 21 automated tests, Ruff, strict mypy, PyInstaller build and packaged runtime smoke test passed.

## Live artifacts

- Final FBX: `C:/ProgramData/NearProjectEnvironment/projects/PRJ-AF5534DC/buildings/BLD-214CDF32/models/final/RUN-ADAPTER-LIVE-002.fbx`
- Browser evidence: `C:/ProgramData/NearProjectEnvironment/browser-traces/RUN-ADAPTER-LIVE-002/`
- Final application: `dist-sprint1-final/NearProjectEnvironment.exe`

## Remaining accepted boundaries

- Hunyuan download remains a manual operator action in the MVP.
- Hunyuan detection failures expose no detailed provider reason; the approved minimum is three views.
- Automatic Tehran building discovery and source imagery acquisition belong to later increments.

## Recommendation

Go. Sprint 1 acceptance is complete; subsequent work can build on persisted projects, jobs,
browser automation, normalized FBX delivery and auditable approvals.
