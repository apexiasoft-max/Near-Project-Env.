"""Minimal Sprint 1 desktop shell."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Any

from npe.application.workflow import VIEW_NAMES, BlenderNormalizer
from npe.bootstrap import Container, bootstrap


def normalizer_script_path() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(str(bundle_root)) / "tools" / "normalize_model_fbx.py"
    return Path(__file__).resolve().parents[3] / "spikes/sprint0/scripts/normalize_model_fbx.py"


def create_window(container: Container) -> Any:
    from PySide6.QtWidgets import (
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QSpinBox,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Near Project Environment")
            self.resize(880, 560)
            root = QWidget()
            layout = QVBoxLayout(root)
            form = QFormLayout()
            self.project_name = QLineEdit("Tehran project")
            self.latitude = QDoubleSpinBox()
            self.latitude.setRange(-90, 90)
            self.latitude.setDecimals(6)
            self.longitude = QDoubleSpinBox()
            self.longitude.setRange(-180, 180)
            self.longitude.setDecimals(6)
            self.radius = QSpinBox()
            self.radius.setRange(1, 200)
            self.radius.setValue(200)
            self.building_code = QLineEdit("B001")
            self.height_input = QDoubleSpinBox()
            self.height_input.setRange(1, 1000)
            self.height_input.setValue(15)
            fields = (
                ("Project", self.project_name),
                ("Latitude", self.latitude),
                ("Longitude", self.longitude),
                ("Radius (m)", self.radius),
                ("Building", self.building_code),
                ("Height (m)", self.height_input),
            )
            for label, widget in fields:
                form.addRow(label, widget)
            layout.addLayout(form)
            create = QPushButton("Create Project + Building Job")
            create.clicked.connect(self.create_job)
            layout.addWidget(create)
            self.job_status = QLabel("No job created")
            layout.addWidget(self.job_status)
            self.active_run_id: str | None = None
            self.view_paths: dict[str, Path] = {}
            for view_name in VIEW_NAMES:
                button = QPushButton(f"Select {view_name.title()} image")
                button.clicked.connect(
                    lambda _checked=False, name=view_name: self.select_view(name)
                )
                layout.addWidget(button)
            attach = QPushButton("Approve Five Views")
            attach.clicked.connect(self.attach_views)
            layout.addWidget(attach)
            open_hunyuan = QPushButton("Open Hunyuan")
            open_hunyuan.clicked.connect(self.open_hunyuan)
            layout.addWidget(open_hunyuan)
            confirm_submit = QPushButton("Confirm Hunyuan Submission")
            confirm_submit.clicked.connect(self.confirm_hunyuan_submission)
            layout.addWidget(confirm_submit)
            download = QPushButton("Register Downloaded Model + Build FBX")
            download.clicked.connect(self.register_model)
            layout.addWidget(download)
            layout.addWidget(QLabel("System Health"))
            self.table = QTableWidget(5, 3)
            self.table.setHorizontalHeaderLabels(["Component", "Status", "Detail"])
            layout.addWidget(self.table)
            refresh = QPushButton("Refresh Health")
            refresh.clicked.connect(self.refresh_health)
            layout.addWidget(refresh)
            self.setCentralWidget(root)
            self.refresh_health()

        def create_job(self) -> None:
            job = container.workflow.create_job(
                self.project_name.text(), self.latitude.value(), self.longitude.value(),
                self.radius.value(), self.building_code.text(), self.height_input.value(),
            )
            self.job_status.setText(f"{job.run_id}: {job.stage}")
            self.active_run_id = job.run_id

        def select_view(self, name: str) -> None:
            selected, _ = QFileDialog.getOpenFileName(
                self, f"Select {name} image", "", "Images (*.png *.jpg *.jpeg *.webp)"
            )
            if selected:
                self.view_paths[name] = Path(selected)
                self.job_status.setText(f"Selected {len(self.view_paths)}/5 views")

        def attach_views(self) -> None:
            if self.active_run_id is None:
                self.job_status.setText("Create a job first")
                return
            try:
                job = container.workflow.attach_views(self.active_run_id, self.view_paths)
                self.job_status.setText(f"{job.run_id}: {job.stage}")
            except (ValueError, FileNotFoundError) as error:
                self.job_status.setText(str(error))

        def open_hunyuan(self) -> None:
            if self.active_run_id is None:
                self.job_status.setText("Create a job first")
                return
            job = container.workflow.get_job(self.active_run_id)
            if job.stage.value != "ready_for_hunyuan":
                self.job_status.setText("Approve five views before opening Hunyuan")
                return
            webbrowser.open_new_tab("https://3d.hunyuanglobal.com/")
            self.job_status.setText(f"{job.run_id}: Hunyuan opened; submission not confirmed")

        def confirm_hunyuan_submission(self) -> None:
            if self.active_run_id is None:
                self.job_status.setText("Create a job first")
                return
            try:
                job = container.workflow.mark_submitted(self.active_run_id)
                self.job_status.setText(f"{job.run_id}: {job.stage}; other jobs may continue")
            except ValueError as error:
                self.job_status.setText(str(error))

        def register_model(self) -> None:
            if self.active_run_id is None:
                self.job_status.setText("Create a job first")
                return
            selected, _ = QFileDialog.getOpenFileName(
                self, "Select downloaded model", "", "3D models (*.fbx *.glb *.gltf)"
            )
            if not selected:
                return
            try:
                job = container.workflow.register_download(
                    self.active_run_id, Path(selected)
                )
                blender = container.health.inspect().blender
                if blender.status != "ok":
                    self.job_status.setText(f"{job.run_id}: model saved; Blender unavailable")
                    return
                job = container.workflow.normalize(
                    self.active_run_id,
                    BlenderNormalizer(Path(blender.detail), normalizer_script_path()),
                )
                self.job_status.setText(f"Completed: {job.final_fbx_path}")
            except (ValueError, FileNotFoundError, RuntimeError) as error:
                self.job_status.setText(str(error))

        def refresh_health(self) -> None:
            report = container.health.inspect().to_dict()
            for row, component in enumerate(
                ("database", "disk", "worker", "browser", "blender")
            ):
                value = report[component]
                assert isinstance(value, dict)
                self.table.setItem(row, 0, QTableWidgetItem(component.title()))
                self.table.setItem(row, 1, QTableWidgetItem(str(value["status"])))
                self.table.setItem(row, 2, QTableWidgetItem(str(value["detail"])))

    return MainWindow()


def main() -> None:
    from PySide6.QtWidgets import QApplication

    application = QApplication([])
    window = create_window(bootstrap())
    window.show()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()
