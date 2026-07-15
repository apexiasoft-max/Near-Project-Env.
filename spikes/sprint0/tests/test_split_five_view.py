import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "split_five_view.py"
SPEC = importlib.util.spec_from_file_location("split_five_view", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


class SplitFiveViewTests(unittest.TestCase):
    def test_splits_ordered_panels_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sheet.png"
            Image.new("RGB", (503, 200), "white").save(source)
            manifest = module.split_sheet(source, root / "out", header_ratio=0.1)

            self.assertEqual(manifest["order"], ["front", "back", "left", "right", "top"])
            self.assertEqual(len(manifest["outputs"]), 5)
            self.assertTrue((root / "out" / "manifest.json").exists())
            self.assertTrue(all(item["height"] == 180 for item in manifest["outputs"]))

    def test_rejects_invalid_header_ratio(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sheet.png"
            Image.new("RGB", (500, 200), "white").save(source)
            with self.assertRaisesRegex(ValueError, "header_ratio"):
                module.split_sheet(source, Path(directory) / "out", header_ratio=0.5)


if __name__ == "__main__":
    unittest.main()

