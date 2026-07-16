"""Five-view review snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ViewOutput:
    direction: str
    image_path: Path
    sha256: str
    status: str
    guidance: str


@dataclass(frozen=True)
class ViewAttempt:
    id: str
    project_id: str
    building_id: str
    run_id: str
    version: int
    status: str
    outputs: tuple[ViewOutput, ...]
    parent_attempt_id: str | None = None

