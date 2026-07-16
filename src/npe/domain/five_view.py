"""Immutable inputs and outputs for five-view image generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

REQUIRED_DIRECTIONS: Final = ("front", "back", "left", "right", "top")


@dataclass(frozen=True)
class FiveViewRequest:
    project_id: str
    building_id: str
    reference_paths: tuple[Path, ...]
    target_height_m: float
    floors: int | None
    front_bearing_deg: float | None

    def validate(self) -> None:
        if not self.reference_paths:
            raise ValueError("At least one approved reference is required")
        if self.target_height_m <= 0:
            raise ValueError("Target height must be positive")
        if self.floors is not None and self.floors <= 0:
            raise ValueError("Floors must be positive")
        missing = [str(path) for path in self.reference_paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing reference files: {', '.join(missing)}")


@dataclass(frozen=True)
class GenerationResult:
    run_id: str
    attempt: int
    output_path: Path
    manifest_path: Path
    diagnostics_path: Path

