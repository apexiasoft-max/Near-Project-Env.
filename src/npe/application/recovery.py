"""Durable stage checkpoints, atomic artifacts and restart reconciliation."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from npe.domain.workflow import JobStage
from npe.infrastructure.database import Database


@dataclass(frozen=True)
class StageAttempt:
    id: str
    run_id: str
    stage: str
    attempt: int
    status: str
    correlation_id: str


class AtomicArtifactWriter:
    def write(
        self, target: Path, content: bytes,
        validator: Callable[[Path], bool] | None = None,
    ) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f"{target.name}.partial")
        try:
            with partial.open("wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if validator is not None and not validator(partial):
                raise ValueError("Artifact validation failed")
            partial.replace(target)
            return target
        except BaseException:
            partial.unlink(missing_ok=True)
            raise


class WorkflowRecoveryService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def begin(
        self, run_id: str, stage: str, detail: dict[str, object] | None = None,
    ) -> StageAttempt:
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            job = connection.execute(
                "SELECT id, correlation_id FROM jobs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if job is None:
                raise KeyError(run_id)
            row = connection.execute(
                """SELECT COALESCE(MAX(attempt), 0) FROM stage_attempts
                   WHERE job_id = ? AND stage = ?""",
                (job["id"], stage),
            ).fetchone()
            attempt_number = int(row[0]) + 1
            attempt_id = f"ATT-{uuid4().hex[:10].upper()}"
            correlation_id = str(job["correlation_id"] or run_id)
            connection.execute(
                """INSERT INTO stage_attempts
                   (id, job_id, run_id, stage, attempt, status, correlation_id,
                    detail_json, started_at)
                   VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)""",
                (
                    attempt_id, job["id"], run_id, stage, attempt_number,
                    correlation_id, json.dumps(detail or {}, sort_keys=True), now,
                ),
            )
        return StageAttempt(
            attempt_id, run_id, stage, attempt_number, "running", correlation_id
        )

    def finish(
        self, attempt_id: str, status: str = "completed",
        detail: dict[str, object] | None = None,
    ) -> None:
        if status not in {"completed", "failed", "needs_review"}:
            raise ValueError("Invalid terminal attempt status")
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE stage_attempts SET status = ?, detail_json = ?, finished_at = ?
                   WHERE id = ? AND status = 'running'""",
                (status, json.dumps(detail or {}, sort_keys=True), now, attempt_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Attempt is not running")

    def reconcile(self) -> list[str]:
        """Mark abandoned operations recoverable without changing their safe stage."""
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, run_id FROM stage_attempts WHERE status = 'running'"
            ).fetchall()
            run_ids = sorted({str(row["run_id"]) for row in rows})
            for row in rows:
                connection.execute(
                    """UPDATE stage_attempts SET status = 'interrupted', finished_at = ?
                       WHERE id = ?""",
                    (now, row["id"]),
                )
            for run_id in run_ids:
                connection.execute(
                    """UPDATE jobs SET status = 'recoverable', last_error = ?, updated_at = ?
                       WHERE run_id = ? AND stage != ?""",
                    ("interrupted external operation", now, run_id, JobStage.COMPLETED),
                )
        return run_ids

    def resume(self, run_id: str) -> JobStage:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT stage, status FROM jobs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise KeyError(run_id)
            stage = JobStage(str(row["stage"]))
            if stage == JobStage.COMPLETED:
                return stage
            connection.execute(
                """UPDATE jobs SET status = 'active', last_error = NULL, updated_at = ?
                   WHERE run_id = ?""",
                (datetime.now(UTC).isoformat(), run_id),
            )
        return stage
