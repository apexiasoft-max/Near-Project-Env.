from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate
from npe.shared.config import AppPaths, Settings


def _container(tmp_path: Path):
    return bootstrap(Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0))


def _project(container) -> str:
    return container.workflow.create_job("Inventory", 35.7577, 51.4099, 200, "MAIN", 1).project_id


def _coverage(tmp_path: Path, margin: float = 0.003) -> AerialCoverage:
    image = tmp_path / "aerial.png"
    Image.new("RGB", (640, 640), (72, 78, 82)).save(image)
    return AerialCoverage(
        image, 51.4099 - margin, 35.7577 - margin,
        51.4099 + margin, 35.7577 + margin,
    )


def _square(lon: float, lat: float, delta: float = 0.00005):
    return (
        (lon - delta, lat - delta), (lon + delta, lat - delta),
        (lon + delta, lat + delta), (lon - delta, lat + delta),
    )


def test_build_filters_radius_marks_boundary_and_exports_artifacts(tmp_path: Path) -> None:
    container = _container(tmp_path)
    project_id = _project(container)
    candidates = [
        FootprintCandidate(_square(51.4099, 35.7577), "manual", floors=6),
        # Roughly 198 m east; footprint crosses the 200 m boundary.
        FootprintCandidate(_square(51.41209, 35.7577, 0.00012), "manual", height_m=18),
        FootprintCandidate(_square(51.4140, 35.7577), "manual", floors=4),
    ]

    result = container.inventory.build(project_id, _coverage(tmp_path), candidates)

    assert [building.code for building in result.buildings] == ["B001", "B002"]
    assert [building.boundary_intersection for building in result.buildings] == [False, True]
    assert result.buildings[0].height_m == 18
    for artifact in (result.original_aerial, result.coded_aerial, result.geojson, result.csv):
        assert artifact.is_file()
    payload = json.loads(result.geojson.read_text(encoding="utf-8"))
    assert len(payload["features"]) == 2
    assert payload["properties"]["radius_m"] == 200


def test_codes_are_never_reused_after_soft_delete(tmp_path: Path) -> None:
    container = _container(tmp_path)
    project_id = _project(container)
    first = container.inventory.build(
        project_id, _coverage(tmp_path), [FootprintCandidate(_square(51.4099, 35.7577), "manual")]
    )
    with container.database.connect() as connection:
        connection.execute(
            "UPDATE buildings SET deleted_at = '2026-01-01' WHERE id = ?",
            (first.buildings[0].id,),
        )
    second = container.inventory.build(
        project_id, _coverage(tmp_path), [FootprintCandidate(_square(51.4101, 35.7577), "manual")]
    )
    assert second.buildings[0].code == "B002"


def test_rejects_aerial_that_does_not_cover_complete_radius(tmp_path: Path) -> None:
    container = _container(tmp_path)
    with pytest.raises(ValueError, match="complete requested radius"):
        container.inventory.build(_project(container), _coverage(tmp_path, 0.0005), [])
