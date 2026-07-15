"""Disposable Hunyuan browser proof using a dedicated persistent Chrome profile.

This script deliberately uses Playwright's full ``set_input_files`` API so no
native Windows file picker is involved. The profile directory must stay local
and must never be committed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from playwright.sync_api import Page, sync_playwright

from hunyuan_view_mapping import VIEW_INPUT_INDEX, expected_view_files
from hunyuan_chrome_session import build_launch_args, find_chrome
from browser_failure_states import BrowserSignals, classify_failure


HUNYUAN_URL = "https://3d.hunyuanglobal.com/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("login", "upload"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--views", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--hold-seconds", type=int, default=300)
    parser.add_argument("--debugging-port", type=int, default=9222)
    return parser.parse_args()


def open_multi_view_dialog(page: Page) -> None:
    page.get_by_text("Image-to-3D", exact=True).click()
    page.get_by_text("Multiple Images", exact=True).click()
    if page.get_by_role("heading", name="Add Multiple Views").count() == 0:
        page.locator("button").filter(has=page.locator("svg")).first.click()
    page.get_by_role("heading", name="Add Multiple Views").wait_for(state="visible")


def upload_views(page: Page, views_dir: Path) -> dict[str, object]:
    files = expected_view_files(views_dir)
    open_multi_view_dialog(page)
    inputs = page.locator('input[type="file"]')
    input_count = inputs.count()
    if input_count != 8:
        failure = classify_failure(
            BrowserSignals(
                url=page.url,
                visible_text=page.locator("body").inner_text()[:4000],
                expected_selector_count=0,
            )
        )
        raise RuntimeError(
            f"{failure}: expected 8 Hunyuan view inputs, found {input_count}"
        )

    uploaded: dict[str, str] = {}
    for direction, index in VIEW_INPUT_INDEX.items():
        inputs.nth(index).set_input_files(str(files[direction]))
        uploaded[direction] = str(files[direction])

    page.wait_for_timeout(4_000)
    failures = page.get_by_text("Detection failed", exact=True).count()
    return {
        "uploaded": uploaded,
        "input_count": input_count,
        "detection_failures": failures,
        "generate_enabled": page.get_by_role("button", name="Generate Now").is_enabled(),
    }


def main() -> None:
    args = parse_args()
    args.profile.mkdir(parents=True, exist_ok=True)
    if args.mode == "login":
        chrome = find_chrome()
        command = build_launch_args(chrome, args.profile, HUNYUAN_URL, args.debugging_port)
        subprocess.Popen(command, close_fds=True)
        print(
            json.dumps(
                {
                    "status": "normal_chrome_login_window_open",
                    "profile": str(args.profile.resolve()),
                    "cdp_url": f"http://127.0.0.1:{args.debugging_port}",
                    "note": "Keep this Chrome window open after manual login.",
                },
                indent=2,
            )
        )
        return

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{args.debugging_port}"
        )
        if not browser.contexts:
            raise RuntimeError("Chrome CDP connection has no browser context")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        if "hunyuanglobal.com" not in page.url:
            page.goto(HUNYUAN_URL, wait_until="domcontentloaded")
        if args.views is None:
            raise ValueError("--views is required in upload mode")
        result = upload_views(page, args.views)
        if args.evidence:
            args.evidence.parent.mkdir(parents=True, exist_ok=True)
            args.evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
            page.screenshot(path=str(args.evidence.with_suffix(".png")), full_page=True)
        print(json.dumps(result, indent=2))
        time.sleep(10)
        browser.close()


if __name__ == "__main__":
    main()
