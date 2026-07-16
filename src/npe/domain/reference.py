"""Provider-neutral reference observation and ranking models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from npe.domain.inventory import LonLat


class ReferenceProvider(StrEnum):
    GOOGLE = "google"
    NESHAN = "neshan"
    MANUAL_POOL = "manual_pool"


@dataclass(frozen=True)
class ReferenceObservation:
    provider: ReferenceProvider
    source_id: str
    image_path: Path
    captured_at: str | None
    camera: LonLat | None
    heading_deg: float | None
    horizontal_fov_deg: float | None
    width_px: int
    height_px: int
    visibility: float
    occlusion: float
    metadata: dict[str, object]


@dataclass(frozen=True)
class RankedReference:
    observation: ReferenceObservation
    attribution_score: float
    quality_score: float
    total_score: float
    evidence: dict[str, float | str | None]


@dataclass(frozen=True)
class ManualPoolItem:
    id: str
    project_id: str
    original_path: Path
    sha256: str
    width_px: int
    height_px: int
    style: str | None
    floors: int | None
    has_balcony: bool | None
    quality_score: float
