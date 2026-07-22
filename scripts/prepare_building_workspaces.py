from __future__ import annotations

import argparse
import json

from npe.bootstrap import bootstrap


def main() -> int:
    parser = argparse.ArgumentParser(description="Create traceable per-building workspaces")
    parser.add_argument("project_id")
    args = parser.parse_args()

    app = bootstrap()
    buildings = app.inventory.list_buildings(args.project_id)
    root = app.settings.paths.projects / args.project_id / "buildings"
    manifest = []
    for building in buildings:
        building_root = root / building.code
        for name in ("references", "five-view", "hunyuan", "models", "reports"):
            (building_root / name).mkdir(parents=True, exist_ok=True)
        centroid = [
            sum(point[0] for point in building.polygon) / len(building.polygon),
            sum(point[1] for point in building.polygon) / len(building.polygon),
        ]
        metadata = {
            "id": building.id,
            "code": building.code,
            "project_id": building.project_id,
            "centroid": centroid,
            "source": building.source,
            "status": "inventory_candidate",
            "requires_map_approval": True,
            "height_m": None,
            "floors": None,
            "references": [],
        }
        (building_root / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        manifest.append(metadata)
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"prepared={len(manifest)} root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
