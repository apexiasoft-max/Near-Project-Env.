"""Generate a repeatable Sprint 2 acceptance bundle from a georeferenced aerial fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate
from npe.shared.config import AppPaths, Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("aerial", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    center_lat, center_lon, radius_m = 35.7577, 51.4099, 200
    container = bootstrap(
        Settings(paths=AppPaths.under(args.output / "runtime"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job(
        "Sprint 2 Tehran Gate", center_lat, center_lon, radius_m, "MAIN", 1,
        args.output,
    )
    candidates = [
        FootprintCandidate(square(51.4093, 35.7578, 0.00012), "reviewed-aerial", floors=6),
        FootprintCandidate(square(51.4100, 35.7574, 0.00015), "reviewed-aerial", floors=8),
        FootprintCandidate(square(51.4108, 35.7582, 0.00011), "reviewed-aerial", floors=5),
        FootprintCandidate(square(51.41205, 35.7577, 0.00015), "reviewed-aerial", floors=7),
        FootprintCandidate(square(51.4140, 35.7577, 0.00010), "out-of-scope", floors=4),
    ]
    coverage = AerialCoverage(
        args.aerial, center_lon - 0.0038, center_lat - 0.003,
        center_lon + 0.0038, center_lat + 0.003,
    )
    result = container.inventory.build(job.project_id, coverage, candidates)
    edited = container.inventory.update_building(
        job.project_id, result.buildings[0].id,
        polygon=square(51.40935, 35.7578, 0.00014),
        floors=7, height_m=21, front_bearing_deg=180,
    )
    estimate = container.height.from_floors(edited.floors or 7)
    container.height.apply(job.project_id, edited.id, estimate)
    approval = container.inventory.approve(job.project_id, "sprint2-gate", "Gate fixture approved")
    report = {
        "coordinates": {"latitude": center_lat, "longitude": center_lon},
        "radius_m": radius_m,
        "building_count": len(result.buildings),
        "boundary_codes": [item.code for item in result.buildings if item.boundary_intersection],
        "corrected_building": edited.code,
        "height_estimate": {
            "meters": estimate.height_m, "floors": estimate.floors,
            "range": [estimate.minimum_m, estimate.maximum_m],
            "method": estimate.method, "confidence": estimate.confidence,
        },
        "approval_id": approval.id,
        "revision_id": approval.revision_id,
        "artifacts": {
            "coded_aerial": str(result.coded_aerial),
            "geojson": str(result.geojson), "csv": str(result.csv),
        },
    }
    (args.output / "gate-result.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


def square(lon: float, lat: float, delta: float):
    return (
        (lon - delta, lat - delta), (lon + delta, lat - delta),
        (lon + delta, lat + delta), (lon - delta, lat + delta),
    )


if __name__ == "__main__":
    main()
