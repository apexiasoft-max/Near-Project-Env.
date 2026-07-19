from __future__ import annotations

from pathlib import Path

import pytest

from npe.bootstrap import bootstrap
from npe.domain.project import ProjectStatus
from npe.shared.config import AppPaths, Settings


def ready_settings(root: Path) -> Settings:
    blender = root / "blender.exe"
    blender.parent.mkdir(parents=True, exist_ok=True)
    blender.write_bytes(b"fixture")
    return Settings(
        paths=AppPaths.under(root / "data"),
        minimum_free_disk_bytes=0,
        blender_path=blender,
    )


def test_lifecycle_survives_restart_and_dashboard_counts_jobs(tmp_path: Path) -> None:
    settings = ready_settings(tmp_path)
    container = bootstrap(settings)
    job = container.workflow.create_job(
        "Tehran", 35.7, 51.4, 200, "B001", 24, tmp_path / "output"
    )
    project = container.lifecycle.get_project(job.project_id)
    assert project.status == ProjectStatus.DRAFT
    assert project.building_count == 1
    assert project.total_jobs == 1

    assert container.lifecycle.start(project.id).status == ProjectStatus.RUNNING
    assert container.lifecycle.pause(project.id).status == ProjectStatus.PAUSED

    restarted = bootstrap(settings)
    recovered = restarted.lifecycle.get_project(project.id)
    assert recovered.status == ProjectStatus.PAUSED
    assert restarted.lifecycle.resume(project.id).status == ProjectStatus.RUNNING
    assert restarted.lifecycle.cancel(project.id).status == ProjectStatus.CANCELLED

    with pytest.raises(ValueError, match="Invalid project transition"):
        restarted.lifecycle.resume(project.id)


def test_preflight_explains_missing_required_dependency(tmp_path: Path) -> None:
    settings = Settings(
        paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=10**30
    )
    container = bootstrap(settings)
    job = container.workflow.create_job("P", 35.7, 51.4, 100, "B1", 12)

    with pytest.raises(RuntimeError, match="Preflight failed: disk"):
        container.lifecycle.start(job.project_id)


def test_project_input_validation_happens_before_persistence(tmp_path: Path) -> None:
    container = bootstrap(ready_settings(tmp_path))

    with pytest.raises(ValueError, match="Project name is required"):
        container.workflow.create_job("  ", 35.7, 51.4, 100, "B1", 12)
    with pytest.raises(ValueError, match="Radius"):
        container.workflow.create_job("P", 35.7, 51.4, 201, "B1", 12)
    assert container.lifecycle.list_projects() == []


def test_project_can_be_created_without_modeling_the_unbuilt_main_building(
    tmp_path: Path,
) -> None:
    container = bootstrap(ready_settings(tmp_path))
    project = container.lifecycle.create("Mezo", 35.7849298, 51.3730481, 200)
    assert project.building_count == 0
    assert project.total_jobs == 0
    with container.database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM buildings WHERE project_id = ?", (project.id,)
        ).fetchone()[0] == 0
