"""Aerial footprint filtering, stable coding and artifact export."""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from npe.application.approvals import ApprovalService
from npe.domain.approval import ApprovalGate, ApprovalSnapshot
from npe.domain.inventory import (
    AerialCoverage,
    FootprintCandidate,
    InventoryArtifacts,
    InventoryBuilding,
    LonLat,
    Polygon,
)
from npe.infrastructure.database import Database
from npe.shared.config import Settings

EARTH_RADIUS_M = 6_371_008.8


class InventoryService:
    def __init__(
        self, settings: Settings, database: Database,
        approvals: ApprovalService | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.approvals = approvals

    def list_buildings(self, project_id: str) -> list[InventoryBuilding]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM buildings WHERE project_id = ? AND deleted_at IS NULL
                   AND footprint_json IS NOT NULL ORDER BY code""",
                (project_id,),
            ).fetchall()
        return [self._building(row) for row in rows]

    def update_building(
        self, project_id: str, building_id: str, *, polygon: Polygon,
        floors: int | None, height_m: float, front_bearing_deg: float | None,
    ) -> InventoryBuilding:
        if len(polygon) < 3 or height_m <= 0 or (floors is not None and floors <= 0):
            raise ValueError("Invalid building geometry or dimensions")
        if front_bearing_deg is not None and not 0 <= front_bearing_deg < 360:
            raise ValueError("Front bearing must be in [0, 360)")
        center, radius_m = self._project_scope(project_id)
        boundary = self._boundary_state(center, radius_m, polygon)
        if boundary is None:
            raise ValueError("Building footprint does not intersect project radius")
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE buildings SET footprint_json = ?, floors = ?, target_height_m = ?,
                   front_bearing_deg = ?, boundary_intersection = ?, updated_at = ?
                   WHERE id = ? AND project_id = ? AND deleted_at IS NULL""",
                (
                    json.dumps(polygon, separators=(",", ":")), floors, height_m,
                    front_bearing_deg, int(boundary), now, building_id, project_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(building_id)
            row = connection.execute(
                "SELECT * FROM buildings WHERE id = ?", (building_id,)
            ).fetchone()
        assert row is not None
        return self._building(row)

    def soft_delete(self, project_id: str, building_id: str) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE buildings SET deleted_at = ?, status = 'deleted'
                   WHERE id = ? AND project_id = ? AND deleted_at IS NULL""",
                (datetime.now(UTC).isoformat(), building_id, project_id),
            )
        if cursor.rowcount != 1:
            raise KeyError(building_id)

    def approve(self, project_id: str, actor: str, comment: str = "") -> ApprovalSnapshot:
        if self.approvals is None:
            raise RuntimeError("Approval service is not configured")
        buildings = self.list_buildings(project_id)
        if not buildings:
            raise ValueError("Inventory has no active buildings")
        payload = {
            "buildings": [
                {
                    "id": item.id, "code": item.code, "polygon": item.polygon,
                    "boundary_intersection": item.boundary_intersection,
                    "floors": item.floors, "height_m": item.height_m,
                    "front_bearing_deg": item.front_bearing_deg,
                }
                for item in buildings
            ]
        }
        revision = self.approvals.create_revision(
            project_id, ApprovalGate.MAP, payload, actor, comment
        )
        return self.approvals.approve(revision.id, actor, comment)

    def build(
        self,
        project_id: str,
        coverage: AerialCoverage,
        candidates: list[FootprintCandidate],
    ) -> InventoryArtifacts:
        center, radius_m = self._project_scope(project_id)
        self._validate_coverage(center, radius_m, coverage)
        if not coverage.image_path.is_file():
            raise FileNotFoundError(coverage.image_path)
        included: list[tuple[FootprintCandidate, bool]] = []
        for candidate in candidates:
            boundary = self._boundary_state(center, radius_m, candidate.polygon)
            if boundary is not None:
                included.append((candidate, boundary))
        codes = self._allocate_codes(project_id, len(included))
        now = datetime.now(UTC).isoformat()
        buildings: list[InventoryBuilding] = []
        with self.database.connect() as connection:
            for code, (candidate, boundary) in zip(codes, included, strict=True):
                building_id = f"BLD-{uuid4().hex[:8].upper()}"
                height = candidate.height_m or ((candidate.floors or 1) * 3.0)
                polygon_json = json.dumps(candidate.polygon, separators=(",", ":"))
                connection.execute(
                    """INSERT INTO buildings
                       (id, project_id, code, target_height_m, status, created_at, updated_at,
                        footprint_json, floors, front_bearing_deg, boundary_intersection,
                        inventory_source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        building_id, project_id, code, height, "candidate", now, now,
                        polygon_json, candidate.floors, candidate.front_bearing_deg,
                        int(boundary), candidate.source,
                    ),
                )
                buildings.append(
                    InventoryBuilding(
                        building_id, project_id, code, candidate.polygon, boundary,
                        candidate.floors, height, candidate.front_bearing_deg, candidate.source,
                    )
                )
        root = self.settings.paths.projects / project_id / "inventory"
        root.mkdir(parents=True, exist_ok=True)
        original = root / f"aerial_original{coverage.image_path.suffix.lower()}"
        shutil.copy2(coverage.image_path, original)
        coded = root / "aerial_coded.png"
        geojson = root / "buildings.geojson"
        csv_path = root / "buildings.csv"
        self._render(coverage, buildings, coded)
        self._write_geojson(center, radius_m, buildings, geojson)
        self._write_csv(buildings, csv_path)
        return InventoryArtifacts(original, coded, geojson, csv_path, tuple(buildings))

    def _project_scope(self, project_id: str) -> tuple[LonLat, int]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT longitude, latitude, radius_m FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise KeyError(project_id)
        return (float(row[0]), float(row[1])), int(row[2])

    def _allocate_codes(self, project_id: str, count: int) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT code FROM buildings WHERE project_id = ?", (project_id,)
            ).fetchall()
        used = [
            int(match.group(1))
            for row in rows
            if (match := re.fullmatch(r"B(\d{3,})", str(row[0])))
        ]
        start = max(used, default=0) + 1
        return [f"B{number:03d}" for number in range(start, start + count)]

    @staticmethod
    def _validate_coverage(
        center: LonLat, radius_m: int, coverage: AerialCoverage
    ) -> None:
        lon, lat = center
        lat_delta = math.degrees(radius_m / EARTH_RADIUS_M)
        lon_delta = lat_delta / max(math.cos(math.radians(lat)), 1e-6)
        if not (
            coverage.west <= lon - lon_delta
            and coverage.east >= lon + lon_delta
            and coverage.south <= lat - lat_delta
            and coverage.north >= lat + lat_delta
        ):
            raise ValueError("Aerial coverage does not include the complete requested radius")

    @classmethod
    def _boundary_state(
        cls, center: LonLat, radius_m: int, polygon: Polygon
    ) -> bool | None:
        if len(polygon) < 3:
            raise ValueError("Footprint requires at least three vertices")
        points = [cls._local_meters(center, point) for point in polygon]
        inside = [math.hypot(x, y) <= radius_m for x, y in points]
        intersects = any(inside) or cls._point_in_polygon((0.0, 0.0), points)
        if not intersects:
            for first, second in zip(points, points[1:] + points[:1], strict=True):
                if cls._distance_to_segment((0.0, 0.0), first, second) <= radius_m:
                    intersects = True
                    break
        if not intersects:
            return None
        return not all(inside)

    @staticmethod
    def _local_meters(origin: LonLat, point: LonLat) -> tuple[float, float]:
        lon0, lat0 = origin
        lon, lat = point
        x = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
        y = math.radians(lat - lat0) * EARTH_RADIUS_M
        return x, y

    @staticmethod
    def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
        x, y = point
        inside = False
        previous = polygon[-1]
        for current in polygon:
            x1, y1 = previous
            x2, y2 = current
            if (y1 > y) != (y2 > y):
                crossing = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < crossing:
                    inside = not inside
            previous = current
        return inside

    @staticmethod
    def _distance_to_segment(
        point: tuple[float, float], first: tuple[float, float], second: tuple[float, float]
    ) -> float:
        px, py = point
        x1, y1 = first
        x2, y2 = second
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    @staticmethod
    def _render(
        coverage: AerialCoverage, buildings: list[InventoryBuilding], target: Path
    ) -> None:
        with Image.open(coverage.image_path).convert("RGB") as image:
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()
            for building in buildings:
                pixels = [
                    (
                        (lon - coverage.west) / (coverage.east - coverage.west) * image.width,
                        (coverage.north - lat) / (coverage.north - coverage.south) * image.height,
                    )
                    for lon, lat in building.polygon
                ]
                color = (255, 165, 0) if building.boundary_intersection else (255, 40, 40)
                draw.line(pixels + [pixels[0]], fill=color, width=3)
                cx = sum(point[0] for point in pixels) / len(pixels)
                cy = sum(point[1] for point in pixels) / len(pixels)
                draw.rectangle((cx - 3, cy - 7, cx + 33, cy + 7), fill=(255, 255, 255))
                draw.text((cx, cy - 6), building.code, fill=(0, 0, 0), font=font)
            image.save(target, format="PNG")

    @staticmethod
    def _write_geojson(
        center: LonLat, radius_m: int, buildings: list[InventoryBuilding], target: Path
    ) -> None:
        features = []
        for building in buildings:
            ring = [list(point) for point in building.polygon]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            features.append(
                {
                    "type": "Feature",
                    "id": building.id,
                    "properties": {
                        "code": building.code,
                        "boundary_intersection": building.boundary_intersection,
                        "floors": building.floors,
                        "height_m": building.height_m,
                        "front_bearing_deg": building.front_bearing_deg,
                        "source": building.source,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                }
            )
        payload = {
            "type": "FeatureCollection",
            "properties": {"center": list(center), "radius_m": radius_m},
            "features": features,
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _write_csv(buildings: list[InventoryBuilding], target: Path) -> None:
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=(
                    "id", "code", "boundary_intersection", "floors", "height_m",
                    "front_bearing_deg", "source", "footprint_json",
                ),
            )
            writer.writeheader()
            for building in buildings:
                writer.writerow(
                    {
                        "id": building.id,
                        "code": building.code,
                        "boundary_intersection": building.boundary_intersection,
                        "floors": building.floors,
                        "height_m": building.height_m,
                        "front_bearing_deg": building.front_bearing_deg,
                        "source": building.source,
                        "footprint_json": json.dumps(building.polygon),
                    }
                )

    @staticmethod
    def _building(row: sqlite3.Row) -> InventoryBuilding:
        values = dict(row)
        polygon = tuple(tuple(point) for point in json.loads(values["footprint_json"]))
        return InventoryBuilding(
            str(values["id"]), str(values["project_id"]), str(values["code"]),
            polygon, bool(values["boundary_intersection"]),
            int(values["floors"]) if values["floors"] is not None else None,
            float(values["target_height_m"]),
            float(values["front_bearing_deg"])
            if values["front_bearing_deg"] is not None else None,
            str(values["inventory_source"] or "manual"),
        )
