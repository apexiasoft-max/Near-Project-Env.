from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageFilter

from npe.application.inventory import EARTH_RADIUS_M
from npe.infrastructure.osm import building_candidates


def _inside(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    result = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
        previous = current
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("osm", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    lon0, lat0 = calibration["center"]
    origin_x = calibration["origin_x"]
    origin_y = calibration["origin_y"]
    mpp = calibration["meters_per_pixel"]
    image = Image.open(args.image).convert("RGB")
    edge = image.convert("L").filter(ImageFilter.FIND_EDGES)
    rgb = image.load()
    edge_pixels = edge.load()
    results = []
    for candidate in building_candidates(args.osm):
        polygon = []
        local = []
        for lon, lat in candidate.polygon:
            x_m = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
            y_m = math.radians(lat - lat0) * EARTH_RADIUS_M
            local.append((x_m, y_m))
            polygon.append((origin_x + x_m / mpp, origin_y - y_m / mpp))
        centroid_x = sum(point[0] for point in local) / len(local)
        centroid_y = sum(point[1] for point in local) / len(local)
        if math.hypot(centroid_x, centroid_y) > 230:
            continue
        x_min = max(0, math.floor(min(point[0] for point in polygon)))
        x_max = min(image.width - 1, math.ceil(max(point[0] for point in polygon)))
        y_min = max(0, math.floor(min(point[1] for point in polygon)))
        y_max = min(image.height - 1, math.ceil(max(point[1] for point in polygon)))
        values = []
        for y in range(y_min, y_max + 1, 2):
            for x in range(x_min, x_max + 1, 2):
                if _inside(x, y, polygon):
                    red, green, blue = rgb[x, y]
                    maximum = max(red, green, blue)
                    values.append((
                        maximum, maximum - min(red, green, blue), edge_pixels[x, y],
                    ))
        if not values:
            continue
        bright = sum(value[0] >= 150 for value in values) / len(values)
        neutral = sum(value[1] <= 38 for value in values) / len(values)
        edged = sum(value[2] >= 35 for value in values) / len(values)
        score = 0.55 * bright + 0.20 * neutral + 0.25 * min(1.0, edged * 3)
        results.append({
            "source": candidate.source, "distance_m": round(math.hypot(centroid_x, centroid_y), 1),
            "bright_fraction": round(bright, 3), "neutral_fraction": round(neutral, 3),
            "edge_fraction": round(edged, 3), "roof_score": round(score, 3),
        })
    results.sort(key=lambda item: item["roof_score"])
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results[:15]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
