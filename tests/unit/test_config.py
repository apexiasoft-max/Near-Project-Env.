from __future__ import annotations

from pathlib import Path

import pytest

from npe.shared.config import AppPaths, Settings


def test_paths_are_initialized_under_one_root(tmp_path: Path) -> None:
    paths = AppPaths.under(tmp_path / "data")
    paths.initialize()
    assert paths.database.parent == paths.root
    assert paths.browser_profile.is_dir()
    assert paths.downloads.is_dir()


def test_non_loopback_api_host_is_rejected(tmp_path: Path) -> None:
    settings = Settings(paths=AppPaths.under(tmp_path), api_host="0.0.0.0")
    with pytest.raises(ValueError, match="loopback"):
        settings.validate()

