"""Geospatial building inventory domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LonLat = tuple[float, float]
Polygon = tuple[LonLat, ...]


@dataclass(frozen=True)
class AerialCoverage:
    image_path: Path
    west: float
    south: float
    east: float
    north: float


@dataclass(frozen=True)
class FootprintCandidate:
    polygon: Polygon
    source: str
    floors: int | None = None
    height_m: float | None = None
    front_bearing_deg: float | None = None


@dataclass(frozen=True)
class InventoryBuilding:
    id: str
    project_id: str
    code: str
    polygon: Polygon
    boundary_intersection: bool
    floors: int | None
    height_m: float
    front_bearing_deg: float | None
    source: str


@dataclass(frozen=True)
class InventoryArtifacts:
    original_aerial: Path
    coded_aerial: Path
    geojson: Path
    csv: Path
    buildings: tuple[InventoryBuilding, ...]
