"""Project lifecycle domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


PROJECT_TRANSITIONS: dict[ProjectStatus, frozenset[ProjectStatus]] = {
    ProjectStatus.DRAFT: frozenset({ProjectStatus.RUNNING, ProjectStatus.CANCELLED}),
    ProjectStatus.RUNNING: frozenset(
        {ProjectStatus.PAUSED, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}
    ),
    ProjectStatus.PAUSED: frozenset({ProjectStatus.RUNNING, ProjectStatus.CANCELLED}),
    ProjectStatus.COMPLETED: frozenset(),
    ProjectStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class ProjectSummary:
    id: str
    name: str
    latitude: float
    longitude: float
    radius_m: int
    output_path: Path
    status: ProjectStatus
    building_count: int
    completed_jobs: int
    total_jobs: int


def ensure_project_transition(current: ProjectStatus, target: ProjectStatus) -> None:
    if target not in PROJECT_TRANSITIONS[current]:
        raise ValueError(f"Invalid project transition: {current} -> {target}")


def validate_project_input(
    name: str, latitude: float, longitude: float, radius_m: int, output_path: Path
) -> None:
    if not name.strip():
        raise ValueError("Project name is required")
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180")
    if not 1 <= radius_m <= 200:
        raise ValueError("Radius must be between 1 and 200 metres")
    if not output_path.is_absolute():
        raise ValueError("Output path must be absolute")
