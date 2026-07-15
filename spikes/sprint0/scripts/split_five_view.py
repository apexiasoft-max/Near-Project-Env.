"""Split a fixed five-column ChatGPT sheet into Hunyuan-ready images."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


DIRECTIONS = ("front", "back", "left", "right", "top")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_sheet(source: Path, output_dir: Path, header_ratio: float = 0.06) -> dict:
    if not 0 <= header_ratio < 0.25:
        raise ValueError("header_ratio must be between 0 and 0.25")

    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.load()
        if image.width < 5 or image.height < 100:
            raise ValueError("sheet is too small")

        boundaries = [round(index * image.width / 5) for index in range(6)]
        top = round(image.height * header_ratio)
        outputs = []
        for index, direction in enumerate(DIRECTIONS):
            left = boundaries[index] + (1 if index else 0)
            right = boundaries[index + 1] - (1 if index < 4 else 0)
            crop = image.crop((left, top, right, image.height)).convert("RGB")
            target = output_dir / f"{direction}.png"
            crop.save(target, format="PNG", optimize=True)
            outputs.append(
                {
                    "direction": direction,
                    "file": target.name,
                    "width": crop.width,
                    "height": crop.height,
                    "sha256": sha256(target),
                }
            )

    manifest = {
        "schema_version": 1,
        "source": source.name,
        "source_sha256": sha256(source),
        "order": list(DIRECTIONS),
        "header_ratio_removed": header_ratio,
        "outputs": outputs,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--header-ratio", type=float, default=0.06)
    args = parser.parse_args()
    manifest = split_sheet(args.source, args.output_dir, args.header_ratio)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

