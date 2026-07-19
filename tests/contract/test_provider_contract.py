from __future__ import annotations

from pathlib import Path

from npe.domain.reference import ReferenceObservation, ReferenceProvider


def test_provider_observation_contract_supports_missing_camera_metadata(tmp_path: Path) -> None:
    image = tmp_path / "provider.jpg"
    image.write_bytes(b"fake-image")
    observation = ReferenceObservation(
        provider=ReferenceProvider.GOOGLE, source_id="fixture-1", image_path=image,
        captured_at=None, camera=None, heading_deg=None, horizontal_fov_deg=None,
        width_px=1280, height_px=720, visibility=0.8, occlusion=0.2,
        metadata={"fixture": True},
    )
    assert observation.image_path.is_file()
    assert observation.provider == "google"
    assert observation.camera is None
