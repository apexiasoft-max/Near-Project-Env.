from __future__ import annotations

from pathlib import Path

from npe.infrastructure.database import Database


def test_database_migration_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    database.migrate()
    database.migrate()
    assert database.is_healthy()
    with database.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"schema_migrations", "projects", "buildings", "jobs"} <= tables

