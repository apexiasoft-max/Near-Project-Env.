from __future__ import annotations

import argparse
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
    parser.add_argument("coverage_radius_m", type=float)
    args = parser.parse_args()
    lat_delta = math.degrees(args.coverage_radius_m / EARTH_RADIUS_M)
    lon_delta = lat_delta / math.cos(math.radians(args.latitude))
    coverage = AerialCoverage(
        args.image, args.longitude - lon_delta, args.latitude - lat_delta,
        args.longitude + lon_delta, args.latitude + lat_delta,
    )
    app = bootstrap()
    artifacts = app.inventory.build(
        args.project_id, coverage, building_candidates(args.osm),
    )
    print(artifacts.coded_aerial)
    print(f"buildings={len(artifacts.buildings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
