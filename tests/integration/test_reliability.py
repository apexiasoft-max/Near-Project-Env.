from __future__ import annotations

from pathlib import Path

from npe.application.reliability import FailureKind, StageFailure
from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings


def setup_job(tmp_path: Path):  # type: ignore[no-untyped-def]
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("P", 35.7, 51.4, 100, "B", 20)
    container.retry.backoff = lambda _attempt: None
    return container, job


def test_transient_failure_succeeds_on_second_and_records_attempts(tmp_path: Path) -> None:
    container, job = setup_job(tmp_path)
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise StageFailure(FailureKind.TRANSIENT, "network timeout")
        return "ok"

    result = container.retry.execute(job.run_id, "hunyuan_upload", operation)

    assert (result.value, result.attempts, result.status) == ("ok", 2, "completed")
    with container.database.connect() as connection:
        attempts = connection.execute(
            "SELECT status FROM stage_attempts WHERE run_id = ? ORDER BY attempt",
            (job.run_id,),
        ).fetchall()
    assert [row["status"] for row in attempts] == ["failed", "completed"]


def test_second_transient_failure_isolated_as_needs_review(tmp_path: Path) -> None:
    container, job = setup_job(tmp_path)

    def operation() -> None:
        raise StageFailure(FailureKind.TRANSIENT, "provider unavailable")

    result = container.retry.execute(job.run_id, "hunyuan_upload", operation)

    assert (result.attempts, result.status) == (2, "needs_review")
    with container.database.connect() as connection:
        stored = connection.execute(
            "SELECT status FROM jobs WHERE run_id = ?", (job.run_id,)
        ).fetchone()
    assert stored["status"] == "needs_review"


def test_validation_failure_does_not_retry(tmp_path: Path) -> None:
    container, job = setup_job(tmp_path)

    result = container.retry.execute(
        job.run_id,
        "view_validation",
        lambda: (_ for _ in ()).throw(
            StageFailure(FailureKind.VALIDATION, "invalid dimensions")
        ),
    )

    assert (result.attempts, result.status) == (1, "needs_review")


def test_provider_lock_is_single_owner_until_lease_expires(tmp_path: Path) -> None:
    container, _job = setup_job(tmp_path)
    now = 100.0
    container.provider_locks.clock = lambda: now

    assert container.provider_locks.acquire("hunyuan", "worker-a", 10)
    assert not container.provider_locks.acquire("hunyuan", "worker-b", 10)
    now = 111.0
    assert container.provider_locks.acquire("hunyuan", "worker-b", 10)
    assert not container.provider_locks.release("hunyuan", "worker-a")
    assert container.provider_locks.release("hunyuan", "worker-b")
