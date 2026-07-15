from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "hunyuan_view_mapping.py"
SPEC = importlib.util.spec_from_file_location("hunyuan_view_mapping", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HunyuanViewMappingTests(unittest.TestCase):
    def test_slot_contract(self) -> None:
        self.assertEqual(
            MODULE.VIEW_INPUT_INDEX,
            {"top": 0, "front": 2, "left": 4, "right": 5, "back": 6},
        )

    def test_expected_files_rejects_missing_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for direction in ("top", "front", "left", "right"):
                (root / f"{direction}.png").write_bytes(b"fixture")
            with self.assertRaises(FileNotFoundError) as context:
                MODULE.expected_view_files(root)
            self.assertIn("back.png", str(context.exception))

    def test_expected_files_returns_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for direction in MODULE.VIEW_INPUT_INDEX:
                (root / f"{direction}.png").write_bytes(b"fixture")
            result = MODULE.expected_view_files(root)
            self.assertEqual(set(result), set(MODULE.VIEW_INPUT_INDEX))
            self.assertTrue(all(path.is_absolute() for path in result.values()))


if __name__ == "__main__":
    unittest.main()
