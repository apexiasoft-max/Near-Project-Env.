from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication, QLabel, QTableWidget

from npe.bootstrap import bootstrap
from npe.desktop.app import create_window
from npe.shared.config import AppPaths, Settings


def test_desktop_shell_renders_five_health_components(tmp_path: Path) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication([])
    container = bootstrap(Settings(paths=AppPaths.under(tmp_path), minimum_free_disk_bytes=0))
    window = create_window(container)
    table = window.findChild(QTableWidget, "healthTable")
    assert table is not None
    assert table.rowCount() == 5
    assert table.item(0, 0).text() == "Database"
    window.close()
    application.processEvents()


def test_dashboard_recovers_persisted_project_after_restart(tmp_path: Path) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication([])
    settings = Settings(paths=AppPaths.under(tmp_path), minimum_free_disk_bytes=0)
    first = bootstrap(settings)
    first.workflow.create_job("Recovered", 35.7, 51.4, 100, "B1", 12)

    window = create_window(bootstrap(settings))
    dashboard = window.findChild(QTableWidget, "projectDashboard")
    assert dashboard is not None
    assert dashboard.rowCount() == 1
    assert dashboard.item(0, 0).text() == "Recovered"
    assert dashboard.item(0, 1).text() == "draft"
    window.close()
    application.processEvents()


def test_reference_review_shows_scores_and_selects_candidate(tmp_path: Path) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication([])
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("References", 35.7, 51.4, 100, "B001", 12)
    replacement = tmp_path / "reference.png"
    Image.new("RGB", (640, 480), (90, 110, 120)).save(replacement)
    candidate_id = container.reference_review.upload_replacement(
        job.project_id, job.building_id, replacement, "fixture"
    )
    window = create_window(container)
    window.active_project_id = job.project_id
    window.active_building_id = job.building_id
    window.refresh_references()

    table = window.findChild(QTableWidget, "referenceCandidateTable")
    preview = window.findChild(QLabel, "referencePreview")
    assert table is not None and preview is not None
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "manual_pool"
    assert table.item(0, 5).text() == "Selected"
    assert window.reference_candidate_ids == [candidate_id]
    assert preview.pixmap() is not None

    window.reject_reference()
    assert table.item(0, 5).text() == "Rejected"
    window.select_reference()
    assert table.item(0, 5).text() == "Selected"
    window.close()
    application.processEvents()


def test_five_view_review_shows_all_directions_on_one_screen(tmp_path: Path) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication([])
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("Views", 35.7, 51.4, 100, "B001", 30)
    views: dict[str, Path] = {}
    for direction in ("front", "back", "left", "right", "top"):
        path = tmp_path / f"{direction}.png"
        Image.new("RGB", (300, 400), (90, 110, 120)).save(path)
        views[direction] = path
    lineage = tmp_path / "lineage.json"
    lineage.write_text("{}", encoding="utf-8")
    attempt = container.five_view_review.register(
        job.project_id, job.building_id, "RUN-UI", views, lineage
    )
    window = create_window(container)
    window.active_building_id = job.building_id

    window.refresh_generated_views()

    assert window.active_view_attempt_id == attempt.id
    for direction in views:
        preview = window.findChild(QLabel, f"generatedView{direction.title()}")
        assert preview is not None
        assert preview.pixmap() is not None
    window.close()
    application.processEvents()
