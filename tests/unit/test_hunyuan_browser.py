from __future__ import annotations

from pathlib import Path

import pytest

from npe.infrastructure.hunyuan_browser import HunyuanBrowserAdapter, classify_hunyuan_state
from npe.shared.config import AppPaths, Settings


def adapter_at(root: Path) -> HunyuanBrowserAdapter:
    return HunyuanBrowserAdapter(
        Settings(paths=AppPaths.under(root), minimum_free_disk_bytes=0)
    )


def test_view_files_accepts_supported_directional_extensions(tmp_path: Path) -> None:
    views = tmp_path / "views"
    views.mkdir()
    for index, direction in enumerate(("top", "front", "left", "right", "back")):
        suffix = ".jpg" if index == 0 else ".png"
        (views / f"{direction}{suffix}").write_bytes(b"image")

    files = adapter_at(tmp_path / "data")._view_files(views)

    assert set(files) == {"top", "front", "left", "right", "back"}
    assert all(path.is_absolute() for path in files.values())


def test_submit_rejects_invalid_minimum_before_opening_browser(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 1 and 5"):
        adapter_at(tmp_path / "data").submit("RUN-1", tmp_path, minimum_views=0)


@pytest.mark.parametrize(
    ("url", "body", "expected"),
    [
        ("https://3d.hunyuanglobal.com/login", "", ("intervention", "logout")),
        ("https://3d.hunyuanglobal.com/", "Verify you are human", ("intervention", "captcha")),
        ("https://3d.hunyuanglobal.com/", "Model generating", ("processing", None)),
        ("https://3d.hunyuanglobal.com/", "Download FBX", ("completed", None)),
        ("https://3d.hunyuanglobal.com/", "Task failed", ("failed", "provider_failed")),
    ],
)
def test_provider_state_classification(
    url: str, body: str, expected: tuple[str, str | None]
) -> None:
    assert classify_hunyuan_state(url, body) == expected
