"""Reference ranking and persistence independent of imagery provider."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from uuid import uuid4

from npe.domain.inventory import LonLat, Polygon
from npe.domain.reference import RankedReference, ReferenceObservation
from npe.infrastructure.database import Database

EARTH_RADIUS_M = 6_371_008.8


class ReferenceService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def rank(
        self, building_id: str, footprint: Polygon,
        observations: list[ReferenceObservation],
    ) -> list[RankedReference]:
        if len(footprint) < 3:
            raise ValueError("Building footprint requires at least three vertices")
        ranked = [self._score(footprint, observation) for observation in observations]
        ranked.sort(key=lambda item: (-item.total_score, item.observation.source_id))
        self._persist(building_id, ranked)
        return ranked

    @classmethod
    def _score(
        cls, footprint: Polygon, observation: ReferenceObservation
    ) -> RankedReference:
        if observation.width_px <= 0 or observation.height_px <= 0:
            raise ValueError("Reference resolution must be positive")
        if not 0 <= observation.visibility <= 1 or not 0 <= observation.occlusion <= 1:
            raise ValueError("Visibility and occlusion must be in [0, 1]")
        centroid = (
            sum(point[0] for point in footprint) / len(footprint),
            sum(point[1] for point in footprint) / len(footprint),
        )
        distance_m: float | None = None
        angle_error: float | None = None
        if observation.camera is not None:
            distance_m = cls._distance(observation.camera, centroid)
        if observation.camera is not None and observation.heading_deg is not None:
            target_bearing = cls._bearing(observation.camera, centroid)
            angle_error = abs((observation.heading_deg - target_bearing + 180) % 360 - 180)
        fov = observation.horizontal_fov_deg or 90.0
        angle_score = 0.35 if angle_error is None else max(0.0, 1.0 - angle_error / (fov / 2))
        distance_score = 0.4 if distance_m is None else max(0.0, 1.0 - distance_m / 120.0)
        attribution = 0.7 * angle_score + 0.3 * distance_score
        pixels = observation.width_px * observation.height_px
        resolution_score = min(1.0, pixels / (1920 * 1080))
        quality = (
            0.35 * resolution_score
            + 0.4 * observation.visibility
            + 0.25 * (1.0 - observation.occlusion)
        )
        total = 0.55 * attribution + 0.45 * quality
        evidence: dict[str, float | str | None] = {
            "provider": observation.provider,
            "distance_m": distance_m,
            "angle_error_deg": angle_error,
            "angle_score": angle_score,
            "distance_score": distance_score,
            "resolution_score": resolution_score,
            "visibility": observation.visibility,
            "occlusion": observation.occlusion,
        }
        return RankedReference(
            observation, round(attribution, 6), round(quality, 6),
            round(total, 6), evidence,
        )

    def _persist(self, building_id: str, ranked: list[RankedReference]) -> None:
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            building = connection.execute(
                "SELECT 1 FROM buildings WHERE id = ? AND deleted_at IS NULL", (building_id,)
            ).fetchone()
            if building is None:
                raise KeyError(building_id)
            connection.execute(
                "UPDATE reference_candidates SET active = 0 WHERE building_id = ?",
                (building_id,),
            )
            for rank, item in enumerate(ranked, start=1):
                observation = item.observation
                connection.execute(
                    """INSERT INTO reference_candidates
                       (id, building_id, provider, source_id, image_path, captured_at,
                        camera_lon, camera_lat, heading_deg, fov_deg, width_px, height_px,
                        visibility, occlusion, attribution_score, quality_score, total_score,
                        rank, evidence_json, metadata_json, active, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                    (
                        f"REF-{uuid4().hex[:10].upper()}", building_id,
                        observation.provider, observation.source_id,
                        str(observation.image_path), observation.captured_at,
                        observation.camera[0] if observation.camera else None,
                        observation.camera[1] if observation.camera else None,
                        observation.heading_deg, observation.horizontal_fov_deg,
                        observation.width_px, observation.height_px,
                        observation.visibility, observation.occlusion,
                        item.attribution_score, item.quality_score, item.total_score, rank,
                        json.dumps(item.evidence, sort_keys=True),
                        json.dumps(observation.metadata, sort_keys=True), now,
                    ),
                )

    @staticmethod
    def _distance(first: LonLat, second: LonLat) -> float:
        lon1, lat1 = map(math.radians, first)
        lon2, lat2 = map(math.radians, second)
        dlon, dlat = lon2 - lon1, lat2 - lat1
        value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))

    @staticmethod
    def _bearing(first: LonLat, second: LonLat) -> float:
        lon1, lat1 = map(math.radians, first)
        lon2, lat2 = map(math.radians, second)
        y = math.sin(lon2 - lon1) * math.cos(lat2)
        x = (
            math.cos(lat1) * math.sin(lat2)
            - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        )
        return (math.degrees(math.atan2(y, x)) + 360) % 360
