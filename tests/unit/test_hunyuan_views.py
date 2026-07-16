from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from npe.application.hunyuan_views import prepare_hunyuan_views
from npe.domain.five_view import REQUIRED_DIRECTIONS


def test_preparation_pads_views_to_square_without_rescaling_subject(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for direction in REQUIRED_DIRECTIONS:
        Image.new("RGB", (300, 700), (100, 80, 60)).save(source / f"{direction}.png")

    manifest_path = prepare_hunyuan_views(source, tmp_path / "prepared")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["appearance_changed"] is False
    for direction in REQUIRED_DIRECTIONS:
        with Image.open(tmp_path / "prepared" / f"{direction}.png") as prepared:
            assert prepared.size == (700, 700)
            assert prepared.getpixel((200, 350)) == (100, 80, 60)
            assert prepared.getpixel((0, 0)) == (50, 54, 61)
