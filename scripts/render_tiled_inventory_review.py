from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from npe.application.inventory import EARTH_RADIUS_M

TILE_PROJECT_PIXEL = {
    "center": (817.5, 449.0),
    "northwest": (1317.5, 749.0),
    "north": (817.5, 749.0),
    "northeast": (317.5, 749.0),
    "east": (317.5, 449.0),
    "west": (1317.5, 449.0),
    "southwest": (1317.5, 149.0),
    "south": (817.5, 149.0),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tiles", type=Path)
    parser.add_argument("geojson", type=Path)
    parser.add_argument("latitude", type=float)
    parser.add_argument("longitude", type=float)
    parser.add_argument("output", type=Path)
    parser.add_argument("--calibrations", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.geojson.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, (origin_x, origin_y) in TILE_PROJECT_PIXEL.items():
        source = args.tiles / f"{name}.png"
        if not source.exists():
            continue
        image = Image.open(source).convert("RGB")
        meters_per_pixel = 0.483 / 2
        if args.calibrations:
            calibration_path = args.calibrations / name / "calibration.json"
            calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
            origin_x = calibration["origin_x"]
            origin_y = calibration["origin_y"]
            meters_per_pixel = calibration["meters_per_pixel"]
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=16)
        for feature in payload["features"]:
            ring = feature["geometry"]["coordinates"][0][:-1]
            pixels = []
            for lon, lat in ring:
                x_m = math.radians(lon - args.longitude) * EARTH_RADIUS_M * math.cos(
                    math.radians(args.latitude)
                )
                y_m = math.radians(lat - args.latitude) * EARTH_RADIUS_M
                pixels.append((
                    origin_x + x_m / meters_per_pixel,
                    origin_y - y_m / meters_per_pixel,
                ))
            if not any(0 <= x < image.width and 0 <= y < image.height for x, y in pixels):
                continue
            color = (255, 40, 40)
            draw.line(pixels + [pixels[0]], fill=color, width=4)
            cx = sum(point[0] for point in pixels) / len(pixels)
            cy = sum(point[1] for point in pixels) / len(pixels)
            code = feature["properties"]["code"]
            box = draw.textbbox((cx, cy), code, font=font, anchor="mm")
            draw.rectangle((box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3), fill="white")
            draw.text((cx, cy), code, fill="black", font=font, anchor="mm")
        image.save(args.output / f"{name}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
