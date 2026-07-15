from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_detection_retry.py"
SPEC = importlib.util.spec_from_file_location("prepare_detection_retry", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DetectionRetryTests(unittest.TestCase):
    def test_prepare_outputs_square_dark_canvas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            target = root / "target.png"
            image = Image.new("RGB", (300, 500), (195, 195, 195))
            draw = ImageDraw.Draw(image)
            draw.rectangle((60, 160, 240, 360), fill=(245, 245, 245), outline=(40, 40, 40), width=4)
            image.save(source)

            MODULE.prepare(source, target, size=256)

            with Image.open(target) as result:
                self.assertEqual(result.size, (256, 256))
                self.assertEqual(result.getpixel((0, 0)), (72, 76, 82))

    def test_subject_bbox_rejects_flat_image(self) -> None:
        image = Image.new("RGB", (100, 100), (128, 128, 128))
        with self.assertRaises(ValueError):
            MODULE.subject_bbox(image)


if __name__ == "__main__":
    unittest.main()
