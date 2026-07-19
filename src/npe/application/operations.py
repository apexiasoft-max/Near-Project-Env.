"""Windows release prerequisites, safe upgrades, and sanitized diagnostics."""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import sqlite3
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from npe.application.health import HealthService
from npe.infrastructure.database import Database
from npe.shared.config import Settings

REQUIRED_PACKAGES = {
    "fastapi": "0.139.0",
    "pydantic": "2.13.4",
    "PySide6": "6.11.1",
    "playwright": "1.61.0",
    "Pillow": "11.3.0",
    "uvicorn": "0.51.0",
}
PACKAGE_MODULES = {
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "PySide6": "PySide6",
    "playwright": "playwright",
    "Pillow": "PIL",
    "uvicorn": "uvicorn",
}
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(token|secret|password|api[_-]?key)(\s*[:=]\s*)([^\s,;]+)"
)
TELEGRAM_TOKEN = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


@dataclass(frozen=True)
class PrerequisiteCheck:
    name: str
    passed: bool
    installed: str
    required: str


@dataclass(frozen=True)
class PrerequisiteReport:
    passed: bool
    checks: tuple[PrerequisiteCheck, ...]


@dataclass(frozen=True)
class UpgradeReceipt:
    backup_path: Path
    schema_version_before: int
    schema_version_after: int
    integrity: str


class PrerequisiteService:
    def inspect(self) -> PrerequisiteReport:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        checks = [
            PrerequisiteCheck("python", python_version == "3.12", python_version, "3.12")
        ]
        for package, required in REQUIRED_PACKAGES.items():
            installed = self._version(package, required)
            checks.append(
                PrerequisiteCheck(package, installed == required, installed, required)
            )
        return PrerequisiteReport(all(check.passed for check in checks), tuple(checks))

    @staticmethod
    def _version(package: str, bundled_version: str) -> str:
        if getattr(sys, "frozen", False):
            module = PACKAGE_MODULES[package]
            return bundled_version if importlib.util.find_spec(module) is not None else "missing"
        return _installed_version(package)


class UpgradeService:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def upgrade(self) -> UpgradeReceipt:
        database_path = self.database.path.resolve()
        if not database_path.is_file():
            self.database.migrate()
        before = self._schema_version(database_path)
        backup = self._backup(database_path)
        try:
            self.database.migrate()
            integrity = self._integrity(database_path)
            if integrity != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        except BaseException:
            self._restore_database(backup, database_path)
            raise
        return UpgradeReceipt(backup, before, self._schema_version(database_path), integrity)

    def restore(self, backup: Path) -> None:
        source = backup.resolve(strict=True)
        backup_root = (self.settings.paths.root / "backups").resolve()
        if not source.is_relative_to(backup_root) or source.suffix != ".db":
            raise ValueError("Backup must be a database under the managed backup root")
        if self._integrity(source) != "ok":
            raise ValueError("Backup database failed integrity check")
        self._restore_database(source, self.database.path)

    def _backup(self, source: Path) -> Path:
        backup_root = self.settings.paths.root / "backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        target = backup_root / f"app-before-upgrade-{stamp}.db"
        with sqlite3.connect(source) as origin, sqlite3.connect(target) as destination:
            origin.backup(destination)
        if self._integrity(target) != "ok":
            target.unlink(missing_ok=True)
            raise RuntimeError("Backup integrity check failed")
        return target

    @staticmethod
    def _restore_database(source: Path, destination: Path) -> None:
        with sqlite3.connect(source) as backup, sqlite3.connect(destination) as active:
            backup.backup(active)

    @staticmethod
    def _integrity(path: Path) -> str:
        with sqlite3.connect(path) as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        return "missing" if row is None else str(row[0])

    @staticmethod
    def _schema_version(path: Path) -> int:
        with sqlite3.connect(path) as connection:
            try:
                row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            except sqlite3.OperationalError:
                return 0
        return int(row[0] or 0) if row else 0


class DiagnosticsService:
    def __init__(self, settings: Settings, database: Database, health: HealthService) -> None:
        self.settings = settings
        self.database = database
        self.health = health

    def create_bundle(self, destination: Path | None = None) -> Path:
        diagnostics = self.settings.paths.root / "diagnostics"
        diagnostics.mkdir(parents=True, exist_ok=True)
        target = (destination or diagnostics / self._name()).resolve()
        if not target.is_relative_to(diagnostics.resolve()) or target.suffix != ".zip":
            raise ValueError("Diagnostics bundle must be a ZIP under diagnostics root")
        with tempfile.TemporaryDirectory(dir=diagnostics) as temporary:
            root = Path(temporary)
            self._write_json(root / "health.json", self._safe_health())
            self._write_json(root / "environment.json", self._environment())
            self._write_json(root / "database.json", self._database_summary())
            self._copy_logs(root / "logs")
            manifest = self._manifest(root)
            self._write_json(root / "manifest.json", {"files": manifest})
            partial = target.with_suffix(".partial")
            with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(item for item in root.rglob("*") if item.is_file()):
                    archive.write(path, path.relative_to(root).as_posix())
            partial.replace(target)
        return target

    def _safe_health(self) -> dict[str, object]:
        payload = self.health.inspect().to_dict()
        for component in payload.values():
            if isinstance(component, dict) and "detail" in component:
                component["detail"] = _sanitize(str(component["detail"]), self.settings.paths.root)
        return payload

    def _environment(self) -> dict[str, object]:
        return {
            "application_version": _installed_version("near-project-environment"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "data_root": "<DATA_ROOT>",
            "telegram_configured": bool(
                self.settings.telegram_bot_token and self.settings.telegram_chat_id
            ),
            "packages": {
                name: _installed_version(name) for name in sorted(REQUIRED_PACKAGES)
            },
        }

    def _database_summary(self) -> dict[str, object]:
        with self.database.connect() as connection:
            version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            counts = {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("projects", "buildings", "jobs", "intervention_events")
            }
        return {
            "integrity": self.database.is_healthy(),
            "schema_version": version[0],
            "counts": counts,
        }

    def _copy_logs(self, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        for source in sorted(self.settings.paths.logs.glob("*")):
            if not source.is_file() or source.suffix.lower() not in {".log", ".jsonl", ".txt"}:
                continue
            content = source.read_text(encoding="utf-8", errors="replace")[-200_000:]
            (destination / source.name).write_text(
                _sanitize(content, self.settings.paths.root), encoding="utf-8"
            )

    @staticmethod
    def _manifest(root: Path) -> list[dict[str, object]]:
        return [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(item for item in root.rglob("*") if item.is_file())
        ]

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _name() -> str:
        return f"npe-diagnostics-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.zip"


def _installed_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "missing"


def _sanitize(content: str, data_root: Path) -> str:
    result = content.replace(str(data_root), "<DATA_ROOT>")
    result = TELEGRAM_TOKEN.sub("<REDACTED_TOKEN>", result)
    result = EMAIL.sub("<REDACTED_EMAIL>", result)
    return SECRET_ASSIGNMENT.sub(r"\1\2<REDACTED>", result)
