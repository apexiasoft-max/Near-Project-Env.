from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from npe.application.delivery import DeliveryMetrics
from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings


def _container(tmp_path: Path):  # type: ignore[no-untyped-def]
    return bootstrap(Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0))


def _file(path: Path, content: bytes = b"artifact-data-that-is-not-empty") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _complete_building(container, tmp_path: Path):  # type: ignore[no-untyped-def]
    job = container.workflow.create_job("Typical Tehran <site>", 35.75, 51.4, 200, "B001", 21)
    reference = _file(tmp_path / "source" / "street.jpg")
    raw = _file(tmp_path / "source" / "raw.glb")
    final = _file(tmp_path / "source" / "final.fbx")
    views = {
        name: _file(tmp_path / "source" / f"{name}.png", f"image-{name}".encode())
        for name in ("front", "back", "left", "right", "top")
    }
    now = datetime.now(UTC).isoformat()
    with container.database.connect() as connection:
        connection.execute(
            """UPDATE jobs SET downloaded_model_path = ?, final_fbx_path = ?,
               stage = 'completed', status = 'completed' WHERE id = ?""",
            (str(raw), str(final), job.id),
        )
        connection.execute(
            """INSERT INTO reference_candidates
               (id, building_id, provider, source_id, image_path, width_px, height_px,
                visibility, occlusion, attribution_score, quality_score, total_score, rank,
                evidence_json, metadata_json, active, selected, rejected, created_at)
               VALUES ('REF-1', ?, 'google', 'source-1', ?, 1280, 720, 1, 0, 1, 1, 1,
                       1, '{}', '{}', 1, 1, 0, ?)""",
            (job.building_id, str(reference), now),
        )
        connection.execute(
            """INSERT INTO five_view_attempts
               (id, project_id, building_id, run_id, version, status, guidance_json, created_at)
               VALUES ('VIEW-1', ?, ?, ?, 1, 'approved', '{}', ?)""",
            (job.project_id, job.building_id, job.run_id, now),
        )
        for direction, path in views.items():
            connection.execute(
                """INSERT INTO five_view_outputs
                   (attempt_id, direction, image_path, sha256, status, guidance)
                   VALUES ('VIEW-1', ?, ?, ?, 'approved', '')""",
                (direction, str(path), hashlib.sha256(path.read_bytes()).hexdigest()),
            )
    inventory = container.settings.paths.projects / job.project_id / "inventory"
    inventory.mkdir(parents=True)
    Image.new("RGB", (32, 32), "gray").save(inventory / "aerial_original.jpg")
    Image.new("RGB", (32, 32), "gray").save(inventory / "aerial_coded.png")
    return job


def test_assembles_traceable_delivery_and_is_repeatable(tmp_path: Path) -> None:
    container = _container(tmp_path)
    job = _complete_building(container, tmp_path)

    result = container.delivery.assemble(
        job.project_id,
        metrics=DeliveryMetrics(runtime_seconds=90, active_human_minutes=4, error_count=0),
    )

    assert (result.building_count, result.completed, result.completion_rate) == (1, 1, 1)
    building = result.package_path / "buildings" / "B001"
    assert (building / "model" / "raw" / "B001.glb").is_file()
    assert (building / "model" / "final" / "B001.fbx").is_file()
    assert len(list((building / "generated" / "approved").glob("*.png"))) == 5
    manifest = json.loads((building / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["artifacts"]) == 8
    for artifact in manifest["artifacts"]:
        path = result.package_path / artifact["relative_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
        assert path.stat().st_size == artifact["size_bytes"]
        assert artifact["project_id"] == job.project_id
    report = (result.package_path / "reports" / "process_report.html").read_text()
    assert "Typical Tehran &lt;site&gt;" in report
    assert "Completed: 1/1" in report
    package_manifest = json.loads(
        (result.package_path / "package_manifest.json").read_text(encoding="utf-8")
    )
    assert {item["relative_path"] for item in package_manifest["files"]} >= {
        "overview/aerial_coded.png", "reports/process_report.html", "buildings/B001/metadata.json"
    }

    second = container.delivery.assemble(job.project_id)
    assert second.package_path == result.package_path
    assert not list(result.package_path.parent.glob(".delivery.partial-*"))


def test_incomplete_building_is_isolated_and_reported(tmp_path: Path) -> None:
    container = _container(tmp_path)
    job = _complete_building(container, tmp_path)
    now = datetime.now(UTC).isoformat()
    with container.database.connect() as connection:
        connection.execute(
            """INSERT INTO buildings
               (id, project_id, code, target_height_m, status, created_at, updated_at)
               VALUES ('BLD-2', ?, 'B002', 12, 'needs_review', ?, ?)""",
            (job.project_id, now, now),
        )

    result = container.delivery.assemble(job.project_id)

    assert (result.completed, result.needs_review, result.missing) == (1, 1, 0)
    with (result.package_path / "overview" / "buildings.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["code"], row["status"]) for row in rows] == [
        ("B001", "Completed"), ("B002", "NeedsReview")
    ]


def test_rejects_unsafe_destination_and_building_code(tmp_path: Path) -> None:
    container = _container(tmp_path)
    job = container.workflow.create_job("Unsafe", 35.75, 51.4, 100, "../escape", 10)
    with pytest.raises(ValueError, match="projects root"):
        container.delivery.assemble(job.project_id, destination=tmp_path / "outside")
    with pytest.raises(ValueError, match="Unsafe building code"):
        container.delivery.assemble(job.project_id)
