from __future__ import annotations

import pytest

from npe.application.height import HeightService
from npe.domain.height import HeightMethod


def test_floor_count_estimate_is_within_one_floor_range() -> None:
    estimate = HeightService.from_floors(8, 3.1)
    assert estimate.height_m == pytest.approx(24.8)
    assert estimate.method == HeightMethod.FLOOR_COUNT
    assert estimate.minimum_m == pytest.approx(21.7)
    assert estimate.maximum_m == pytest.approx(27.9)


def test_calibrated_shadow_uses_reference_ratio_and_rejects_occlusion() -> None:
    estimate = HeightService.from_calibrated_shadow(12, 10, 20)
    assert estimate.height_m == 24
    assert estimate.floors == 8
    assert 0 < estimate.confidence < 1
    with pytest.raises(ValueError, match="Occluded"):
        HeightService.from_calibrated_shadow(12, 10, 20, occluded=True)


def test_override_requires_explanation() -> None:
    with pytest.raises(ValueError, match="reason"):
        HeightService.override(24, 8, "")
    assert HeightService.override(24, 8, "survey").confidence == 1


def test_aerial_relative_estimate_preserves_range_and_evidence() -> None:
    estimate = HeightService.from_aerial_relative(6, 5, 7, 0.62, "clear relative shadow")
    assert estimate.height_m == pytest.approx(18.6)
    assert estimate.minimum_m == pytest.approx(15.5)
    assert estimate.maximum_m == pytest.approx(21.7)
    assert estimate.method == HeightMethod.AERIAL_RELATIVE
    assert estimate.evidence["observation"] == "clear relative shadow"

    with pytest.raises(ValueError, match="range"):
        HeightService.from_aerial_relative(6, 7, 8, 0.5, "invalid")
