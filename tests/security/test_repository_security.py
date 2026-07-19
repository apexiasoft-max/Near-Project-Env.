from __future__ import annotations

import re
import subprocess
from pathlib import Path


def test_tracked_text_does_not_contain_known_secret_shapes() -> None:
    root = Path(__file__).parents[2]
    names = subprocess.run(
        ["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    patterns = (
        re.compile("A" + "A[EF][A-Za-z0-9_-]{30,}"),
        re.compile("sk" + r"-[A-Za-z0-9_-]{20,}"),
        re.compile(
            r"(?i)(telegram_bot_token|api_key)[ \t]*=[ \t]*[\"']?[A-Za-z0-9_-]{20,}"
        ),
    )
    violations: list[str] = []
    for name in names:
        path = root / name
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(content) for pattern in patterns):
            violations.append(name)
    assert violations == []
