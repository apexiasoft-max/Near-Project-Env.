"""Validated, explainable strategies for estimating building height."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from npe.domain.height import HeightEstimate, HeightMethod
from npe.infrastructure.database import Database


class HeightService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def from_floors(floors: int, floor_height_m: float = 3.0) -> HeightEstimate:
        if floors <= 0 or not 2.4 <= floor_height_m <= 5.0:
            raise ValueError("Invalid floor-count evidence")
        height = floors * floor_height_m
        uncertainty = floor_height_m
        return HeightEstimate(
            height, floors, height - uncertainty, height + uncertainty,
            HeightMethod.FLOOR_COUNT, 0.72,
            {"floors": floors, "floor_height_m": floor_height_m},
        )

    @staticmethod
    def from_calibrated_shadow(
        shadow_length_m: float, reference_shadow_m: float,
        reference_height_m: float, *, occluded: bool = False,
    ) -> HeightEstimate:
        if occluded:
            raise ValueError("Occluded shadow cannot produce a calibrated estimate")
        if min(shadow_length_m, reference_shadow_m, reference_height_m) <= 0:
            raise ValueError("Shadow calibration values must be positive")
        ratio = reference_height_m / reference_shadow_m
        height = shadow_length_m * ratio
        uncertainty = max(3.0, height * 0.18)
        return HeightEstimate(
            height, round(height / 3.0), max(0.1, height - uncertainty),
            height + uncertainty, HeightMethod.CALIBRATED_SHADOW, 0.65,
            {
                "shadow_length_m": shadow_length_m,
                "reference_shadow_m": reference_shadow_m,
                "reference_height_m": reference_height_m,
            },
        )

    @staticmethod
    def override(height_m: float, floors: int | None, reason: str) -> HeightEstimate:
        if height_m <= 0 or (floors is not None and floors <= 0) or not reason.strip():
            raise ValueError("Human override requires valid dimensions and a reason")
        return HeightEstimate(
            height_m, floors, height_m, height_m, HeightMethod.HUMAN_OVERRIDE, 1.0,
            {"reason": reason.strip()},
        )

    def apply(self, project_id: str, building_id: str, estimate: HeightEstimate) -> None:
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE buildings SET target_height_m = ?, floors = ?, height_min_m = ?,
                   height_max_m = ?, height_method = ?, height_confidence = ?,
                   height_evidence_json = ?, updated_at = ?
                   WHERE id = ? AND project_id = ? AND deleted_at IS NULL""",
                (
                    estimate.height_m, estimate.floors, estimate.minimum_m,
                    estimate.maximum_m, estimate.method, estimate.confidence,
                    json.dumps(estimate.evidence, sort_keys=True), now,
                    building_id, project_id,
                ),
            )
        if cursor.rowcount != 1:
            raise KeyError(building_id)

