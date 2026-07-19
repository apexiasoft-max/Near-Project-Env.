"""Minimal Sprint 1 desktop shell."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from npe.application.workflow import VIEW_NAMES, BlenderNormalizer
from npe.bootstrap import Container, bootstrap
from npe.domain.approval import ApprovalGate


def normalizer_script_path() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(str(bundle_root)) / "tools" / "normalize_model_fbx.py"
    return Path(__file__).resolve().parents[3] / "spikes/sprint0/scripts/normalize_model_fbx.py"


def create_window(container: Container) -> Any:
    from PySide6.QtWidgets import (
        QComboBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QScrollArea,
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
            self.output_path = QLineEdit(str(container.settings.paths.projects))
            fields = (
                ("Project", self.project_name),
                ("Latitude", self.latitude),
                ("Longitude", self.longitude),
                ("Radius (m)", self.radius),
                ("Output path", self.output_path),
            )
            for label, widget in fields:
                form.addRow(label, widget)
            layout.addLayout(form)
            create = QPushButton("Create Project")
            create.clicked.connect(self.create_project)
            layout.addWidget(create)
            self.job_status = QLabel("No job created")
            layout.addWidget(self.job_status)
            self.active_run_id: str | None = None
            self.active_project_id: str | None = None
            self.active_building_id: str | None = None
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
            automate_hunyuan = QPushButton("Upload Views + Start Hunyuan")
            automate_hunyuan.clicked.connect(self.automate_hunyuan)
            layout.addWidget(automate_hunyuan)
            confirm_submit = QPushButton("Confirm Hunyuan Submission")
            confirm_submit.clicked.connect(self.confirm_hunyuan_submission)
            layout.addWidget(confirm_submit)
            download = QPushButton("Register Downloaded Model + Build FBX")
            download.clicked.connect(self.register_model)
            layout.addWidget(download)
            lifecycle_buttons = (
                ("Start Project", "start"),
                ("Pause Project", "pause"),
                ("Resume Project", "resume"),
                ("Cancel Project", "cancel"),
            )
            for label, command in lifecycle_buttons:
                button = QPushButton(label)
                button.clicked.connect(
                    lambda _checked=False, value=command: self.project_command(value)
                )
                layout.addWidget(button)
            layout.addWidget(QLabel("Project Dashboard"))
            self.project_table = QTableWidget(0, 6)
            self.project_table.setObjectName("projectDashboard")
            self.project_table.setHorizontalHeaderLabels(
                ["Project", "Status", "Buildings", "Jobs", "Completed", "Output"]
            )
            layout.addWidget(self.project_table)
            self.approval_comment = QLineEdit()
            self.approval_comment.setPlaceholderText("Approval comment")
            layout.addWidget(self.approval_comment)
            for label, gate in (
                ("Approve Map Snapshot", ApprovalGate.MAP),
                ("Approve Reference Snapshot", ApprovalGate.REFERENCE),
                ("Approve Five-View Snapshot", ApprovalGate.VIEW),
            ):
                button = QPushButton(label)
                button.clicked.connect(
                    lambda _checked=False, value=gate: self.approve_current(value)
                )
                layout.addWidget(button)
            self.audit_table = QTableWidget(0, 4)
            self.audit_table.setHorizontalHeaderLabels(
                ["Time", "Actor", "Event", "Comment"]
            )
            layout.addWidget(self.audit_table)
            layout.addWidget(QLabel("Reference Review"))
            self.reference_preview = QLabel("Select a reference candidate")
            self.reference_preview.setObjectName("referencePreview")
            self.reference_preview.setMinimumHeight(180)
            self.reference_preview.setScaledContents(False)
            layout.addWidget(self.reference_preview)
            self.reference_table = QTableWidget(0, 6)
            self.reference_table.setObjectName("referenceCandidateTable")
            self.reference_table.setHorizontalHeaderLabels(
                ["Provider", "Source", "Attribution", "Quality", "Total", "Status"]
            )
            self.reference_table.cellClicked.connect(self.preview_reference)
            layout.addWidget(self.reference_table)
            reference_actions = QHBoxLayout()
            for label, action in (
                ("Refresh Candidates", self.refresh_references),
                ("Select Candidate", self.select_reference),
                ("Reject Candidate", self.reject_reference),
                ("Upload Replacement", self.upload_reference),
                ("Mark Missing", self.mark_reference_missing),
                ("Approve Reference", self.approve_reference),
            ):
                button = QPushButton(label)
                button.setObjectName(action.__name__)
                button.clicked.connect(action)
                reference_actions.addWidget(button)
            layout.addLayout(reference_actions)
            self.reference_candidate_ids: list[str] = []
            layout.addWidget(QLabel("Five-View Review"))
            view_comparison = QHBoxLayout()
            self.generated_view_previews: dict[str, QLabel] = {}
            for direction in VIEW_NAMES:
                preview = QLabel(direction.upper())
                preview.setObjectName(f"generatedView{direction.title()}")
                preview.setMinimumSize(130, 180)
                preview.setScaledContents(True)
                self.generated_view_previews[direction] = preview
                view_comparison.addWidget(preview)
            layout.addLayout(view_comparison)
            self.revision_direction = QComboBox()
            self.revision_direction.addItems(["entire set", *VIEW_NAMES])
            layout.addWidget(self.revision_direction)
            self.revision_guidance = QLineEdit()
            self.revision_guidance.setPlaceholderText("Required revision guidance")
            layout.addWidget(self.revision_guidance)
            generated_actions = QHBoxLayout()
            for label, action in (
                ("Refresh Five Views", self.refresh_generated_views),
                ("Request Revision", self.request_view_revision),
                ("Approve Five-View Set", self.approve_generated_views),
            ):
                button = QPushButton(label)
                button.setObjectName(action.__name__)
                button.clicked.connect(action)
                generated_actions.addWidget(button)
            layout.addLayout(generated_actions)
            self.active_view_attempt_id: str | None = None
            layout.addWidget(QLabel("System Health"))
            self.table = QTableWidget(5, 3)
            self.table.setObjectName("healthTable")
            self.table.setHorizontalHeaderLabels(["Component", "Status", "Detail"])
            layout.addWidget(self.table)
            refresh = QPushButton("Refresh Health")
            refresh.clicked.connect(self.refresh_health)
            layout.addWidget(refresh)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(root)
            self.setCentralWidget(scroll)
            self.refresh_health()
            self.refresh_dashboard()

        def create_project(self) -> None:
            project = container.lifecycle.create(
                self.project_name.text(), self.latitude.value(), self.longitude.value(),
                self.radius.value(), Path(self.output_path.text()),
            )
            self.job_status.setText(f"{project.id}: {project.status}")
            self.active_run_id = None
            self.active_project_id = project.id
            self.active_building_id = None
            self.refresh_dashboard()

        def approve_current(self, gate: ApprovalGate) -> None:
            if self.active_project_id is None:
                self.job_status.setText("Select or create a project first")
                return
            building_id = None if gate == ApprovalGate.MAP else self.active_building_id
            if gate != ApprovalGate.MAP and building_id is None:
                self.job_status.setText("Select or create a building first")
                return
            payload: dict[str, object]
            if gate == ApprovalGate.MAP:
                payload = {
                    "latitude": self.latitude.value(),
                    "longitude": self.longitude.value(),
                    "radius_m": self.radius.value(),
                    "output_path": self.output_path.text(),
                }
            elif gate == ApprovalGate.REFERENCE:
                payload = {name: str(path) for name, path in self.view_paths.items()}
            else:
                if self.active_run_id is None:
                    self.job_status.setText("No active Run")
                    return
                job = container.workflow.get_job(self.active_run_id)
                if job.input_manifest is None:
                    self.job_status.setText("Approve five views before snapshotting them")
                    return
                payload = json.loads(job.input_manifest.read_text(encoding="utf-8"))
            try:
                revision = container.approvals.create_revision(
                    self.active_project_id, gate, payload, "local-operator",
                    self.approval_comment.text(), building_id,
                )
                approval = container.approvals.approve(
                    revision.id, "local-operator", self.approval_comment.text()
                )
                self.job_status.setText(f"Approved {gate}: {approval.id}")
                self.refresh_audit()
            except (KeyError, ValueError) as error:
                self.job_status.setText(str(error))

        def refresh_audit(self) -> None:
            if self.active_project_id is None:
                self.audit_table.setRowCount(0)
                return
            events = container.approvals.audit_timeline(self.active_project_id)
            self.audit_table.setRowCount(len(events))
            for row, event in enumerate(events):
                for column, value in enumerate(
                    (event.created_at, event.actor, event.event_type, event.comment)
                ):
                    self.audit_table.setItem(row, column, QTableWidgetItem(value))

        def refresh_references(self) -> None:
            if self.active_project_id is None or self.active_building_id is None:
                self.reference_table.setRowCount(0)
                self.reference_candidate_ids = []
                return
            candidates = container.reference_review.list_candidates(
                self.active_project_id, self.active_building_id
            )
            self.reference_candidate_ids = [item.id for item in candidates]
            self.reference_table.setRowCount(len(candidates))
            for row, item in enumerate(candidates):
                status = (
                    "Selected" if item.selected
                    else "Rejected" if item.rejected
                    else "Candidate"
                )
                values = (
                    item.provider, item.source_id, f"{item.attribution_score:.3f}",
                    f"{item.quality_score:.3f}", f"{item.total_score:.3f}", status,
                )
                for column, value in enumerate(values):
                    self.reference_table.setItem(row, column, QTableWidgetItem(str(value)))
            if candidates:
                self.reference_table.selectRow(0)
                self._show_reference(candidates[0].image_path)

        def preview_reference(self, row: int, _column: int) -> None:
            if not 0 <= row < len(self.reference_candidate_ids):
                return
            candidates = container.reference_review.list_candidates(
                self.active_project_id or "", self.active_building_id or ""
            )
            selected = next(
                (item for item in candidates if item.id == self.reference_candidate_ids[row]), None
            )
            if selected is not None:
                self._show_reference(selected.image_path)

        def _show_reference(self, path: Path) -> None:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QPixmap

            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self.reference_preview.setText(f"Image unavailable: {path}")
                return
            self.reference_preview.setPixmap(
                pixmap.scaled(
                    760, 260, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        def _selected_reference_id(self) -> str | None:
            row = self.reference_table.currentRow()
            if not 0 <= row < len(self.reference_candidate_ids):
                self.job_status.setText("Select a reference candidate first")
                return None
            return self.reference_candidate_ids[row]

        def select_reference(self) -> None:
            candidate_id = self._selected_reference_id()
            if (
                candidate_id is None
                or self.active_project_id is None
                or self.active_building_id is None
            ):
                return
            container.reference_review.select(
                self.active_project_id, self.active_building_id,
                candidate_id, "local-operator",
            )
            self.job_status.setText(f"Selected reference {candidate_id}")
            self.refresh_references()

        def reject_reference(self) -> None:
            candidate_id = self._selected_reference_id()
            if (
                candidate_id is None
                or self.active_project_id is None
                or self.active_building_id is None
            ):
                return
            container.reference_review.reject(
                self.active_project_id, self.active_building_id,
                candidate_id, "local-operator",
            )
            self.job_status.setText(f"Rejected reference {candidate_id}")
            self.refresh_references()

        def upload_reference(self) -> None:
            if self.active_project_id is None or self.active_building_id is None:
                self.job_status.setText("Select or create a building first")
                return
            selected, _ = QFileDialog.getOpenFileName(
                self, "Upload replacement reference", "", "Images (*.png *.jpg *.jpeg *.webp)"
            )
            if not selected:
                return
            candidate_id = container.reference_review.upload_replacement(
                self.active_project_id, self.active_building_id,
                Path(selected), "local-operator",
            )
            self.job_status.setText(f"Uploaded and selected {candidate_id}")
            self.refresh_references()

        def mark_reference_missing(self) -> None:
            if self.active_project_id is None or self.active_building_id is None:
                self.job_status.setText("Select or create a building first")
                return
            event_id = container.reference_review.mark_missing(
                self.active_project_id, self.active_building_id, "local-operator"
            )
            self.job_status.setText(f"MissingReference notification queued: {event_id}")

        def approve_reference(self) -> None:
            if self.active_project_id is None or self.active_building_id is None:
                self.job_status.setText("Select or create a building first")
                return
            try:
                approval = container.reference_review.approve(
                    self.active_project_id, self.active_building_id, "local-operator"
                )
                self.job_status.setText(f"Reference approved: {approval.id}")
                self.refresh_audit()
            except (KeyError, ValueError) as error:
                self.job_status.setText(str(error))

        def refresh_generated_views(self) -> None:
            if self.active_building_id is None:
                self.job_status.setText("Select or create a building first")
                return
            attempt = container.five_view_review.latest(self.active_building_id)
            if attempt is None:
                self.job_status.setText("No generated five-view attempt")
                return
            self.active_view_attempt_id = attempt.id
            from PySide6.QtGui import QPixmap

            for output in attempt.outputs:
                preview = self.generated_view_previews[output.direction]
                pixmap = QPixmap(str(output.image_path))
                if pixmap.isNull():
                    preview.setText(f"{output.direction.upper()} unavailable")
                else:
                    preview.setPixmap(pixmap)
            self.job_status.setText(f"Five-view attempt v{attempt.version}: {attempt.status}")

        def request_view_revision(self) -> None:
            if self.active_view_attempt_id is None:
                self.job_status.setText("Refresh and select a five-view attempt first")
                return
            direction = self.revision_direction.currentText()
            directions = None if direction == "entire set" else {direction}
            try:
                revision = container.five_view_review.request_revision(
                    self.active_view_attempt_id,
                    self.revision_guidance.text(),
                    directions,
                )
                self.active_view_attempt_id = revision.id
                self.job_status.setText(f"Revision v{revision.version} queued")
            except (KeyError, ValueError) as error:
                self.job_status.setText(str(error))

        def approve_generated_views(self) -> None:
            if self.active_view_attempt_id is None:
                self.job_status.setText("Refresh and select a five-view attempt first")
                return
            try:
                approved = container.five_view_review.approve(self.active_view_attempt_id)
                self.job_status.setText(
                    f"Five-view attempt v{approved.version} approved; Hunyuan unlocked"
                )
            except (KeyError, ValueError) as error:
                self.job_status.setText(str(error))

        def project_command(self, command: str) -> None:
            if self.active_project_id is None:
                self.job_status.setText("Select or create a project first")
                return
            action = getattr(container.lifecycle, command)
            try:
                project = action(self.active_project_id)
                self.job_status.setText(f"{project.id}: {project.status}")
                self.refresh_dashboard()
            except (RuntimeError, ValueError, KeyError) as error:
                self.job_status.setText(str(error))

        def refresh_dashboard(self) -> None:
            projects = container.lifecycle.list_projects()
            self.project_table.setRowCount(len(projects))
            for row, project in enumerate(projects):
                values = (
                    project.name,
                    project.status,
                    project.building_count,
                    project.total_jobs,
                    project.completed_jobs,
                    project.output_path,
                )
                for column, value in enumerate(values):
                    self.project_table.setItem(row, column, QTableWidgetItem(str(value)))
            if self.active_project_id is None and projects:
                self.active_project_id = projects[0].id
            self.refresh_audit()

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
            try:
                container.hunyuan.open()
                self.job_status.setText(
                    f"{job.run_id}: dedicated Hunyuan browser opened; submission not confirmed"
                )
            except RuntimeError as error:
                self.job_status.setText(str(error))

        def automate_hunyuan(self) -> None:
            if self.active_run_id is None:
                self.job_status.setText("Create a job first")
                return
            job = container.workflow.get_job(self.active_run_id)
            if job.stage.value != "ready_for_hunyuan" or job.input_manifest is None:
                self.job_status.setText("Approve five views before Hunyuan upload")
                return
            try:
                result = container.hunyuan.submit(
                    job.run_id, job.input_manifest.parent, minimum_views=3
                )
                if not result.generation_started:
                    self.job_status.setText(
                        f"{job.run_id}: {result.failure_code}; "
                        f"accepted {result.accepted_views}/5"
                    )
                    return
                job = container.workflow.mark_submitted(job.run_id)
                self.job_status.setText(
                    f"{job.run_id}: generation started with "
                    f"{result.accepted_views}/5 views; {job.stage}"
                )
            except (FileNotFoundError, RuntimeError, ValueError) as error:
                self.job_status.setText(str(error))

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
