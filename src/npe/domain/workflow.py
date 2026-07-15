"""Walking-skeleton workflow states and records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class JobStage(StrEnum):
    AWAITING_VIEWS = "awaiting_views"
    READY_FOR_HUNYUAN = "ready_for_hunyuan"
    AWAITING_MANUAL_DOWNLOAD = "awaiting_manual_download"
    NORMALIZING = "normalizing"
    COMPLETED = "completed"
    FAILED = "failed"


ALLOWED_TRANSITIONS: dict[JobStage, frozenset[JobStage]] = {
    JobStage.AWAITING_VIEWS: frozenset({JobStage.READY_FOR_HUNYUAN, JobStage.FAILED}),
    JobStage.READY_FOR_HUNYUAN: frozenset(
        {JobStage.AWAITING_MANUAL_DOWNLOAD, JobStage.FAILED}
    ),
    JobStage.AWAITING_MANUAL_DOWNLOAD: frozenset(
        {JobStage.NORMALIZING, JobStage.FAILED}
    ),
    JobStage.NORMALIZING: frozenset({JobStage.COMPLETED, JobStage.FAILED}),
    JobStage.COMPLETED: frozenset(),
    JobStage.FAILED: frozenset(),
}


@dataclass(frozen=True)
class Job:
    id: str
    project_id: str
    building_id: str
    run_id: str
    stage: JobStage
    input_manifest: Path | None
    downloaded_model_path: Path | None
    final_fbx_path: Path | None


def ensure_transition(current: JobStage, target: JobStage) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid job transition: {current} -> {target}")
