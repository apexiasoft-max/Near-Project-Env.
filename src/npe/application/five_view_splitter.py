"""Deterministic five-panel sheet splitting, validation and lineage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PIL import Image, ImageStat, UnidentifiedImageError

from npe.domain.five_view import REQUIRED_DIRECTIONS

LAYOUT_VERSION = "horizontal-five-v1"


@dataclass(frozen=True)
class SplitResult:
    views: dict[str, Path]
    lineage_path: Path


class FiveViewSplitter:
    def __init__(self, minimum_width: int = 256, minimum_height: int = 256) -> None:
        self.minimum_width = minimum_width
        self.minimum_height = minimum_height

    def split(
        self, sheet_path: Path, output_dir: Path, source_manifest: Path,
        generation_attempt: int,
    ) -> SplitResult:
        if generation_attempt <= 0:
            raise ValueError("Generation attempt must be positive")
        if not source_manifest.is_file():
            raise FileNotFoundError(source_manifest)
        try:
            with Image.open(sheet_path) as source:
                sheet = source.convert("RGB")
        except (UnidentifiedImageError, OSError) as error:
            raise ValueError(f"Invalid five-view sheet: {error}") from error
        if sheet.width < self.minimum_width * 5 or sheet.height < self.minimum_height:
            raise ValueError("Sheet is below minimum dimensions for five valid views")
        output_dir.mkdir(parents=True, exist_ok=True)
        views: dict[str, Path] = {}
        output_evidence: dict[str, dict[str, object]] = {}
        for index, direction in enumerate(REQUIRED_DIRECTIONS):
            left = round(index * sheet.width / 5) + 3
            right = round((index + 1) * sheet.width / 5) - 3
            view = sheet.crop((left, 3, right, sheet.height - 3))
            self._validate_view(direction, view)
            path = output_dir / f"{direction}.png"
            view.save(path, format="PNG")
            views[direction] = path
            output_evidence[direction] = {
                "path": str(path),
                "width_px": view.width,
                "height_px": view.height,
                "sha256": _sha256(path),
            }
        lineage_path = output_dir / "lineage.json"
        lineage = {
            "schema_version": 1,
            "layout_version": LAYOUT_VERSION,
            "generation_attempt": generation_attempt,
            "source_sheet": str(sheet_path),
            "source_sheet_sha256": _sha256(sheet_path),
            "source_manifest": str(source_manifest),
            "source_manifest_sha256": _sha256(source_manifest),
            "directions": list(REQUIRED_DIRECTIONS),
            "outputs": output_evidence,
        }
        lineage_path.write_text(json.dumps(lineage, indent=2), encoding="utf-8")
        return SplitResult(views, lineage_path)

    def _validate_view(self, direction: str, view: Image.Image) -> None:
        if view.width < self.minimum_width or view.height < self.minimum_height:
            raise ValueError(f"{direction} view is below minimum dimensions")
        grayscale = view.convert("L")
        extrema = cast(tuple[int, int], grayscale.getextrema())
        variance = ImageStat.Stat(grayscale).var[0]
        if extrema is None or extrema[1] - extrema[0] < 8 or variance < 4:
            raise ValueError(f"{direction} view has no meaningful content")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
