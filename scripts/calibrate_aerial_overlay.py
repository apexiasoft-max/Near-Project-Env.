from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from npe.application.inventory import EARTH_RADIUS_M
from npe.infrastructure.osm import building_candidates


def _local_meters(lon: float, lat: float, lon0: float, lat0: float) -> tuple[float, float]:
    x = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * EARTH_RADIUS_M
    return x, y


def _samples(polygons, lon0: float, lat0: float) -> list[tuple[float, float]]:
    result = []
    for candidate in polygons:
        points = [_local_meters(lon, lat, lon0, lat0) for lon, lat in candidate.polygon]
        for first, second in zip(points, points[1:] + points[:1], strict=True):
            distance = math.dist(first, second)
            count = max(2, int(distance / 4))
            for index in range(count):
                ratio = index / count
                result.append((
                    first[0] + (second[0] - first[0]) * ratio,
                    first[1] + (second[1] - first[1]) * ratio,
                ))
    return result


def _score(edge, samples, origin_x: int, origin_y: int, mpp: float) -> float:
    width, height = edge.size
    pixels = edge.load()
    values = []
    for x_m, y_m in samples:
        x = round(origin_x + x_m / mpp)
        y = round(origin_y - y_m / mpp)
        if 1 <= x < width - 1 and 1 <= y < height - 1:
            values.append(max(
                pixels[x, y], pixels[x - 1, y], pixels[x + 1, y],
                pixels[x, y - 1], pixels[x, y + 1],
            ))
    if len(values) < len(samples) * 0.6:
        return -1
    values.sort(reverse=True)
    keep = max(1, int(len(values) * 0.7))
    return sum(values[:keep]) / keep


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("osm", type=Path)
    parser.add_argument("latitude", type=float)
    parser.add_argument("longitude", type=float)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    candidates = building_candidates(args.osm)
    samples = _samples(candidates, args.longitude, args.latitude)
    image = Image.open(args.image).convert("RGB")
    edge = image.convert("L").filter(ImageFilter.FIND_EDGES)
    center_x, center_y = image.width // 2, image.height // 2
    best = (-1.0, center_x, center_y, 0.6)
    for mpp_index in range(48, 73, 2):
        mpp = mpp_index / 100
        for origin_x in range(center_x - 80, center_x + 81, 8):
            for origin_y in range(center_y - 64, center_y + 65, 8):
                score = _score(edge, samples, origin_x, origin_y, mpp)
                if score > best[0]:
                    best = (score, origin_x, origin_y, mpp)
    _, coarse_x, coarse_y, coarse_mpp = best
    for mpp_index in range(round(coarse_mpp * 100) - 3, round(coarse_mpp * 100) + 4):
        mpp = mpp_index / 100
        for origin_x in range(coarse_x - 8, coarse_x + 9, 2):
            for origin_y in range(coarse_y - 8, coarse_y + 9, 2):
                score = _score(edge, samples, origin_x, origin_y, mpp)
                if score > best[0]:
                    best = (score, origin_x, origin_y, mpp)
    score, origin_x, origin_y, mpp = best
    preview = image.copy()
    draw = ImageDraw.Draw(preview)
    for candidate in candidates:
        pixels = []
        for lon, lat in candidate.polygon:
            x_m, y_m = _local_meters(lon, lat, args.longitude, args.latitude)
            pixels.append((origin_x + x_m / mpp, origin_y - y_m / mpp))
        draw.line(pixels + [pixels[0]], fill=(255, 0, 0), width=2)
    args.output.mkdir(parents=True, exist_ok=True)
    preview.save(args.output / "calibration-preview.png")
    payload = {
        "score": score, "origin_x": origin_x, "origin_y": origin_y,
        "meters_per_pixel": mpp, "image_width": image.width,
        "image_height": image.height, "center": [args.longitude, args.latitude],
    }
    (args.output / "calibration.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8",
    )
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
