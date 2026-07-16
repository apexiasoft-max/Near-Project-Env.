# Sprint 1 Approval and Audit Evidence

## Delivered increment

- immutable JSON revision payloads with monotonically increasing target versions and SHA-256 hash;
- project-scoped Map approval and building-scoped Reference/View approvals;
- immutable approval snapshots with actor, time and comment;
- batch Reference/View approval with per-building exclusion;
- targeted invalidation records without deleting or rewriting historical approvals;
- audit timeline containing actor, timestamp, comment and changed values;
- desktop approval controls and audit table;
- versioned API commands for revision, approval, batch approval and audit queries.

## Invalidation contract

- New Map revision invalidates active Map, Reference and View approvals in the same project.
- New Reference revision invalidates active Reference and View approvals only for that building.
- New View revision invalidates active View approvals only for that building.
- Other buildings and unrelated upstream approvals remain valid.

## Verification

- 21 unit/integration tests passed;
- batch exception and upstream/downstream combinations are covered;
- API revision/approval/audit contract passed;
- Ruff and strict mypy passed;
- SQLite migration passed on the existing workstation database;
- live project `PRJ-AF5534DC` stored all three gates and invalidated only the changed View approval;
- final Windows build and packaged worker smoke test passed.

## Final Sprint 1 build

`dist-sprint1-final/NearProjectEnvironment.exe`
