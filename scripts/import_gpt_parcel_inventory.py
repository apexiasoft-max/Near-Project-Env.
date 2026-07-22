from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from npe.application.inventory import EARTH_RADIUS_M
from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate


def main() -> int:
    parser = argparse.ArgumentParser(description="Replace an unapproved inventory with GPT parcels")
    parser.add_argument("project_id")
    parser.add_argument("image", type=Path)
    parser.add_argument("geojson", type=Path)
    parser.add_argument("calibration", type=Path)
    args = parser.parse_args()

    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    payload = json.loads(args.geojson.read_text(encoding="utf-8"))
    center_lon, center_lat = (float(value) for value in calibration["center"])
    mpp = float(calibration["meters_per_pixel"])
    origin_x = float(calibration["origin_x"])
    origin_y = float(calibration["origin_y"])
    width = float(calibration["image_width"])
    height = float(calibration["image_height"])
    west = center_lon + math.degrees((-origin_x * mpp) / EARTH_RADIUS_M) / math.cos(
        math.radians(center_lat)
    )
    east = center_lon + math.degrees(((width - origin_x) * mpp) / EARTH_RADIUS_M) / math.cos(
        math.radians(center_lat)
    )
    north = center_lat + math.degrees((origin_y * mpp) / EARTH_RADIUS_M)
    south = center_lat - math.degrees(((height - origin_y) * mpp) / EARTH_RADIUS_M)
    coverage = AerialCoverage(args.image, west, south, east, north)

    candidates = []
    for feature in payload["features"]:
        ring = feature["geometry"]["coordinates"][0]
        polygon = tuple((float(point[0]), float(point[1])) for point in ring[:-1])
        candidates.append(
            FootprintCandidate(
                polygon=polygon,
                source=f"gpt-parcel:{feature['properties']['code']}",
            )
        )

    app = bootstrap()
    removed = app.inventory.discard_unapproved(args.project_id)
    artifacts = app.inventory.build(args.project_id, coverage, candidates)
    print(f"removed={removed} imported={len(artifacts.buildings)}")
    print(artifacts.coded_aerial)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
