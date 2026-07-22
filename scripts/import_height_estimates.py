from __future__ import annotations

import argparse
import json
from pathlib import Path

from npe.bootstrap import bootstrap


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and import aerial height estimates")
    parser.add_argument("project_id")
    parser.add_argument("estimates", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.estimates.read_text(encoding="utf-8"))
    rows = payload.get("buildings")
    if not isinstance(rows, list):
        raise ValueError("Expected a buildings array")
    app = bootstrap()
    buildings = {item.code: item for item in app.inventory.list_buildings(args.project_id)}
    received = {str(row.get("code")) for row in rows}
    if received != set(buildings):
        missing = sorted(set(buildings) - received)
        unexpected = sorted(received - set(buildings))
        raise ValueError(f"Building code mismatch: missing={missing}, unexpected={unexpected}")

    for row in rows:
        code = str(row["code"])
        estimate = app.height.from_aerial_relative(
            floors=int(row["floors"]),
            minimum_floors=int(row["min_floors"]),
            maximum_floors=int(row["max_floors"]),
            confidence=float(row["confidence"]),
            evidence=str(row["evidence"]),
        )
        app.height.apply(args.project_id, buildings[code].id, estimate)
        metadata_path = (
            app.settings.paths.projects
            / args.project_id
            / "buildings"
            / code
            / "metadata.json"
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.update(
            {
                "floors": estimate.floors,
                "height_m": estimate.height_m,
                "height_range_m": [estimate.minimum_m, estimate.maximum_m],
                "height_confidence": estimate.confidence,
                "height_method": str(estimate.method),
                "height_evidence": estimate.evidence,
            }
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"imported={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
