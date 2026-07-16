"""Prepare approved views for Hunyuan without changing building appearance."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from npe.domain.five_view import REQUIRED_DIRECTIONS


def prepare_hunyuan_views(source_dir: Path, target_dir: Path) -> Path:
    """Center each full view on a square dark-gray canvas for robust detection."""
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "method": "square-pad-v1",
        "appearance_changed": False,
        "outputs": {},
    }
    outputs = manifest["outputs"]
    assert isinstance(outputs, dict)
    for direction in REQUIRED_DIRECTIONS:
        matches = list(source_dir.glob(f"{direction}.*"))
        if len(matches) != 1:
            raise FileNotFoundError(f"Expected one {direction} view")
        with Image.open(matches[0]) as source:
            image = source.convert("RGB")
        size = max(image.width, image.height)
        canvas = Image.new("RGB", (size, size), (50, 54, 61))
        offset = ((size - image.width) // 2, (size - image.height) // 2)
        canvas.paste(image, offset)
        output = target_dir / f"{direction}.png"
        canvas.save(output, "PNG")
        outputs[direction] = {
            "source": str(matches[0]),
            "output": str(output),
            "size": [size, size],
            "offset": list(offset),
        }
    manifest_path = target_dir / "preparation.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
