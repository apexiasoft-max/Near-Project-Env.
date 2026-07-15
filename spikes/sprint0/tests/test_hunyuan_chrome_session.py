from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "hunyuan_chrome_session.py"
SPEC = importlib.util.spec_from_file_location("hunyuan_chrome_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HunyuanChromeSessionTests(unittest.TestCase):
    def test_candidates_use_standard_windows_roots(self) -> None:
        candidates = MODULE.chrome_candidates(
            {"PROGRAMFILES": "C:/PF", "PROGRAMFILES(X86)": "C:/PF86", "LOCALAPPDATA": "C:/Local"}
        )
        self.assertEqual(len(candidates), 3)
        self.assertTrue(all(path.name == "chrome.exe" for path in candidates))

    def test_launch_command_has_cdp_but_no_automation_flag(self) -> None:
        args = MODULE.build_launch_args(
            Path("C:/Chrome/chrome.exe"), Path("C:/Profile"), "https://example.com", 9222
        )
        self.assertIn("--remote-debugging-port=9222", args)
        self.assertFalse(any("automation" in value.lower() for value in args))
        self.assertFalse(any("no-sandbox" in value.lower() for value in args))

    def test_invalid_debugging_port_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.build_launch_args(Path("chrome.exe"), Path("profile"), "https://example.com", 0)


if __name__ == "__main__":
    unittest.main()
