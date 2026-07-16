"""Immutable five-view attempt history and approval gate."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from npe.domain.five_view import REQUIRED_DIRECTIONS
from npe.domain.five_view_review import ViewAttempt, ViewOutput
from npe.infrastructure.database import Database


class FiveViewReviewService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def register(
        self, project_id: str, building_id: str, run_id: str,
        views: dict[str, Path], lineage_path: Path,
    ) -> ViewAttempt:
        if set(views) != set(REQUIRED_DIRECTIONS):
            raise ValueError("A complete five-direction set is required")
        if not lineage_path.is_file():
            raise FileNotFoundError(lineage_path)
        missing = [str(path) for path in views.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError(", ".join(missing))
        attempt_id = f"VIEW-{uuid4().hex[:10].upper()}"
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM five_view_attempts WHERE building_id = ?",
                (building_id,),
            ).fetchone()
            version = int(row[0]) + 1
            connection.execute(
                """INSERT INTO five_view_attempts
                   (id, project_id, building_id, run_id, version, status, guidance_json,
                    lineage_path, created_at)
                   VALUES (?, ?, ?, ?, ?, 'awaiting_review', '{}', ?, ?)""",
                (attempt_id, project_id, building_id, run_id, version, str(lineage_path), now),
            )
            for direction in REQUIRED_DIRECTIONS:
                path = views[direction]
                connection.execute(
                    """INSERT INTO five_view_outputs
                       (attempt_id, direction, image_path, sha256, status, guidance)
                       VALUES (?, ?, ?, ?, 'pending', '')""",
                    (attempt_id, direction, str(path), _sha256(path)),
                )
        return self.get(attempt_id)

    def get(self, attempt_id: str) -> ViewAttempt:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM five_view_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            if row is None:
                raise KeyError(attempt_id)
            output_rows = connection.execute(
                "SELECT * FROM five_view_outputs WHERE attempt_id = ? ORDER BY direction",
                (attempt_id,),
            ).fetchall()
        outputs = tuple(
            ViewOutput(
                str(item["direction"]), Path(str(item["image_path"])),
                str(item["sha256"]), str(item["status"]), str(item["guidance"]),
            )
            for item in output_rows
        )
        return ViewAttempt(
            str(row["id"]), str(row["project_id"]), str(row["building_id"]),
            str(row["run_id"]), int(row["version"]), str(row["status"]), outputs,
            str(row["parent_attempt_id"]) if row["parent_attempt_id"] else None,
        )

    def latest(self, building_id: str) -> ViewAttempt | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT id FROM five_view_attempts WHERE building_id = ?
                   ORDER BY version DESC LIMIT 1""",
                (building_id,),
            ).fetchone()
        return None if row is None else self.get(str(row["id"]))

    def request_revision(
        self, attempt_id: str, guidance: str, directions: set[str] | None = None,
    ) -> ViewAttempt:
        if not guidance.strip():
            raise ValueError("Revision guidance is required")
        rejected = set(REQUIRED_DIRECTIONS) if directions is None else directions
        if not rejected or not rejected <= set(REQUIRED_DIRECTIONS):
            raise ValueError("Invalid revision directions")
        current = self.get(attempt_id)
        if current.status != "awaiting_review":
            raise ValueError("Only an awaiting-review attempt can be revised")
        next_id = f"VIEW-{uuid4().hex[:10].upper()}"
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE five_view_attempts SET status = 'revision_requested' WHERE id = ?",
                (attempt_id,),
            )
            for direction in rejected:
                connection.execute(
                    """UPDATE five_view_outputs SET status = 'rejected', guidance = ?
                       WHERE attempt_id = ? AND direction = ?""",
                    (guidance.strip(), attempt_id, direction),
                )
            connection.execute(
                """INSERT INTO five_view_attempts
                   (id, project_id, building_id, run_id, version, parent_attempt_id,
                    status, guidance_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending_generation', ?, ?)""",
                (
                    next_id, current.project_id, current.building_id,
                    f"{current.run_id}-R{current.version + 1}", current.version + 1,
                    attempt_id,
                    json.dumps({"directions": sorted(rejected), "guidance": guidance.strip()}),
                    now,
                ),
            )
        return self.get(next_id)

    def approve(self, attempt_id: str) -> ViewAttempt:
        attempt = self.get(attempt_id)
        if attempt.status != "awaiting_review":
            raise ValueError("Attempt is not ready for approval")
        if {output.direction for output in attempt.outputs} != set(REQUIRED_DIRECTIONS):
            raise ValueError("Complete five-direction set is required")
        if any(not output.image_path.is_file() for output in attempt.outputs):
            raise ValueError("All five view files must exist")
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE five_view_outputs SET status = 'approved' WHERE attempt_id = ?",
                (attempt_id,),
            )
            connection.execute(
                "UPDATE five_view_attempts SET status = 'approved' WHERE id = ?", (attempt_id,)
            )
            connection.execute(
                "UPDATE buildings SET status = 'views_approved', updated_at = ? WHERE id = ?",
                (now, attempt.building_id),
            )
            connection.execute(
                """UPDATE jobs SET stage = 'ready_for_hunyuan', status = 'ready', updated_at = ?
                   WHERE building_id = ? AND stage = 'awaiting_views'""",
                (now, attempt.building_id),
            )
        return self.get(attempt_id)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
