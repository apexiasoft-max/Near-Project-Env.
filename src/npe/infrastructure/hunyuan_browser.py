"""Hunyuan browser adapter backed by a dedicated persistent Chrome profile."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from playwright.sync_api import BrowserContext, Page, sync_playwright

from npe.shared.config import Settings

HUNYUAN_URL: Final = "https://3d.hunyuanglobal.com/"
VIEW_INPUT_INDEX: Final = {"top": 0, "front": 2, "left": 4, "right": 5, "back": 6}


@dataclass(frozen=True)
class HunyuanSubmission:
    run_id: str
    accepted_views: int
    detection_failures: int
    generation_started: bool
    failure_code: str | None
    evidence_json: Path
    screenshot: Path


class HunyuanBrowserAdapter:
    """Own the minimum browser behavior needed by the Sprint 1 walking skeleton."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._playwright: Any | None = None
        self._context: BrowserContext | None = None

    def open(self) -> Page:
        if self._context is None:
            self._playwright = sync_playwright().start()
            self._context = self._playwright.chromium.launch_persistent_context(
                str(self.settings.paths.browser_profile),
                channel="chrome",
                headless=False,
                no_viewport=True,
                args=["--no-first-run", "--no-default-browser-check"],
            )
        page = self._hunyuan_page()
        page.bring_to_front()
        return page

    def submit(self, run_id: str, views_dir: Path, minimum_views: int = 3) -> HunyuanSubmission:
        if not 1 <= minimum_views <= len(VIEW_INPUT_INDEX):
            raise ValueError("minimum_views must be between 1 and 5")
        files = self._view_files(views_dir)
        page = self.open()
        page.goto(HUNYUAN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2_000)
        self._raise_session_failure(page)
        self._open_multi_view_dialog(page)
        inputs = page.locator('input[type="file"]')
        if inputs.count() != 8:
            raise RuntimeError(f"selector_changed: expected 8 inputs, found {inputs.count()}")
        for direction, index in VIEW_INPUT_INDEX.items():
            inputs.nth(index).set_input_files(str(files[direction]))
        page.wait_for_timeout(5_000)
        self._raise_session_failure(page)
        failures = page.get_by_text("Detection failed", exact=True).count()
        accepted = len(VIEW_INPUT_INDEX) - failures
        generate = page.get_by_role("button", name="Generate Now")
        started = accepted >= minimum_views and generate.is_enabled()
        if started:
            generate.click()
            page.wait_for_timeout(1_500)
        failure_code = None if started else "insufficient_accepted_views"
        return self._write_evidence(page, run_id, accepted, failures, started, failure_code)

    def _hunyuan_page(self) -> Page:
        assert self._context is not None
        for page in self._context.pages:
            if "hunyuanglobal.com" in page.url:
                return page
        return self._context.new_page()

    @staticmethod
    def _open_multi_view_dialog(page: Page) -> None:
        page.get_by_text("Image-to-3D", exact=True).click()
        page.get_by_text("Multiple Images", exact=True).click()
        heading = page.get_by_role("heading", name="Add Multiple Views")
        if heading.count() == 0:
            page.locator("button").filter(has=page.locator("svg")).first.click()
        heading.wait_for(state="visible")

    @staticmethod
    def _raise_session_failure(page: Page) -> None:
        body = page.locator("body").inner_text().casefold()
        if "send verification code is restricted" in body:
            raise RuntimeError("verification_throttled")
        if "captcha" in body or "verify you are human" in body:
            raise RuntimeError("captcha")
        if any(token in page.url.casefold() for token in ("login", "signin", "sign-in")):
            raise RuntimeError("logout")

    @staticmethod
    def _view_files(views_dir: Path) -> dict[str, Path]:
        files: dict[str, Path] = {}
        for direction in VIEW_INPUT_INDEX:
            matches = [path for path in views_dir.glob(f"{direction}.*") if path.is_file()]
            if len(matches) != 1:
                raise FileNotFoundError(f"Expected one {direction} view in {views_dir}")
            files[direction] = matches[0].resolve()
        return files

    def _write_evidence(
        self, page: Page, run_id: str, accepted: int, failures: int,
        started: bool, failure_code: str | None,
    ) -> HunyuanSubmission:
        root = self.settings.paths.browser_traces / run_id
        root.mkdir(parents=True, exist_ok=True)
        screenshot = root / "submission.png"
        evidence = root / "submission.json"
        page.screenshot(path=str(screenshot), full_page=True)
        result = HunyuanSubmission(
            run_id, accepted, failures, started, failure_code, evidence, screenshot
        )
        payload = asdict(result)
        payload["recorded_at"] = datetime.now(UTC).isoformat()
        payload["evidence_json"] = str(evidence)
        payload["screenshot"] = str(screenshot)
        evidence.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return result
