from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from npe.application.operations import REQUIRED_PACKAGES
from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings


def _container(tmp_path: Path):  # type: ignore[no-untyped-def]
    return bootstrap(
        Settings(
            paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0,
            telegram_bot_token="123456789:" + "THIS_IS_A_SECRET_TELEGRAM_TOKEN",
            telegram_chat_id="123456",
        )
    )


def test_prerequisites_pin_runtime_and_packages(tmp_path: Path) -> None:
    report = _container(tmp_path).prerequisites.inspect()
    checks = {item.name: item for item in report.checks}
    assert checks["python"].required == "3.12"
    assert set(REQUIRED_PACKAGES) <= checks.keys()
    assert all(item.installed for item in checks.values())


def test_upgrade_creates_integrity_checked_backup(tmp_path: Path) -> None:
    container = _container(tmp_path)
    container.workflow.create_job("Upgrade", 35.7, 51.4, 100, "B001", 20)

    receipt = container.upgrade.upgrade()

    assert receipt.backup_path.is_file()
    assert receipt.integrity == "ok"
    assert receipt.schema_version_after >= receipt.schema_version_before
    with sqlite3.connect(receipt.backup_path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1


def test_failed_migration_restores_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    container = _container(tmp_path)
    job = container.workflow.create_job("Rollback", 35.7, 51.4, 100, "B001", 20)

    def fail() -> None:
        with sqlite3.connect(container.database.path) as connection:
            connection.execute("DELETE FROM projects")
        raise RuntimeError("migration failed")

    monkeypatch.setattr(container.database, "migrate", fail)
    with pytest.raises(RuntimeError, match="migration failed"):
        container.upgrade.upgrade()
    with container.database.connect() as connection:
        row = connection.execute("SELECT id FROM projects").fetchone()
    assert row[0] == job.project_id


def test_diagnostics_redacts_secrets_and_has_actionable_manifest(tmp_path: Path) -> None:
    container = _container(tmp_path)
    token = "123456789:" + "THIS_IS_A_SECRET_TELEGRAM_TOKEN"
    log = container.settings.paths.logs / "worker.log"
    log.write_text(
        f"token={token} operator=person@example.com root={container.settings.paths.root}",
        encoding="utf-8",
    )

    bundle = container.diagnostics.create_bundle()

    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        combined = "\n".join(
            archive.read(name).decode("utf-8") for name in names if name.endswith((".json", ".log"))
        )
        manifest = json.loads(archive.read("manifest.json"))
    assert {"health.json", "environment.json", "database.json", "manifest.json"} <= names
    assert token not in combined
    assert "person@example.com" not in combined
    assert str(container.settings.paths.root) not in combined
    assert "<REDACTED>" in combined and "<DATA_ROOT>" in combined
    assert manifest["files"]


def test_diagnostics_rejects_path_traversal(tmp_path: Path) -> None:
    container = _container(tmp_path)
    with pytest.raises(ValueError, match="diagnostics root"):
        container.diagnostics.create_bundle(tmp_path / "escaped.zip")
