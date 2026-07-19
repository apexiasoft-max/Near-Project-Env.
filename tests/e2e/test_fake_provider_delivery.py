from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from npe.bootstrap import bootstrap
from npe.domain.reference import ReferenceObservation, ReferenceProvider
from npe.shared.config import AppPaths, Settings


def test_fake_provider_result_flows_to_completed_delivery(tmp_path: Path) -> None:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("Fake provider E2E", 35.75, 51.4, 200, "B001", 24)
    source = tmp_path / "source"
    source.mkdir()
    reference = source / "reference.jpg"
    reference.write_bytes(b"synthetic-reference")
    observation = ReferenceObservation(
        ReferenceProvider.GOOGLE, "fake-google-1", reference, None,
        (51.3998, 35.75), 90, 90, 1920, 1080, 0.95, 0.05, {"fake": True},
    )
    footprint = (
        (51.4, 35.75), (51.4001, 35.75),
        (51.4001, 35.7501), (51.4, 35.7501),
    )
    ranked = container.references.rank(job.building_id, footprint, [observation])
    assert ranked[0].observation.source_id == "fake-google-1"
    now = datetime.now(UTC).isoformat()
    raw = source / "raw.glb"
    final = source / "final.fbx"
    raw.write_bytes(b"synthetic-raw-model")
    final.write_bytes(b"synthetic-meter-scaled-fbx")
    with container.database.connect() as connection:
        connection.execute(
            "UPDATE reference_candidates SET selected = 1 WHERE building_id = ?",
            (job.building_id,),
        )
        connection.execute(
            """UPDATE jobs SET stage = 'completed', status = 'completed',
               downloaded_model_path = ?, final_fbx_path = ? WHERE id = ?""",
            (str(raw), str(final), job.id),
        )
        connection.execute(
            """INSERT INTO five_view_attempts
               (id, project_id, building_id, run_id, version, status, guidance_json, created_at)
               VALUES ('FAKE-VIEW', ?, ?, ?, 1, 'approved', '{}', ?)""",
            (job.project_id, job.building_id, job.run_id, now),
        )
        for direction in ("front", "back", "left", "right", "top"):
            path = source / f"{direction}.png"
            path.write_bytes(f"synthetic-{direction}".encode())
            connection.execute(
                """INSERT INTO five_view_outputs
                   (attempt_id, direction, image_path, sha256, status, guidance)
                   VALUES ('FAKE-VIEW', ?, ?, ?, 'approved', '')""",
                (direction, str(path), hashlib.sha256(path.read_bytes()).hexdigest()),
            )

    result = container.delivery.assemble(job.project_id)

    assert (result.completed, result.missing, result.needs_review) == (1, 0, 0)
    assert (result.package_path / "buildings" / "B001" / "model" / "final" / "B001.fbx").is_file()
