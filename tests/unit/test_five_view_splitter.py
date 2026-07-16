from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from npe.application.five_view_splitter import FiveViewSplitter


def make_sheet(path: Path) -> None:
    sheet = Image.new("RGB", (1500, 300), "white")
    draw = ImageDraw.Draw(sheet)
    colors = ("red", "green", "blue", "yellow", "purple")
    for index, color in enumerate(colors):
        left = index * 300
        draw.rectangle((left, 0, left + 299, 299), fill=color)
        draw.rectangle((left + 80, 60, left + 220, 260), fill="black")
        if index:
            draw.rectangle((left - 2, 0, left + 2, 299), fill="white")
    sheet.save(path)


def test_split_creates_exact_named_views_without_separators_and_lineage(
    tmp_path: Path,
) -> None:
    sheet = tmp_path / "sheet.png"
    make_sheet(sheet)
    manifest = tmp_path / "input-manifest.json"
    manifest.write_text('{"run_id":"RUN-1"}', encoding="utf-8")

    result = FiveViewSplitter().split(sheet, tmp_path / "views", manifest, 1)

    assert set(result.views) == {"front", "back", "left", "right", "top"}
    assert all(path.name == f"{direction}.png" for direction, path in result.views.items())
    with Image.open(result.views["back"]) as back:
        assert back.size == (294, 294)
        assert back.getpixel((0, 10)) != (255, 255, 255)
    lineage = json.loads(result.lineage_path.read_text(encoding="utf-8"))
    assert lineage["layout_version"] == "horizontal-five-v1"
    assert lineage["generation_attempt"] == 1
    assert set(lineage["outputs"]) == set(result.views)
    assert all(item["sha256"] for item in lineage["outputs"].values())


def test_split_rejects_sheet_below_five_panel_minimum(tmp_path: Path) -> None:
    sheet = tmp_path / "small.png"
    Image.new("RGB", (1000, 300), "red").save(sheet)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="minimum dimensions"):
        FiveViewSplitter().split(sheet, tmp_path / "views", manifest, 1)


def test_split_rejects_empty_panel(tmp_path: Path) -> None:
    sheet = tmp_path / "empty.png"
    Image.new("RGB", (1500, 300), "gray").save(sheet)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="no meaningful content"):
        FiveViewSplitter().split(sheet, tmp_path / "views", manifest, 1)
