from __future__ import annotations

from pathlib import Path

from PIL import Image

from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate
from npe.shared.config import AppPaths, Settings


def test_missing_building_does_not_block_replacement_approval_and_resume(
    tmp_path: Path,
) -> None:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("P", 35.7577, 51.4099, 200, "MAIN", 1)
    aerial = tmp_path / "aerial.png"
    Image.new("RGB", (32, 32)).save(aerial)
    polygon = (
        (51.4098, 35.7576), (51.4100, 35.7576),
        (51.4100, 35.7578), (51.4098, 35.7578),
    )
    inventory = container.inventory.build(
        job.project_id,
        AerialCoverage(aerial, 51.406, 35.754, 51.414, 35.761),
        [FootprintCandidate(polygon, "gate"), FootprintCandidate(polygon, "gate")],
    )
    blocked, unaffected = inventory.buildings

    event_id = container.reference_review.mark_missing(job.project_id, blocked.id, "system")
    with container.database.connect() as connection:
        statuses = {
            row["id"]: row["status"]
            for row in connection.execute(
                "SELECT id, status FROM buildings WHERE id IN (?, ?)",
                (blocked.id, unaffected.id),
            )
        }
    assert statuses == {blocked.id: "missing_reference", unaffected.id: "candidate"}

    replacement = tmp_path / "replacement.png"
    Image.new("RGB", (1280, 720), (100, 80, 70)).save(replacement)
    candidate_id = container.reference_review.upload_replacement(
        job.project_id, blocked.id, replacement, "reviewer"
    )
    container.reference_review.select(
        job.project_id, blocked.id, candidate_id, "reviewer", front_bearing_deg=170
    )
    approval = container.reference_review.approve(job.project_id, blocked.id, "reviewer")
    assert approval.valid
    with container.database.connect() as connection:
        event = connection.execute(
            "SELECT status FROM intervention_events WHERE id = ?", (event_id,)
        ).fetchone()
        building = connection.execute(
            "SELECT status, front_bearing_deg FROM buildings WHERE id = ?", (blocked.id,)
        ).fetchone()
    assert event["status"] == "resolved"
    assert (building["status"], building["front_bearing_deg"]) == (
        "reference_approved", 170,
    )

