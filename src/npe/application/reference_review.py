"""Reference selection, missing-reference intervention, resume and approval."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from npe.application.approvals import ApprovalService
from npe.domain.approval import ApprovalGate, ApprovalSnapshot
from npe.domain.reference import ReferenceCandidate, ReferenceProvider
from npe.infrastructure.database import Database


class ReferenceReviewService:
    def __init__(self, database: Database, approvals: ApprovalService) -> None:
        self.database = database
        self.approvals = approvals

    def list_candidates(self, project_id: str, building_id: str) -> list[ReferenceCandidate]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT r.* FROM reference_candidates r
                   JOIN buildings b ON b.id = r.building_id
                   WHERE r.building_id = ? AND b.project_id = ? AND r.active = 1
                   ORDER BY r.rank, r.created_at""",
                (building_id, project_id),
            ).fetchall()
        return [
            ReferenceCandidate(
                str(row["id"]), str(row["building_id"]),
                ReferenceProvider(str(row["provider"])), str(row["source_id"]),
                Path(str(row["image_path"])), float(row["attribution_score"]),
                float(row["quality_score"]), float(row["total_score"]),
                int(row["rank"]), bool(row["selected"]), bool(row["rejected"]),
            )
            for row in rows
        ]

    def select(
        self, project_id: str, building_id: str, candidate_id: str,
        actor: str, front_bearing_deg: float | None = None,
    ) -> None:
        if front_bearing_deg is not None and not 0 <= front_bearing_deg < 360:
            raise ValueError("Front bearing must be in [0, 360)")
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            candidate = connection.execute(
                """SELECT 1 FROM reference_candidates r JOIN buildings b ON b.id = r.building_id
                   WHERE r.id = ? AND r.building_id = ? AND b.project_id = ? AND r.active = 1""",
                (candidate_id, building_id, project_id),
            ).fetchone()
            if candidate is None:
                raise KeyError(candidate_id)
            connection.execute(
                "UPDATE reference_candidates SET selected = 0 WHERE building_id = ?",
                (building_id,),
            )
            connection.execute(
                "UPDATE reference_candidates SET selected = 1, rejected = 0 WHERE id = ?",
                (candidate_id,),
            )
            connection.execute(
                """UPDATE buildings SET status = 'reference_selected', front_bearing_deg =
                   COALESCE(?, front_bearing_deg), updated_at = ? WHERE id = ?""",
                (front_bearing_deg, now, building_id),
            )
            self._event(
                connection, project_id, building_id, "reference_selected", actor,
                {"candidate_id": candidate_id, "front_bearing_deg": front_bearing_deg}, now,
            )

    def reject(self, project_id: str, building_id: str, candidate_id: str, actor: str) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE reference_candidates SET rejected = 1, selected = 0
                   WHERE id = ? AND building_id = ?""",
                (candidate_id, building_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(candidate_id)
            self._event(
                connection, project_id, building_id, "reference_rejected", actor,
                {"candidate_id": candidate_id}, datetime.now(UTC).isoformat(),
            )

    def upload_replacement(
        self, project_id: str, building_id: str, path: Path, actor: str,
    ) -> str:
        try:
            with Image.open(path) as image:
                width, height = image.size
                image.verify()
        except (UnidentifiedImageError, OSError) as error:
            raise ValueError(f"Invalid replacement image: {error}") from error
        candidate_id = f"REF-{uuid4().hex[:10].upper()}"
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            building = connection.execute(
                "SELECT 1 FROM buildings WHERE id = ? AND project_id = ?",
                (building_id, project_id),
            ).fetchone()
            if building is None:
                raise KeyError(building_id)
            connection.execute(
                """INSERT INTO reference_candidates
                   (id, building_id, provider, source_id, image_path, width_px, height_px,
                    visibility, occlusion, attribution_score, quality_score, total_score,
                    rank, evidence_json, metadata_json, active, selected, rejected, created_at)
                   VALUES (?, ?, 'manual_pool', ?, ?, ?, ?, 1, 0, 1, 1, 1, 0,
                           '{}', '{}', 1, 0, 0, ?)""",
                (candidate_id, building_id, path.name, str(path.resolve()), width, height, now),
            )
        self.select(project_id, building_id, candidate_id, actor)
        return candidate_id

    def mark_missing(self, project_id: str, building_id: str, actor: str) -> str:
        event_id = f"INT-{uuid4().hex[:10].upper()}"
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE buildings SET status = 'missing_reference', updated_at = ?
                   WHERE id = ? AND project_id = ? AND deleted_at IS NULL""",
                (now, building_id, project_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(building_id)
            connection.execute(
                """INSERT INTO intervention_events
                   (id, project_id, building_id, kind, channel, payload_json, status, created_at)
                   VALUES (?, ?, ?, 'missing_reference', 'telegram', ?, 'pending', ?)""",
                (
                    event_id, project_id, building_id,
                    json.dumps({"project_id": project_id, "building_id": building_id}), now,
                ),
            )
            self._event(
                connection, project_id, building_id, "missing_reference", actor,
                {"intervention_event_id": event_id}, now,
            )
        return event_id

    def approve(self, project_id: str, building_id: str, actor: str) -> ApprovalSnapshot:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT id, provider, source_id, image_path FROM reference_candidates
                   WHERE building_id = ? AND selected = 1 AND active = 1""",
                (building_id,),
            ).fetchone()
        if row is None:
            raise ValueError("A reference must be selected before approval")
        payload = {"candidate": dict(row)}
        revision = self.approvals.create_revision(
            project_id, ApprovalGate.REFERENCE, payload, actor, building_id=building_id
        )
        approval = self.approvals.approve(revision.id, actor)
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE buildings SET status = 'reference_approved', updated_at = ? WHERE id = ?",
                (now, building_id),
            )
            connection.execute(
                """UPDATE intervention_events SET status = 'resolved', resolved_at = ?
                   WHERE building_id = ? AND status IN ('pending', 'notified')""",
                (now, building_id),
            )
        return approval

    @staticmethod
    def _event(
        connection: sqlite3.Connection, project_id: str, building_id: str,
        event_type: str, actor: str, changes: dict[str, object], now: str,
    ) -> None:
        connection.execute(
            """INSERT INTO audit_events
               (id, project_id, building_id, event_type, actor, comment, changes_json, created_at)
               VALUES (?, ?, ?, ?, ?, '', ?, ?)""",
            (
                f"AUD-{uuid4().hex[:10].upper()}", project_id, building_id,
                event_type, actor, json.dumps(changes, sort_keys=True), now,
            ),
        )
