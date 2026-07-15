from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "browser_failure_states.py"
SPEC = importlib.util.spec_from_file_location("browser_failure_states", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BrowserFailureStateTests(unittest.TestCase):
    def signals(self, **kwargs):
        return MODULE.BrowserSignals(url="https://example.test", **kwargs)

    def test_distinguishes_required_session_failures(self) -> None:
        self.assertEqual(
            MODULE.classify_failure(self.signals(visible_text="Verify you are human CAPTCHA")),
            "captcha",
        )
        self.assertEqual(
            MODULE.classify_failure(MODULE.BrowserSignals(url="https://example.test/login")),
            "logout",
        )
        self.assertEqual(MODULE.classify_failure(self.signals(timed_out=True)), "timeout")
        self.assertEqual(
            MODULE.classify_failure(self.signals(expected_selector_count=0)),
            "selector_changed",
        )

    def test_distinguishes_transfer_and_output_failures(self) -> None:
        self.assertEqual(
            MODULE.classify_failure(self.signals(upload_failed=True)), "upload_failure"
        )
        self.assertEqual(
            MODULE.classify_failure(self.signals(download_failed=True)), "download_failure"
        )
        self.assertEqual(
            MODULE.classify_failure(self.signals(output_count=0, expected_output_count=5)),
            "no_output",
        )
        self.assertEqual(
            MODULE.classify_failure(self.signals(output_count=4, expected_output_count=5)),
            "incomplete_output",
        )

    def test_verification_throttle_is_not_generic_logout(self) -> None:
        self.assertEqual(
            MODULE.classify_failure(
                self.signals(visible_text="Send verification code is restricted")
            ),
            "verification_throttled",
        )
