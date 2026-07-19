"""Extract and review Microsoft Global ML Building Footprints near a project.

The source files are gzip-compressed GeoJSONL partitions.  This script streams
the partition, clips candidates by a metric radius, and can render the polygons
over an already calibrated north-up aerial screenshot.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

EARTH_RADIUS_M = 6_371_008.8


def local_xy(lon: float, lat: float, center_lon: float, center_lat: float) -> tuple[float, float]:
    """Return local east/north metres around ``center``."""
    lat_scale = math.pi * EARTH_RADIUS_M / 180.0
    return (
        (lon - center_lon) * lat_scale * math.cos(math.radians(center_lat)),
        (lat - center_lat) * lat_scale,
    )


def segment_distance_to_origin(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    denominator = dx * dx + dy * dy
    if denominator == 0:
        return math.hypot(*a)
    t = max(0.0, min(1.0, -(a[0] * dx + a[1] * dy) / denominator))
    return math.hypot(a[0] + t * dx, a[1] + t * dy)


def polygon_intersects_radius(points: list[tuple[float, float]], radius_m: float) -> bool:
    if any(math.hypot(x, y) <= radius_m for x, y in points):
        return True
    return any(
        segment_distance_to_origin(points[index], points[(index + 1) % len(points)]) <= radius_m
        for index in range(len(points))
    )


def extract(source: Path, *, lon: float, lat: float, radius_m: float) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    with gzip.open(source, "rt", encoding="utf-8") as stream:
        for line in stream:
            feature = json.loads(line)
            geometry = feature.get("geometry", {})
            if geometry.get("type") != "Polygon":
                continue
            ring = geometry.get("coordinates", [[]])[0]
            local_ring = [local_xy(float(x), float(y), lon, lat) for x, y in ring]
            if local_ring and polygon_intersects_radius(local_ring, radius_m):
                selected.append(feature)
    return selected


def render_overlay(
    aerial_path: Path,
    output_path: Path,
    features: list[dict[str, Any]],
    *,
    lon: float,
    lat: float,
    origin_x: float,
    origin_y: float,
    meters_per_pixel: float,
    radius_m: float,
) -> None:
    image = Image.open(aerial_path).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default(size=16)
    for index, feature in enumerate(features, start=1):
        ring = feature["geometry"]["coordinates"][0]
        pixels = []
        for point_lon, point_lat in ring:
            east, north = local_xy(float(point_lon), float(point_lat), lon, lat)
            pixels.append((origin_x + east / meters_per_pixel, origin_y - north / meters_per_pixel))
        draw.polygon(pixels, fill=(0, 180, 255, 38), outline=(255, 0, 0, 255), width=3)
        center_x = sum(point[0] for point in pixels[:-1]) / max(1, len(pixels) - 1)
        center_y = sum(point[1] for point in pixels[:-1]) / max(1, len(pixels) - 1)
        label = f"M{index:02d}"
        draw.rounded_rectangle(
            (center_x - 18, center_y - 12, center_x + 22, center_y + 10),
            radius=4,
            fill=(255, 255, 255, 230),
            outline=(180, 0, 0, 255),
            width=2,
        )
        draw.text((center_x - 15, center_y - 9), label, fill=(140, 0, 0, 255), font=font)
    radius_px = radius_m / meters_per_pixel
    draw.ellipse(
        (origin_x - radius_px, origin_y - radius_px, origin_x + radius_px, origin_y + radius_px),
        outline=(255, 215, 0, 220),
        width=3,
    )
    draw.ellipse((origin_x - 6, origin_y - 6, origin_x + 6, origin_y + 6), fill=(255, 0, 255, 255))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_geojson", type=Path)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--radius-m", type=float, required=True)
    parser.add_argument("--aerial", type=Path)
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--origin-x", type=float)
    parser.add_argument("--origin-y", type=float)
    parser.add_argument("--meters-per-pixel", type=float)
    args = parser.parse_args()

    features = extract(args.source, lon=args.lon, lat=args.lat, radius_m=args.radius_m)
    collection = {"type": "FeatureCollection", "features": features}
    args.output_geojson.parent.mkdir(parents=True, exist_ok=True)
    args.output_geojson.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    if args.aerial and args.overlay:
        required = (args.origin_x, args.origin_y, args.meters_per_pixel)
        if any(value is None for value in required):
            parser.error("overlay rendering requires origin and meters-per-pixel")
        render_overlay(
            args.aerial,
            args.overlay,
            features,
            lon=args.lon,
            lat=args.lat,
            origin_x=args.origin_x,
            origin_y=args.origin_y,
            meters_per_pixel=args.meters_per_pixel,
            radius_m=args.radius_m,
        )
    print(json.dumps({"building_count": len(features), "output": str(args.output_geojson)}))


if __name__ == "__main__":
    main()
