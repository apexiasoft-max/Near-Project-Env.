"""Composition root shared by API, worker, and desktop processes."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from npe.application.approvals import ApprovalService
from npe.application.delivery import DeliveryPackageService
from npe.application.five_view_generation import FiveViewGenerationService
from npe.application.five_view_review import FiveViewReviewService
from npe.application.health import HealthService
from npe.application.height import HeightService
from npe.application.inventory import InventoryService
from npe.application.manual_pool import ManualPoolService
from npe.application.operations import DiagnosticsService, PrerequisiteService, UpgradeService
from npe.application.pilots import PilotEvidenceService
from npe.application.project_lifecycle import ProjectLifecycleService
from npe.application.recovery import WorkflowRecoveryService
from npe.application.reference_review import ReferenceReviewService
from npe.application.references import ReferenceService
from npe.application.reliability import ProviderLockService, RetryExecutor
from npe.application.workflow import WalkingSkeletonService
from npe.infrastructure.chatgpt_browser import ChatGPTBrowserAdapter
from npe.infrastructure.credential_store import TELEGRAM_TOKEN_TARGET, WindowsCredentialStore
from npe.infrastructure.database import Database
from npe.infrastructure.hunyuan_browser import HunyuanBrowserAdapter
from npe.infrastructure.telegram import TelegramNotifier
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
    height: HeightService
    references: ReferenceService
    manual_pool: ManualPoolService
    reference_review: ReferenceReviewService
    telegram: TelegramNotifier
    five_view_generation: FiveViewGenerationService
    five_view_review: FiveViewReviewService
    recovery: WorkflowRecoveryService
    retry: RetryExecutor
    provider_locks: ProviderLockService
    delivery: DeliveryPackageService
    prerequisites: PrerequisiteService
    upgrade: UpgradeService
    diagnostics: DiagnosticsService
    pilots: PilotEvidenceService


def bootstrap(settings: Settings | None = None) -> Container:
    active = load_settings() if settings is None else settings
    active.validate()
    active.paths.initialize()
    database = Database(active.paths.database)
    database.migrate()
    health = HealthService(active, database)
    telegram_token = active.telegram_bot_token or WindowsCredentialStore().read(
        TELEGRAM_TOKEN_TARGET
    )
    return Container(
        active, database, health, WalkingSkeletonService(active, database),
        HunyuanBrowserAdapter(active), ProjectLifecycleService(database, health),
        approvals := ApprovalService(database),
        InventoryService(active, database, approvals),
        HeightService(database),
        ReferenceService(database),
        ManualPoolService(active, database),
        ReferenceReviewService(database, approvals),
        TelegramNotifier(
            database, telegram_token, active.telegram_chat_id,
            proxy_url=active.telegram_proxy_url,
        ),
        FiveViewGenerationService(
            active,
            ChatGPTBrowserAdapter(active),
            lambda: f"RUN-{uuid4().hex[:12].upper()}",
        ),
        FiveViewReviewService(database),
        recovery := WorkflowRecoveryService(database),
        RetryExecutor(database, recovery),
        ProviderLockService(database),
        DeliveryPackageService(active, database),
        PrerequisiteService(),
        UpgradeService(active, database),
        DiagnosticsService(active, database, health),
        PilotEvidenceService(active),
    )
