from __future__ import annotations

from pathlib import Path

from npe.application.references import ReferenceService
from npe.domain.reference import ReferenceObservation, ReferenceProvider

FOOTPRINT = (
    (51.4098, 35.7576), (51.4100, 35.7576),
    (51.4100, 35.7578), (51.4098, 35.7578),
)


def observation(
    provider: ReferenceProvider, source_id: str, heading: float,
    *, visibility: float = 0.9, occlusion: float = 0.1,
) -> ReferenceObservation:
    return ReferenceObservation(
        provider, source_id, Path(f"{source_id}.png"), None,
        (51.4099, 35.7569), heading, 90, 1920, 1080,
        visibility, occlusion, {},
    )


def test_camera_geometry_outranks_wrong_heading() -> None:
    toward = observation(ReferenceProvider.NESHAN, "toward", 0)
    away = observation(ReferenceProvider.GOOGLE, "away", 180)
    scored = [ReferenceService._score(FOOTPRINT, item) for item in (away, toward)]
    assert scored[1].attribution_score > scored[0].attribution_score


def test_provider_has_no_priority_and_quality_can_win() -> None:
    google = observation(ReferenceProvider.GOOGLE, "g", 0, visibility=0.5, occlusion=0.5)
    neshan = observation(ReferenceProvider.NESHAN, "n", 0, visibility=1, occlusion=0)
    assert ReferenceService._score(FOOTPRINT, neshan).total_score > ReferenceService._score(
        FOOTPRINT, google
    ).total_score


def test_invalid_quality_evidence_is_rejected() -> None:
    invalid = observation(ReferenceProvider.GOOGLE, "bad", 0, visibility=1.2)
    try:
        ReferenceService._score(FOOTPRINT, invalid)
    except ValueError as error:
        assert "[0, 1]" in str(error)
    else:
        raise AssertionError("invalid evidence was accepted")
