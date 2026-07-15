from __future__ import annotations

from pathlib import Path

from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings
from npe.worker.runner import write_heartbeat


def test_health_reports_all_required_components(tmp_path: Path) -> None:
    settings = Settings(
        paths=AppPaths.under(tmp_path),
        minimum_free_disk_bytes=0,
        blender_path=tmp_path / "blender.exe",
    )
    settings.paths.initialize()
    settings.blender_path.write_bytes(b"")
    container = bootstrap(settings)
    write_heartbeat(settings.paths.runtime / "worker.heartbeat", timestamp=100.0)
    report = container.health.inspect(now=100.0).to_dict()
    assert report["database"]["status"] == "ok"
    assert report["disk"]["status"] == "ok"
    assert report["worker"]["status"] == "ok"
    assert report["browser"]["status"] == "ok"
    assert report["blender"]["status"] == "ok"
    assert report["status"] == "ok"


def test_stale_worker_is_distinct_from_stopped(tmp_path: Path) -> None:
    settings = Settings(paths=AppPaths.under(tmp_path), minimum_free_disk_bytes=0)
    container = bootstrap(settings)
    write_heartbeat(settings.paths.runtime / "worker.heartbeat", timestamp=10.0)
    report = container.health.inspect(now=100.0)
    assert report.worker.status == "stale"

