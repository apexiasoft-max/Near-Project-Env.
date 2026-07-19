from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from npe.application.inventory import EARTH_RADIUS_M
from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage
from npe.infrastructure.osm import building_candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("image", type=Path)
    parser.add_argument("osm", type=Path)
    parser.add_argument("latitude", type=float)
    parser.add_argument("longitude", type=float)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("--exclude-nearest-project-site", action="store_true")
    parser.add_argument("--exclude-sources", type=Path)
    args = parser.parse_args()
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    mpp = float(calibration["meters_per_pixel"])
    origin_x = float(calibration["origin_x"])
    origin_y = float(calibration["origin_y"])
    west_m = -origin_x * mpp
    east_m = (float(calibration["image_width"]) - origin_x) * mpp
    north_m = origin_y * mpp
    south_m = -(float(calibration["image_height"]) - origin_y) * mpp
    west = args.longitude + math.degrees(west_m / EARTH_RADIUS_M) / math.cos(
        math.radians(args.latitude)
    )
    east = args.longitude + math.degrees(east_m / EARTH_RADIUS_M) / math.cos(
        math.radians(args.latitude)
    )
    south = args.latitude + math.degrees(south_m / EARTH_RADIUS_M)
    north = args.latitude + math.degrees(north_m / EARTH_RADIUS_M)
    coverage = AerialCoverage(
        args.image, west, south, east, north,
    )
    app = bootstrap()
    candidates = building_candidates(args.osm)
    if args.exclude_sources:
        excluded = set(json.loads(args.exclude_sources.read_text(encoding="utf-8")))
        candidates = [candidate for candidate in candidates if candidate.source not in excluded]
    if args.exclude_nearest_project_site and candidates:
        def distance(candidate):
            lon = sum(point[0] for point in candidate.polygon) / len(candidate.polygon)
            lat = sum(point[1] for point in candidate.polygon) / len(candidate.polygon)
            x = math.radians(lon - args.longitude) * EARTH_RADIUS_M * math.cos(
                math.radians(args.latitude)
            )
            y = math.radians(lat - args.latitude) * EARTH_RADIUS_M
            return math.hypot(x, y)

        candidates.remove(min(candidates, key=distance))
    artifacts = app.inventory.build(args.project_id, coverage, candidates)
    print(artifacts.coded_aerial)
    print(f"buildings={len(artifacts.buildings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
