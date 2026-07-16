"""Small SQLite boundary with explicit migrations and health probes."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        radius_m INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS buildings (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        code TEXT NOT NULL,
        target_height_m REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(project_id, code)
    );
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        building_id TEXT NOT NULL REFERENCES buildings(id),
        run_id TEXT NOT NULL UNIQUE,
        stage TEXT NOT NULL,
        status TEXT NOT NULL,
        input_manifest TEXT,
        downloaded_model_path TEXT,
        final_fbx_path TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    ALTER TABLE projects ADD COLUMN output_path TEXT;
    UPDATE projects SET output_path = '' WHERE output_path IS NULL;
    UPDATE projects SET status = 'draft' WHERE status = 'active';
    """,
    """
    CREATE TABLE revisions (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        building_id TEXT REFERENCES buildings(id),
        gate TEXT NOT NULL,
        version INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(project_id, building_id, gate, version)
    );
    CREATE TABLE approval_snapshots (
        id TEXT PRIMARY KEY,
        revision_id TEXT NOT NULL REFERENCES revisions(id),
        project_id TEXT NOT NULL REFERENCES projects(id),
        building_id TEXT REFERENCES buildings(id),
        gate TEXT NOT NULL,
        actor TEXT NOT NULL,
        comment TEXT NOT NULL,
        approved_at TEXT NOT NULL
    );
    CREATE TABLE approval_invalidations (
        approval_id TEXT PRIMARY KEY REFERENCES approval_snapshots(id),
        caused_by_revision_id TEXT NOT NULL REFERENCES revisions(id),
        invalidated_at TEXT NOT NULL
    );
    CREATE TABLE audit_events (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        building_id TEXT REFERENCES buildings(id),
        event_type TEXT NOT NULL,
        actor TEXT NOT NULL,
        comment TEXT NOT NULL,
        changes_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    ALTER TABLE buildings ADD COLUMN footprint_json TEXT;
    ALTER TABLE buildings ADD COLUMN floors INTEGER;
    ALTER TABLE buildings ADD COLUMN front_bearing_deg REAL;
    ALTER TABLE buildings ADD COLUMN boundary_intersection INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE buildings ADD COLUMN inventory_source TEXT;
    ALTER TABLE buildings ADD COLUMN deleted_at TEXT;
    """,
    """
    ALTER TABLE buildings ADD COLUMN height_min_m REAL;
    ALTER TABLE buildings ADD COLUMN height_max_m REAL;
    ALTER TABLE buildings ADD COLUMN height_method TEXT;
    ALTER TABLE buildings ADD COLUMN height_confidence REAL;
    ALTER TABLE buildings ADD COLUMN height_evidence_json TEXT;
    """,
    """
    CREATE TABLE reference_candidates (
        id TEXT PRIMARY KEY,
        building_id TEXT NOT NULL REFERENCES buildings(id),
        provider TEXT NOT NULL,
        source_id TEXT NOT NULL,
        image_path TEXT NOT NULL,
        captured_at TEXT,
        camera_lon REAL,
        camera_lat REAL,
        heading_deg REAL,
        fov_deg REAL,
        width_px INTEGER NOT NULL,
        height_px INTEGER NOT NULL,
        visibility REAL NOT NULL,
        occlusion REAL NOT NULL,
        attribution_score REAL NOT NULL,
        quality_score REAL NOT NULL,
        total_score REAL NOT NULL,
        rank INTEGER NOT NULL,
        evidence_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );
    CREATE INDEX idx_reference_candidates_building
        ON reference_candidates(building_id, active, rank);
    """,
    """
    CREATE TABLE manual_pool_items (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        original_path TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        width_px INTEGER NOT NULL,
        height_px INTEGER NOT NULL,
        style TEXT,
        floors INTEGER,
        has_balcony INTEGER,
        quality_score REAL NOT NULL,
        metadata_json TEXT NOT NULL,
        indexed_at TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(project_id, sha256)
    );
    """,
    """
    ALTER TABLE reference_candidates ADD COLUMN selected INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE reference_candidates ADD COLUMN rejected INTEGER NOT NULL DEFAULT 0;
    CREATE TABLE intervention_events (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        building_id TEXT NOT NULL REFERENCES buildings(id),
        kind TEXT NOT NULL,
        channel TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        resolved_at TEXT
    );
    """,
    """
    ALTER TABLE intervention_events ADD COLUMN notified_at TEXT;
    """,
    """
    CREATE TABLE five_view_attempts (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        building_id TEXT NOT NULL REFERENCES buildings(id),
        run_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        parent_attempt_id TEXT REFERENCES five_view_attempts(id),
        status TEXT NOT NULL,
        guidance_json TEXT NOT NULL,
        lineage_path TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(building_id, version)
    );
    CREATE TABLE five_view_outputs (
        attempt_id TEXT NOT NULL REFERENCES five_view_attempts(id),
        direction TEXT NOT NULL,
        image_path TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        status TEXT NOT NULL,
        guidance TEXT NOT NULL,
        PRIMARY KEY(attempt_id, direction)
    );
    """,
    """
    ALTER TABLE jobs ADD COLUMN correlation_id TEXT;
    ALTER TABLE jobs ADD COLUMN last_error TEXT;
    CREATE TABLE stage_attempts (
        id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL REFERENCES jobs(id),
        run_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        attempt INTEGER NOT NULL,
        status TEXT NOT NULL,
        correlation_id TEXT NOT NULL,
        detail_json TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        UNIQUE(job_id, stage, attempt)
    );
    CREATE INDEX idx_stage_attempts_running ON stage_attempts(status, started_at);
    """,
    """
    CREATE TABLE provider_locks (
        provider TEXT PRIMARY KEY,
        owner_id TEXT NOT NULL,
        acquired_at REAL NOT NULL,
        expires_at REAL NOT NULL
    );
    """,
    """
    ALTER TABLE intervention_events ADD COLUMN notify_attempts INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE intervention_events ADD COLUMN last_notify_error TEXT;
    """,
)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.executescript(MIGRATIONS[0])
            for version, sql in enumerate(MIGRATIONS[1:], start=1):
                row = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
                ).fetchone()
                if row is None:
                    connection.executescript(sql)
                    connection.execute(
                        "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
                    )

    def is_healthy(self) -> bool:
        try:
            with self.connect() as connection:
                row = connection.execute("SELECT 1").fetchone()
                return bool(row is not None and row[0] == 1)
        except sqlite3.Error:
            return False
