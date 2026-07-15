"""Typed, local-only application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True)
class AppPaths:
    root: Path
    database: Path
    projects: Path
    logs: Path
    runtime: Path
    browser_profile: Path
    browser_traces: Path
    downloads: Path

    @classmethod
    def under(cls, root: Path) -> AppPaths:
        resolved = root.expanduser().resolve()
        return cls(
            root=resolved,
            database=resolved / "app.db",
            projects=resolved / "projects",
            logs=resolved / "logs",
            runtime=resolved / "runtime",
            browser_profile=resolved / "browser-profile",
            browser_traces=resolved / "browser-traces",
            downloads=resolved / "downloads",
        )

    def initialize(self) -> None:
        for directory in (
            self.root,
            self.projects,
            self.logs,
            self.runtime,
            self.browser_profile,
            self.browser_traces,
            self.downloads,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    paths: AppPaths
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    worker_stale_after_seconds: int = 15
    minimum_free_disk_bytes: int = 2 * 1024**3
    blender_path: Path | None = None

    def validate(self) -> None:
        if self.api_host not in LOOPBACK_HOSTS:
            raise ValueError("API host must be loopback-only")
        if not 1 <= self.api_port <= 65535:
            raise ValueError("API port must be between 1 and 65535")


def default_data_root() -> Path:
    override = os.environ.get("NPE_DATA_ROOT")
    if override:
        return Path(override)
    program_data = os.environ.get("PROGRAMDATA")
    if program_data:
        return Path(program_data) / "NearProjectEnvironment"
    return Path.home() / ".near-project-environment"


def load_settings() -> Settings:
    blender = os.environ.get("NPE_BLENDER_PATH")
    settings = Settings(
        paths=AppPaths.under(default_data_root()),
        api_host=os.environ.get("NPE_API_HOST", "127.0.0.1"),
        api_port=int(os.environ.get("NPE_API_PORT", "8765")),
        blender_path=Path(blender) if blender else None,
    )
    settings.validate()
    return settings
