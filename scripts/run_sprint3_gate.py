"""Run the Sprint 3 Google-only Product Owner variance gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate
from npe.domain.reference import ReferenceObservation, ReferenceProvider
from npe.shared.config import AppPaths, Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("streetview", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    latitude, longitude = 35.784297, 51.3741911
    container = bootstrap(
        Settings(paths=AppPaths.under(args.output / "runtime"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job(
        "Sprint 3 Google Reference Gate", latitude, longitude, 100, "MAIN", 1
    )
    footprint = square(51.37396, 35.78418, 0.00008)
    fallback_footprint = square(51.37435, 35.78435, 0.00006)
    aerial = args.output / "aerial-fixture.png"
    Image.new("RGB", (256, 256), (80, 84, 88)).save(aerial)
    inventory = container.inventory.build(
        job.project_id,
        AerialCoverage(aerial, longitude - 0.002, latitude - 0.002,
                       longitude + 0.002, latitude + 0.002),
        [
            FootprintCandidate(footprint, "reviewed-google", floors=12),
            FootprintCandidate(fallback_footprint, "manual-fallback", floors=6),
        ],
    )
    primary, fallback = inventory.buildings
    with Image.open(args.streetview) as image:
        width, height = image.size
    observation = ReferenceObservation(
        ReferenceProvider.GOOGLE,
        "CIHM0ogKEICAgICRlNCugQE",
        args.streetview.resolve(),
        "2023-03",
        (longitude, latitude),
        241.14,
        75.0,
        width,
        height,
        0.94,
        0.12,
        {
            "source": "user-opened Google Street View",
            "neshan_state": "unavailable_by_product-owner-variance",
        },
    )
    ranked = container.references.rank(primary.id, footprint, [observation])
    with container.database.connect() as connection:
        candidate_id = str(
            connection.execute(
                """SELECT id FROM reference_candidates
                   WHERE building_id = ? AND active = 1 ORDER BY rank LIMIT 1""",
                (primary.id,),
            ).fetchone()[0]
        )
    container.reference_review.select(
        job.project_id, primary.id, candidate_id, "sprint3-gate", 241.14
    )
    google_approval = container.reference_review.approve(
        job.project_id, primary.id, "sprint3-gate"
    )
    intervention_id = container.reference_review.mark_missing(
        job.project_id, fallback.id, "sprint3-gate"
    )
    replacement_id = container.reference_review.upload_replacement(
        job.project_id, fallback.id, args.streetview, "sprint3-gate"
    )
    fallback_approval = container.reference_review.approve(
        job.project_id, fallback.id, "sprint3-gate"
    )
    report = {
        "provider_mode": "google_only_product_owner_variance",
        "neshan": {"state": "unavailable", "required": False},
        "google": {
            "camera": {"latitude": latitude, "longitude": longitude},
            "heading_deg": 241.14,
            "captured_at": "2023-03",
            "source_id": observation.source_id,
            "attribution_score": ranked[0].attribution_score,
            "quality_score": ranked[0].quality_score,
            "total_score": ranked[0].total_score,
            "evidence": ranked[0].evidence,
            "approval_id": google_approval.id,
        },
        "manual_fallback": {
            "missing_reference_event": intervention_id,
            "replacement_candidate_id": replacement_id,
            "approval_id": fallback_approval.id,
            "resumed": True,
        },
        "result": "go_with_google_only_variance",
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
