"""System health query for the desktop shell and API."""

from __future__ import annotations

import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from npe.infrastructure.database import Database
from npe.shared.config import Settings


@dataclass(frozen=True)
class ComponentHealth:
    status: str
    detail: str


@dataclass(frozen=True)
class HealthReport:
    status: str
    database: ComponentHealth
    disk: ComponentHealth
    worker: ComponentHealth
    browser: ComponentHealth
    blender: ComponentHealth

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class HealthService:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def inspect(self, now: float | None = None) -> HealthReport:
        current = time.time() if now is None else now
        database = ComponentHealth(
            "ok" if self.database.is_healthy() else "error",
            str(self.settings.paths.database),
        )
        free = shutil.disk_usage(self.settings.paths.root).free
        disk = ComponentHealth(
            "ok" if free >= self.settings.minimum_free_disk_bytes else "degraded",
            f"{free} bytes free",
        )
        worker = self._worker_health(current)
        browser = ComponentHealth(
            "ok" if self.settings.paths.browser_profile.is_dir() else "error",
            str(self.settings.paths.browser_profile),
        )
        blender = self._blender_health()
        components = (database, disk, worker, browser, blender)
        overall = "ok" if all(item.status == "ok" for item in components) else "degraded"
        return HealthReport(overall, database, disk, worker, browser, blender)

    def _worker_health(self, now: float) -> ComponentHealth:
        heartbeat = self.settings.paths.runtime / "worker.heartbeat"
        if not heartbeat.exists():
            return ComponentHealth("stopped", "worker heartbeat not found")
        try:
            lines = heartbeat.read_text(encoding="utf-8").splitlines()
            heartbeat_at = float(lines[1])
        except (IndexError, OSError, ValueError):
            return ComponentHealth("error", "worker heartbeat is invalid")
        age = max(0.0, now - heartbeat_at)
        status = "ok" if age <= self.settings.worker_stale_after_seconds else "stale"
        return ComponentHealth(status, f"heartbeat age {age:.1f}s")

    def _blender_health(self) -> ComponentHealth:
        configured = self.settings.blender_path
        if configured and configured.is_file():
            return ComponentHealth("ok", str(configured))
        discovered = shutil.which("blender")
        if discovered:
            return ComponentHealth("ok", discovered)
        for candidate in (
            Path("C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"),
            Path("C:/Program Files/Blender Foundation/Blender 4.5/blender.exe"),
            Path("C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"),
        ):
            if candidate.is_file():
                return ComponentHealth("ok", str(candidate))
        return ComponentHealth("unavailable", "configure NPE_BLENDER_PATH")
