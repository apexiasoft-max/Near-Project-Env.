"""Create a tighter, higher-contrast Hunyuan detection retry image."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps


def subject_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    edges = ImageOps.grayscale(image).filter(ImageFilter.FIND_EDGES)
    mask = edges.point(lambda value: 255 if value >= 18 else 0)
    width, height = image.size
    border = min(3, max(1, min(width, height) // 20))
    draw = ImageDraw.Draw(mask)
    draw.rectangle((0, 0, width - 1, border - 1), fill=0)
    draw.rectangle((0, height - border, width - 1, height - 1), fill=0)
    draw.rectangle((0, 0, border - 1, height - 1), fill=0)
    draw.rectangle((width - border, 0, width - 1, height - 1), fill=0)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("No subject edges detected")
    left, top, right, bottom = bbox
    pad_x = max(4, int((right - left) * 0.08))
    pad_y = max(4, int((bottom - top) * 0.08))
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(width, right + pad_x),
        min(height, bottom + pad_y),
    )


def prepare(
    source: Path,
    target: Path,
    size: int = 768,
    manual_crop: tuple[int, int, int, int] | None = None,
) -> None:
    with Image.open(source).convert("RGB") as image:
        if manual_crop is not None:
            image = image.crop(manual_crop)
        crop = ImageOps.autocontrast(image.crop(subject_bbox(image)), cutoff=1)
        # Generated sheets may carry a second studio backdrop inside the crop.
        # Remove only background regions connected to the crop edges so the
        # final Hunyuan input has one uniform backdrop, not a nested rectangle.
        replacement = (72, 76, 82)
        for seed in (
            (0, 0),
            (crop.width - 1, 0),
            (0, crop.height - 1),
            (crop.width - 1, crop.height - 1),
        ):
            ImageDraw.floodfill(crop, seed, replacement, thresh=38)
        target_extent = int(size * 0.86)
        scale = min(target_extent / crop.width, target_extent / crop.height)
        crop = crop.resize(
            (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
            Image.Resampling.LANCZOS,
        )
        canvas = Image.new("RGB", (size, size), (72, 76, 82))
        x = (size - crop.width) // 2
        y = (size - crop.height) // 2
        canvas.paste(crop, (x, y))
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--size", type=int, default=768)
    parser.add_argument(
        "--crop",
        help="Optional source crop as left,top,right,bottom before subject detection",
    )
    args = parser.parse_args()
    crop = tuple(int(value) for value in args.crop.split(",")) if args.crop else None
    if crop is not None and len(crop) != 4:
        parser.error("--crop requires left,top,right,bottom")
    prepare(args.source, args.target, args.size, crop)


if __name__ == "__main__":
    main()
