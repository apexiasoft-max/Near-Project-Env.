from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings


def test_manual_pool_indexes_only_inbox_deduplicates_and_preserves_metadata(
    tmp_path: Path,
) -> None:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    project_id = container.workflow.create_job("P", 35.7, 51.4, 100, "MAIN", 1).project_id
    inbox = container.manual_pool.inbox(project_id)
    first = inbox / "tower.jpg"
    Image.new("RGB", (1920, 1080), (120, 90, 80)).save(first)
    (inbox / "tower.json").write_text(
        json.dumps({"style": "modern", "floors": 8, "has_balcony": True}),
        encoding="utf-8",
    )
    (inbox / "duplicate.jpg").write_bytes(first.read_bytes())
    (inbox / "broken.png").write_text("not an image", encoding="utf-8")
    outside = tmp_path / "outside.jpg"
    Image.new("RGB", (10, 10)).save(outside)

    items, failures = container.manual_pool.scan(project_id)

    assert len(items) == 1
    assert items[0].style == "modern"
    assert (items[0].floors, items[0].has_balcony, items[0].quality_score) == (8, True, 1)
    assert {item["reason"].split(":")[0] for item in failures} == {
        "duplicate_in_scan", "invalid_image",
    }
    assert all(item.original_path != outside for item in items)

    rescanned, _ = container.manual_pool.scan(project_id)
    assert rescanned[0].id == items[0].id
