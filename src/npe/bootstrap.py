"""Composition root shared by API, worker, and desktop processes."""

from __future__ import annotations

from dataclasses import dataclass

from npe.application.approvals import ApprovalService
from npe.application.health import HealthService
from npe.application.inventory import InventoryService
from npe.application.project_lifecycle import ProjectLifecycleService
from npe.application.workflow import WalkingSkeletonService
from npe.infrastructure.database import Database
from npe.infrastructure.hunyuan_browser import HunyuanBrowserAdapter
from npe.shared.config import Settings, load_settings


@dataclass(frozen=True)
class Container:
    settings: Settings
    database: Database
    health: HealthService
    workflow: WalkingSkeletonService
    hunyuan: HunyuanBrowserAdapter
    lifecycle: ProjectLifecycleService
    approvals: ApprovalService
    inventory: InventoryService


def bootstrap(settings: Settings | None = None) -> Container:
    active = load_settings() if settings is None else settings
    active.validate()
    active.paths.initialize()
    database = Database(active.paths.database)
    database.migrate()
    health = HealthService(active, database)
    return Container(
        active, database, health, WalkingSkeletonService(active, database),
        HunyuanBrowserAdapter(active), ProjectLifecycleService(database, health),
        ApprovalService(database),
        InventoryService(active, database),
    )
