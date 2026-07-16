from __future__ import annotations

from pathlib import Path

from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate
from npe.domain.reference import ReferenceObservation, ReferenceProvider
from npe.shared.config import AppPaths, Settings


def test_ranked_provider_candidates_are_persisted_with_alternatives(tmp_path: Path) -> None:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("P", 35.7577, 51.4099, 200, "MAIN", 1)
    aerial = tmp_path / "aerial.png"
    from PIL import Image

    Image.new("RGB", (32, 32)).save(aerial)
    polygon = (
        (51.4098, 35.7576), (51.4100, 35.7576),
        (51.4100, 35.7578), (51.4098, 35.7578),
    )
    inventory = container.inventory.build(
        job.project_id,
        AerialCoverage(aerial, 51.406, 35.754, 51.414, 35.761),
        [FootprintCandidate(polygon, "gate")],
    )
    observations = [
        ReferenceObservation(
            ReferenceProvider.GOOGLE, "google-1", tmp_path / "g.png", None,
            (51.4099, 35.7569), 180, 90, 1920, 1080, 0.4, 0.5, {},
        ),
        ReferenceObservation(
            ReferenceProvider.NESHAN, "neshan-1", tmp_path / "n.png", None,
            (51.4099, 35.7569), 0, 90, 1920, 1080, 0.95, 0.05, {},
        ),
    ]

    ranked = container.references.rank(inventory.buildings[0].id, polygon, observations)

    assert [item.observation.source_id for item in ranked] == ["neshan-1", "google-1"]
    with container.database.connect() as connection:
        rows = connection.execute(
            """SELECT provider, rank, evidence_json FROM reference_candidates
               WHERE building_id = ? AND active = 1 ORDER BY rank""",
            (inventory.buildings[0].id,),
        ).fetchall()
    assert [(row["provider"], row["rank"]) for row in rows] == [("neshan", 1), ("google", 2)]

