from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description="Project GPT parcel outlines onto an aerial image")
    parser.add_argument("source", type=Path)
    parser.add_argument("annotated", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--radius-m", type=float, default=200.0)
    args = parser.parse_args()

    source = cv2.imread(str(args.source), cv2.IMREAD_COLOR)
    annotated = cv2.imread(str(args.annotated), cv2.IMREAD_COLOR)
    if source is None or annotated is None:
        raise FileNotFoundError("Could not read source or annotated image")
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    output = args.output
    output.mkdir(parents=True, exist_ok=True)

    homography, inliers = _align(annotated, source)
    red = _red_mask(annotated)
    warped = cv2.warpPerspective(red, homography, (source.shape[1], source.shape[0]))
    # GPT may leave sub-pixel breaks in otherwise closed parcel outlines. A larger
    # closing kernel repairs those gaps after registration without expanding the
    # parcel selection itself.
    warped = cv2.morphologyEx(warped, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    warped = cv2.dilate(warped, np.ones((3, 3), np.uint8), iterations=1)

    origin = np.array(
        [float(calibration["origin_x"]), float(calibration["origin_y"])], dtype=np.float64
    )
    meters_per_pixel = float(calibration["meters_per_pixel"])
    center_lon, center_lat = (float(value) for value in calibration["center"])
    parcels = _parcel_regions(warped, origin, args.radius_m / meters_per_pixel)
    parcels.sort(key=lambda contour: _sort_key(contour, origin))

    preview = source.copy()
    cv2.circle(
        preview,
        tuple(np.rint(origin).astype(int)),
        round(args.radius_m / meters_per_pixel),
        (255, 220, 0),
        3,
        cv2.LINE_AA,
    )
    features = []
    for number, contour in enumerate(parcels, start=1):
        code = f"B{number:03d}"
        simplified = cv2.approxPolyDP(contour, 2.0, True).reshape(-1, 2)
        centroid = simplified.mean(axis=0)
        cv2.polylines(preview, [simplified.astype(np.int32)], True, (0, 0, 255), 3)
        cv2.rectangle(
            preview,
            (int(centroid[0]) - 3, int(centroid[1]) - 10),
            (int(centroid[0]) + 42, int(centroid[1]) + 8),
            (255, 255, 255),
            -1,
        )
        cv2.putText(
            preview,
            code,
            (int(centroid[0]), int(centroid[1]) + 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        ring = [
            _pixel_to_lonlat(point, origin, meters_per_pixel, center_lon, center_lat)
            for point in simplified
        ]
        ring.append(ring[0])
        features.append(
            {
                "type": "Feature",
                "id": code,
                "properties": {
                    "code": code,
                    "source": "gpt-semantic-parcel-outline",
                    "requires_human_approval": True,
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        )

    cv2.imwrite(str(output / "red-mask-aligned.png"), warped)
    cv2.imwrite(str(output / "coded-parcels-review.png"), preview)
    (output / "parcels.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "properties": {
                    "center": [center_lon, center_lat],
                    "radius_m": args.radius_m,
                    "alignment_inliers": inliers,
                    "status": "requires_human_approval",
                },
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (output / "extraction-report.json").write_text(
        json.dumps(
            {
                "alignment_inliers": inliers,
                "parcel_count": len(parcels),
                "radius_m": args.radius_m,
                "decision": "review_required",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(output / "coded-parcels-review.png")
    print(f"parcels={len(parcels)} alignment_inliers={inliers}")
    return 0


def _align(annotated: np.ndarray, source: np.ndarray) -> tuple[np.ndarray, int]:
    annotated_gray = cv2.cvtColor(annotated, cv2.COLOR_BGR2GRAY)
    source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    detector = cv2.SIFT_create(nfeatures=12_000)
    key_a, desc_a = detector.detectAndCompute(annotated_gray, None)
    key_s, desc_s = detector.detectAndCompute(source_gray, None)
    if desc_a is None or desc_s is None:
        raise RuntimeError("Not enough visual features to align GPT output")
    matches = cv2.BFMatcher(cv2.NORM_L2).knnMatch(desc_a, desc_s, k=2)
    good = [first for first, second in matches if first.distance < 0.72 * second.distance]
    if len(good) < 20:
        raise RuntimeError(f"Alignment rejected: only {len(good)} reliable matches")
    points_a = np.float32([key_a[item.queryIdx].pt for item in good])
    points_s = np.float32([key_s[item.trainIdx].pt for item in good])
    homography, mask = cv2.findHomography(points_a, points_s, cv2.RANSAC, 4.0)
    if homography is None or mask is None:
        raise RuntimeError("Could not calculate annotated-to-source homography")
    inliers = int(mask.sum())
    if inliers < 15:
        raise RuntimeError(f"Alignment rejected: only {inliers} inliers")
    return homography, inliers


def _red_mask(image: np.ndarray) -> np.ndarray:
    blue, green, red = cv2.split(image)
    return np.where(
        (red > 135) & (red > green.astype(np.int16) + 35) & (red > blue.astype(np.int16) + 35),
        255,
        0,
    ).astype(np.uint8)


def _parcel_regions(mask: np.ndarray, origin: np.ndarray, radius_px: float) -> list[np.ndarray]:
    free = cv2.bitwise_not(mask)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(free, connectivity=8)
    parcels: list[np.ndarray] = []
    for label in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[label])
        if area < 700 or area > 60_000 or width < 14 or height < 14:
            continue
        component = np.where(labels == label, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        # Scope membership is based on polygon-circle intersection, not centroid.
        # Otherwise a nearby parcel whose center falls just outside the radius is
        # incorrectly dropped even though part of the building is in scope.
        signed_distance = cv2.pointPolygonTest(
            contour, (float(origin[0]), float(origin[1])), True
        )
        if signed_distance < 0 and abs(signed_distance) > radius_px:
            continue
        parcels.append(contour)
    return parcels


def _centroid(contour: np.ndarray) -> tuple[float, float]:
    moments = cv2.moments(contour)
    if moments["m00"] == 0:
        points = contour.reshape(-1, 2)
        return float(points[:, 0].mean()), float(points[:, 1].mean())
    return moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]


def _sort_key(contour: np.ndarray, origin: np.ndarray) -> tuple[float, float]:
    centroid = np.array(_centroid(contour))
    delta = centroid - origin
    return float(np.linalg.norm(delta)), math.atan2(float(delta[0]), float(-delta[1]))


def _pixel_to_lonlat(
    point: np.ndarray,
    origin: np.ndarray,
    meters_per_pixel: float,
    center_lon: float,
    center_lat: float,
) -> list[float]:
    east_m = (float(point[0]) - origin[0]) * meters_per_pixel
    north_m = (origin[1] - float(point[1])) * meters_per_pixel
    lat = center_lat + math.degrees(north_m / 6_371_008.8)
    lon = center_lon + math.degrees(east_m / 6_371_008.8) / math.cos(math.radians(center_lat))
    return [lon, lat]


if __name__ == "__main__":
    raise SystemExit(main())
