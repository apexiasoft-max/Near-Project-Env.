from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import QApplication, QTableWidget

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
