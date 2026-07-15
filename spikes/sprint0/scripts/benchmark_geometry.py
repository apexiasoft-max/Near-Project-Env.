"""Benchmark deterministic footprint and height baseline calculations."""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


def bbox_iou(left: list[float], right: list[float]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    if lx2 <= lx1 or ly2 <= ly1 or rx2 <= rx1 or ry2 <= ry1:
        raise ValueError("bounding boxes must have positive area")
    intersection = max(0.0, min(lx2, rx2) - max(lx1, rx1)) * max(
        0.0, min(ly2, ry2) - max(ly1, ry1)
    )
    left_area = (lx2 - lx1) * (ly2 - ly1)
    right_area = (rx2 - rx1) * (ry2 - ry1)
    return intersection / (left_area + right_area - intersection)


def floor_height(sample: dict[str, Any]) -> float:
    return sample["visible_floor_count"] * sample["mean_floor_height_m"]


def shadow_height(sample: dict[str, Any]) -> float:
    return sample["shadow_length_m"] * math.tan(
        math.radians(sample["solar_elevation_deg"])
    )


def benchmark(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    samples = data.get("samples")
    if not isinstance(samples, list) or len(samples) < 5:
        raise ValueError("at least five samples are required")

    rows: list[dict[str, Any]] = []
    for sample in samples:
        reference = float(sample["reference_height_m"])
        tolerance = float(sample["one_floor_tolerance_m"])
        by_floor = floor_height(sample)
        by_shadow = shadow_height(sample)
        rows.append(
            {
                "site_id": sample["site_id"],
                "reference_height_m": reference,
                "one_floor_tolerance_m": tolerance,
                "height": {
                    "floor_count": {
                        "estimate_m": by_floor,
                        "absolute_error_m": abs(by_floor - reference),
                        "within_one_floor": abs(by_floor - reference) <= tolerance,
                    },
                    "shadow": {
                        "estimate_m": by_shadow,
                        "absolute_error_m": abs(by_shadow - reference),
                        "within_one_floor": abs(by_shadow - reference) <= tolerance,
                    },
                },
                "footprint": {
                    "threshold_bbox_iou": bbox_iou(
                        sample["reference_bbox_m"], sample["threshold_bbox_m"]
                    ),
                    "edge_bbox_iou": bbox_iou(
                        sample["reference_bbox_m"], sample["edge_bbox_m"]
                    ),
                },
            }
        )

    def height_summary(method: str) -> dict[str, float]:
        errors = [row["height"][method]["absolute_error_m"] for row in rows]
        passes = [row["height"][method]["within_one_floor"] for row in rows]
        return {
            "mae_m": statistics.fmean(errors),
            "within_one_floor_rate": sum(passes) / len(passes),
        }

    def footprint_summary(method: str) -> dict[str, float]:
        values = [row["footprint"][method] for row in rows]
        return {"mean_iou": statistics.fmean(values), "min_iou": min(values)}

    return {
        "schema_version": 1,
        "fixture_status": data.get("fixture_status"),
        "sample_count": len(rows),
        "rows": rows,
        "summary": {
            "height": {
                "floor_count": height_summary("floor_count"),
                "shadow": height_summary("shadow"),
            },
            "footprint": {
                "threshold_bbox": footprint_summary("threshold_bbox_iou"),
                "edge_bbox": footprint_summary("edge_bbox_iou"),
            },
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: benchmark_geometry.py INPUT_JSON OUTPUT_JSON", file=sys.stderr)
        return 2
    source, output = map(Path, argv[1:])
    result = benchmark(json.loads(source.read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
