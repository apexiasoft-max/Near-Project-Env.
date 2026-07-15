"""Build a normal Chrome launch command for a local CDP session."""

from __future__ import annotations

import os
from pathlib import Path


def chrome_candidates(environment: dict[str, str] | None = None) -> list[Path]:
    env = environment or os.environ
    roots = [env.get("PROGRAMFILES"), env.get("PROGRAMFILES(X86)"), env.get("LOCALAPPDATA")]
    return [
        Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe"
        for root in roots
        if root
    ]


def find_chrome(environment: dict[str, str] | None = None) -> Path:
    for candidate in chrome_candidates(environment):
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("Google Chrome was not found in the standard Windows locations")


def build_launch_args(
    chrome: Path,
    profile: Path,
    url: str,
    debugging_port: int,
) -> list[str]:
    if not 1 <= debugging_port <= 65535:
        raise ValueError("debugging_port must be between 1 and 65535")
    return [
        str(chrome.resolve()),
        f"--user-data-dir={profile.resolve()}",
        f"--remote-debugging-port={debugging_port}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]
