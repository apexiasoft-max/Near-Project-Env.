from __future__ import annotations

from pathlib import Path

import pytest

from npe.bootstrap import bootstrap
from npe.domain.five_view import REQUIRED_DIRECTIONS
from npe.shared.config import AppPaths, Settings


def setup_attempt(tmp_path: Path) -> tuple[object, object]:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("P", 35.7, 51.4, 200, "B", 30)
    views = {}
    for direction in REQUIRED_DIRECTIONS:
        path = tmp_path / f"{direction}.png"
        path.write_bytes(f"image-{direction}".encode())
        views[direction] = path
    lineage = tmp_path / "lineage.json"
    lineage.write_text("{}", encoding="utf-8")
    attempt = container.five_view_review.register(
        job.project_id, job.building_id, "RUN-1", views, lineage
    )
    return container, attempt


def test_direction_revision_preserves_original_and_creates_new_attempt(
    tmp_path: Path,
) -> None:
    container, attempt = setup_attempt(tmp_path)

    revision = container.five_view_review.request_revision(
        attempt.id, "left facade is inconsistent", {"left"}
    )
    original = container.five_view_review.get(attempt.id)

    assert original.status == "revision_requested"
    left = next(output for output in original.outputs if output.direction == "left")
    assert left.status == "rejected"
    assert revision.status == "pending_generation"
    assert revision.version == 2
    assert revision.parent_attempt_id == attempt.id


def test_only_complete_existing_set_unlocks_hunyuan(tmp_path: Path) -> None:
    container, attempt = setup_attempt(tmp_path)

    approved = container.five_view_review.approve(attempt.id)

    assert approved.status == "approved"
    assert all(output.status == "approved" for output in approved.outputs)
    with container.database.connect() as connection:
        job = connection.execute(
            "SELECT stage FROM jobs WHERE building_id = ?", (attempt.building_id,)
        ).fetchone()
    assert job["stage"] == "ready_for_hunyuan"


def test_revision_and_approval_require_valid_state(tmp_path: Path) -> None:
    container, attempt = setup_attempt(tmp_path)
    container.five_view_review.request_revision(attempt.id, "redo all")

    with pytest.raises(ValueError, match="not ready"):
        container.five_view_review.approve(attempt.id)
