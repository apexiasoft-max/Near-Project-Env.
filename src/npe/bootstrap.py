"""Composition root shared by API, worker, and desktop processes."""

from __future__ import annotations

from dataclasses import dataclass

from npe.application.health import HealthService
from npe.application.workflow import WalkingSkeletonService
from npe.infrastructure.database import Database
from npe.shared.config import Settings, load_settings


@dataclass(frozen=True)
class Container:
    settings: Settings
    database: Database
    health: HealthService
    workflow: WalkingSkeletonService


def bootstrap(settings: Settings | None = None) -> Container:
    active = load_settings() if settings is None else settings
    active.validate()
    active.paths.initialize()
    database = Database(active.paths.database)
    database.migrate()
    return Container(
        active, database, HealthService(active, database),
        WalkingSkeletonService(active, database),
    )
