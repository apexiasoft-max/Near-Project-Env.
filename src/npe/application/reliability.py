"""Central retry policy, failure isolation and provider ownership locks."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

from npe.application.recovery import WorkflowRecoveryService
from npe.infrastructure.database import Database

T = TypeVar("T")
MAX_ATTEMPTS = 2


class FailureKind(StrEnum):
    TRANSIENT = "transient"
    VALIDATION = "validation"
    INTERVENTION = "intervention"


class StageFailure(RuntimeError):
    def __init__(self, kind: FailureKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class RetryResult:
    value: object | None
    attempts: int
    status: str


class RetryExecutor:
    def __init__(
        self, database: Database, recovery: WorkflowRecoveryService,
        backoff: Callable[[int], None] | None = None,
    ) -> None:
        self.database = database
        self.recovery = recovery
        self.backoff = backoff or (lambda attempt: time.sleep(float(attempt)))

    def execute(self, run_id: str, stage: str, operation: Callable[[], T]) -> RetryResult:
        for number in range(1, MAX_ATTEMPTS + 1):
            attempt = self.recovery.begin(run_id, stage, {"policy_attempt": number})
            try:
                value = operation()
            except StageFailure as error:
                terminal = error.kind != FailureKind.TRANSIENT or number == MAX_ATTEMPTS
                status = "needs_review" if terminal else "failed"
                self.recovery.finish(
                    attempt.id, status,
                    {"kind": error.kind, "message": str(error), "policy_attempt": number},
                )
                if terminal:
                    self._needs_review(run_id, stage, error)
                    return RetryResult(None, number, "needs_review")
                self.backoff(number)
                continue
            self.recovery.finish(attempt.id, "completed", {"policy_attempt": number})
            return RetryResult(value, number, "completed")
        raise AssertionError("unreachable")

    def _needs_review(self, run_id: str, stage: str, error: StageFailure) -> None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT building_id FROM jobs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise KeyError(run_id)
            connection.execute(
                """UPDATE jobs SET status = 'needs_review', last_error = ?
                   WHERE run_id = ?""",
                (f"{stage}:{error.kind}:{error}", run_id),
            )
            connection.execute(
                "UPDATE buildings SET status = 'needs_review' WHERE id = ?",
                (row["building_id"],),
            )


class ProviderLockService:
    def __init__(self, database: Database, clock: Callable[[], float] = time.time) -> None:
        self.database = database
        self.clock = clock

    def acquire(self, provider: str, owner_id: str, lease_seconds: float = 120) -> bool:
        now = self.clock()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT owner_id, expires_at FROM provider_locks WHERE provider = ?",
                (provider,),
            ).fetchone()
            if row is not None and float(row["expires_at"]) > now:
                return str(row["owner_id"]) == owner_id
            connection.execute(
                """INSERT INTO provider_locks(provider, owner_id, acquired_at, expires_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(provider) DO UPDATE SET owner_id = excluded.owner_id,
                   acquired_at = excluded.acquired_at, expires_at = excluded.expires_at""",
                (provider, owner_id, now, now + lease_seconds),
            )
        return True

    def release(self, provider: str, owner_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM provider_locks WHERE provider = ? AND owner_id = ?",
                (provider, owner_id),
            )
        return cursor.rowcount == 1
