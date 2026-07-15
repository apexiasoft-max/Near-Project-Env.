from __future__ import annotations

import sys

from npe.main import component_command


def test_development_component_commands_use_module_entrypoints() -> None:
    assert component_command("api") == [sys.executable, "-m", "npe.api.app"]
    assert component_command("worker") == [sys.executable, "-m", "npe.worker.runner"]
    assert component_command("desktop") == [sys.executable, "-m", "npe.desktop.app"]

