from __future__ import annotations

import json
from pathlib import Path

import pytest

from npe.application.height import HeightService

DATASET = Path(__file__).parents[1] / "golden" / "tehran_buildings.v1.json"


def test_golden_dataset_is_versioned_varied_and_height_calibrated() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    samples = payload["samples"]
    assert payload["version"] == 1
    assert len(samples) >= 8
    assert {item["imagery"] for item in samples} == {"available", "partial", "missing"}
    assert {item["shadow"]["occluded"] for item in samples} == {True, False}
    assert max(item["floors"] for item in samples) - min(item["floors"] for item in samples) >= 10
    assert len({json.dumps(item["footprint"]) for item in samples}) == len(samples)
    for item in samples:
        if item["shadow"]["occluded"]:
            continue
        estimate = HeightService.from_calibrated_shadow(
            item["shadow"]["length_m"], item["shadow"]["reference_length_m"],
            item["shadow"]["reference_height_m"],
        )
        assert estimate.height_m == pytest.approx(item["reviewed_height_m"], abs=3.0)
