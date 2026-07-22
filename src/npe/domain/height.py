"""Explainable height estimates and evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HeightMethod(StrEnum):
    FLOOR_COUNT = "floor_count"
    CALIBRATED_SHADOW = "calibrated_shadow"
    AERIAL_RELATIVE = "aerial_relative"
    HUMAN_OVERRIDE = "human_override"


@dataclass(frozen=True)
class HeightEstimate:
    height_m: float
    floors: int | None
    minimum_m: float
    maximum_m: float
    method: HeightMethod
    confidence: float
    evidence: dict[str, object]
