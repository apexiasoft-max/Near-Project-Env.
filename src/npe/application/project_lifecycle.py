"""Persistent project lifecycle commands and dashboard query."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from npe.application.health import HealthService
from npe.domain.project import (
    ProjectStatus,
    ProjectSummary,
    ensure_project_transition,
    validate_project_input,
)
from npe.infrastructure.database import Database


@dataclass(frozen=True)
class PreflightCheck:
    component: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PreflightResult:
    passed: bool
    checks: tuple[PreflightCheck, ...]

    @property
    def failure_message(self) -> str:
        failures = [f"{item.component}: {item.detail}" for item in self.checks if not item.passed]
        return "; ".join(failures)


class ProjectLifecycleService:
    def __init__(self, database: Database, health: HealthService) -> None:
        self.database = database
        self.health = health

    def preflight(self) -> PreflightResult:
        report = self.health.inspect()
        required = {
            "database": report.database,
            "disk": report.disk,
            "browser": report.browser,
            "blender": report.blender,
        }
        checks = tuple(
            PreflightCheck(name, value.status == "ok", value.detail)
            for name, value in required.items()
        )
        return PreflightResult(all(item.passed for item in checks), checks)

    def create(
        self,
        name: str,
        latitude: float,
        longitude: float,
        radius_m: int,
        output_path: Path | None = None,
    ) -> ProjectSummary:
        project_id = f"PRJ-{uuid4().hex[:8].upper()}"
        resolved_output = (
            output_path.expanduser().resolve()
            if output_path is not None
            else (self.health.settings.paths.projects / project_id).resolve()
        )
        validate_project_input(name, latitude, longitude, radius_m, resolved_output)
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO projects
                   (id, name, latitude, longitude, radius_m, status, created_at, updated_at,
                    output_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, name.strip(), latitude, longitude, radius_m,
                    ProjectStatus.DRAFT, now, now, str(resolved_output),
                ),
            )
        return self.get_project(project_id)

    def start(self, project_id: str) -> ProjectSummary:
        result = self.preflight()
        if not result.passed:
            raise RuntimeError(f"Preflight failed: {result.failure_message}")
        return self._transition(project_id, ProjectStatus.RUNNING)

    def pause(self, project_id: str) -> ProjectSummary:
        return self._transition(project_id, ProjectStatus.PAUSED)

    def resume(self, project_id: str) -> ProjectSummary:
        result = self.preflight()
        if not result.passed:
            raise RuntimeError(f"Preflight failed: {result.failure_message}")
        return self._transition(project_id, ProjectStatus.RUNNING)

    def cancel(self, project_id: str) -> ProjectSummary:
        return self._transition(project_id, ProjectStatus.CANCELLED)

    def complete(self, project_id: str) -> ProjectSummary:
        return self._transition(project_id, ProjectStatus.COMPLETED)

    def list_projects(self) -> list[ProjectSummary]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT p.*, COUNT(DISTINCT b.id) AS building_count,
                       COUNT(DISTINCT CASE WHEN j.stage = 'completed' THEN j.id END)
                           AS completed_jobs,
                       COUNT(DISTINCT j.id) AS total_jobs
                FROM projects p
                LEFT JOIN buildings b ON b.project_id = p.id
                LEFT JOIN jobs j ON j.project_id = p.id
                GROUP BY p.id
                ORDER BY p.created_at DESC
                """
            ).fetchall()
        return [self._summary(row) for row in rows]

    def get_project(self, project_id: str) -> ProjectSummary:
        projects = {item.id: item for item in self.list_projects()}
        if project_id not in projects:
            raise KeyError(project_id)
        return projects[project_id]

    def _transition(self, project_id: str, target: ProjectStatus) -> ProjectSummary:
        current = self.get_project(project_id)
        ensure_project_transition(current.status, target)
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
                (target, datetime.now(UTC).isoformat(), project_id),
            )
        return self.get_project(project_id)

    @staticmethod
    def _summary(row: sqlite3.Row) -> ProjectSummary:
        values = dict(row)
        return ProjectSummary(
            id=str(values["id"]),
            name=str(values["name"]),
            latitude=float(values["latitude"]),
            longitude=float(values["longitude"]),
            radius_m=int(values["radius_m"]),
            output_path=Path(str(values["output_path"])),
            status=ProjectStatus(str(values["status"])),
            building_count=int(values["building_count"]),
            completed_jobs=int(values["completed_jobs"]),
            total_jobs=int(values["total_jobs"]),
        )
