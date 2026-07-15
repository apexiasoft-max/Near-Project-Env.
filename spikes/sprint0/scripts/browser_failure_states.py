"""Deterministic failure classification for the Sprint 0 browser spike."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserSignals:
    url: str
    visible_text: str = ""
    expected_selector_count: int | None = None
    timed_out: bool = False
    upload_failed: bool = False
    download_failed: bool = False
    output_count: int | None = None
    expected_output_count: int | None = None


def classify_failure(signals: BrowserSignals) -> str | None:
    """Return one stable failure code, ordered by actionable precedence."""

    text = signals.visible_text.casefold()
    url = signals.url.casefold()
    if "captcha" in text or "verify you are human" in text:
        return "captcha"
    if "send verification code is restricted" in text:
        return "verification_throttled"
    if any(token in url for token in ("login", "sign-in", "signin")) or any(
        token in text for token in ("log in", "sign in", "session expired")
    ):
        return "logout"
    if signals.timed_out:
        return "timeout"
    if signals.expected_selector_count == 0:
        return "selector_changed"
    if signals.upload_failed:
        return "upload_failure"
    if signals.download_failed:
        return "download_failure"
    if signals.output_count is not None and signals.expected_output_count is not None:
        if signals.output_count == 0:
            return "no_output"
        if signals.output_count < signals.expected_output_count:
            return "incomplete_output"
    return None
