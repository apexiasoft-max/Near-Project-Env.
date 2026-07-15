"""Pure helpers for mapping five-view artifacts to Hunyuan input slots."""

from __future__ import annotations

from pathlib import Path
from typing import Final


VIEW_INPUT_INDEX: Final = {
    "top": 0,
    "front": 2,
    "left": 4,
    "right": 5,
    "back": 6,
}


def expected_view_files(views_dir: Path) -> dict[str, Path]:
    result = {name: (views_dir / f"{name}.png").resolve() for name in VIEW_INPUT_INDEX}
    missing = [str(path) for path in result.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing view files: {missing}")
    return result
