from __future__ import annotations

from pathlib import Path

import pytest

from npe.application.recovery import AtomicArtifactWriter
from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings


def container_at(root: Path):  # type: ignore[no-untyped-def]
    return bootstrap(Settings(paths=AppPaths.under(root), minimum_free_disk_bytes=0))


def test_restart_reconciles_running_attempt_and_resumes_same_stage(tmp_path: Path) -> None:
    first = container_at(tmp_path / "data")
    job = first.workflow.create_job("P", 35.7, 51.4, 200, "B1", 20)
    attempt = first.recovery.begin(job.run_id, "reference_acquisition", {"provider": "google"})

    restarted = container_at(tmp_path / "data")
    assert restarted.recovery.reconcile() == [job.run_id]
    assert restarted.recovery.resume(job.run_id).value == "awaiting_views"
    with restarted.database.connect() as connection:
        stored = connection.execute(
            "SELECT status FROM stage_attempts WHERE id = ?", (attempt.id,)
        ).fetchone()
        job_row = connection.execute(
            "SELECT status, last_error FROM jobs WHERE run_id = ?", (job.run_id,)
        ).fetchone()
    assert stored["status"] == "interrupted"
    assert job_row["status"] == "active"
    assert job_row["last_error"] is None


def test_reconciliation_does_not_affect_other_building(tmp_path: Path) -> None:
    container = container_at(tmp_path / "data")
    interrupted = container.workflow.create_job("A", 35.7, 51.4, 100, "A", 10)
    unaffected = container.workflow.create_job("B", 35.7, 51.4, 100, "B", 10)
    container.recovery.begin(interrupted.run_id, "generation")

    container.recovery.reconcile()

    with container.database.connect() as connection:
        statuses = {
            row["run_id"]: row["status"]
            for row in connection.execute("SELECT run_id, status FROM jobs").fetchall()
        }
    assert statuses[interrupted.run_id] == "recoverable"
    assert statuses[unaffected.run_id] == "active"


def test_atomic_writer_removes_partial_when_validation_fails(tmp_path: Path) -> None:
    target = tmp_path / "artifact.fbx"

    with pytest.raises(ValueError, match="validation"):
        AtomicArtifactWriter().write(target, b"incomplete", lambda _path: False)

    assert not target.exists()
    assert not (tmp_path / "artifact.fbx.partial").exists()


def test_atomic_writer_renames_only_valid_artifact(tmp_path: Path) -> None:
    target = tmp_path / "artifact.fbx"

    result = AtomicArtifactWriter().write(
        target, b"valid-model-content", lambda path: path.stat().st_size > 10
    )

    assert result.read_bytes() == b"valid-model-content"
    assert not (tmp_path / "artifact.fbx.partial").exists()
