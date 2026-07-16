"""Minimal ChatGPT web adapter for five-view image generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Error, Page, TimeoutError, sync_playwright

from npe.application.five_view_generation import TransientGenerationError
from npe.shared.config import Settings

CHATGPT_URL = "https://chatgpt.com/"


class ChatGPTBrowserAdapter:
    """Keep volatile ChatGPT selectors inside one replaceable page adapter."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._playwright: Any | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def open(self) -> Page:
        if self._context is None:
            self._playwright = sync_playwright().start()
            try:
                self._browser = self._playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9223"
                )
                if not self._browser.contexts:
                    raise RuntimeError("Dedicated Chrome has no browser context")
                self._context = self._browser.contexts[0]
            except Error:
                self._context = self._playwright.chromium.launch_persistent_context(
                    str(self.settings.paths.browser_profile),
                    channel="chrome",
                    headless=False,
                    no_viewport=True,
                    args=[
                        "--remote-debugging-port=9223",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
        page = self._chatgpt_page()
        page.bring_to_front()
        return page

    def generate(
        self, prompt: str, references: tuple[Path, ...], output_path: Path,
    ) -> dict[str, object]:
        page = self.open()
        page.goto(CHATGPT_URL, wait_until="domcontentloaded")
        try:
            self._raise_session_failure(page)
            existing = page.locator('img[alt^="Generated image:"]').count()
            self._upload(page, references)
            composer = page.get_by_role("textbox", name="Chat with ChatGPT")
            composer.fill(prompt)
            page.get_by_role("button", name="Send prompt", exact=True).click()
            generated = page.locator('img[alt^="Generated image:"]')
            page.wait_for_function(
                "([selector, count]) => document.querySelectorAll(selector).length > count",
                arg=['img[alt^="Generated image:"]', existing],
                timeout=180_000,
            )
            image = generated.nth(existing)
            source = image.get_attribute("src")
            if not source:
                raise TransientGenerationError("generated image has no source")
            assert self._context is not None
            response = self._context.request.get(source, timeout=60_000)
            if not response.ok:
                raise TransientGenerationError(
                    f"generated image download failed: HTTP {response.status}"
                )
            output_path.write_bytes(response.body())
            return {
                "page_health": "ready",
                "reference_count": len(references),
                "capture_method": "authenticated_asset_request",
                "content_type": response.headers.get("content-type"),
            }
        except TimeoutError as error:
            raise TransientGenerationError("generation timed out") from error
        except Error as error:
            raise TransientGenerationError(f"browser automation failed: {error}") from error

    def _chatgpt_page(self) -> Page:
        assert self._context is not None
        for page in self._context.pages:
            if "chatgpt.com" in page.url:
                return page
        return self._context.new_page()

    @staticmethod
    def _upload(page: Page, references: tuple[Path, ...]) -> None:
        with page.expect_file_chooser() as chooser:
            page.get_by_role("button", name="Add files and more", exact=True).click()
            page.get_by_text("Upload from computer", exact=True).click()
        chooser.value.set_files([str(path.resolve()) for path in references])

    @staticmethod
    def _raise_session_failure(page: Page) -> None:
        text = page.locator("body").inner_text().casefold()
        if "verify you are human" in text or "captcha" in text:
            raise RuntimeError("captcha")
        if "log in" in text and page.get_by_role("button", name="Log in").count():
            raise RuntimeError("logout")
