"""Immutable revision snapshots, approval commands and targeted invalidation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from uuid import uuid4

from npe.domain.approval import ApprovalGate, ApprovalSnapshot, AuditEvent, Revision
from npe.infrastructure.database import Database


class ApprovalService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_revision(
        self,
        project_id: str,
        gate: ApprovalGate,
        payload: Mapping[str, object],
        actor: str,
        comment: str = "",
        building_id: str | None = None,
    ) -> Revision:
        self._validate_scope(project_id, gate, building_id)
        payload_json = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        content_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        now = datetime.now(UTC).isoformat()
        revision_id = f"REV-{uuid4().hex[:10].upper()}"
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT COALESCE(MAX(version), 0) + 1 FROM revisions
                   WHERE project_id = ? AND gate = ? AND building_id IS ?""",
                (project_id, gate, building_id),
            ).fetchone()
            assert row is not None
            version = int(row[0])
            connection.execute(
                """INSERT INTO revisions
                   (id, project_id, building_id, gate, version, payload_json,
                    content_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    revision_id, project_id, building_id, gate, version, payload_json,
                    content_hash, now,
                ),
            )
            invalidated = self._invalidate_downstream(
                connection, project_id, gate, building_id, now, revision_id
            )
            self._audit(
                connection, project_id, building_id, "revision_created", actor, comment,
                {"revision_id": revision_id, "gate": gate, "version": version,
                 "content_hash": content_hash, "invalidated_approval_ids": invalidated},
                now,
            )
        return self.get_revision(revision_id)

    def approve(
        self,
        revision_id: str,
        actor: str,
        comment: str = "",
    ) -> ApprovalSnapshot:
        revision = self.get_revision(revision_id)
        latest = self.latest_revision(
            revision.project_id, revision.gate, revision.building_id
        )
        if latest.id != revision.id:
            raise ValueError("Only the latest revision can be approved")
        now = datetime.now(UTC).isoformat()
        approval_id = f"APR-{uuid4().hex[:10].upper()}"
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO approval_snapshots
                   (id, revision_id, project_id, building_id, gate, actor, comment, approved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    approval_id, revision.id, revision.project_id, revision.building_id,
                    revision.gate, actor, comment, now,
                ),
            )
            self._audit(
                connection, revision.project_id, revision.building_id, "approved", actor,
                comment, {"approval_id": approval_id, "revision_id": revision.id,
                          "gate": revision.gate, "version": revision.version}, now,
            )
        return self.get_approval(approval_id)

    def batch_approve(
        self,
        project_id: str,
        gate: ApprovalGate,
        building_ids: Iterable[str],
        excluded_building_ids: Iterable[str],
        actor: str,
        comment: str = "",
    ) -> list[ApprovalSnapshot]:
        if gate == ApprovalGate.MAP:
            raise ValueError("Map approval is project-scoped and cannot be batched")
        excluded = set(excluded_building_ids)
        approvals = []
        for building_id in building_ids:
            if building_id in excluded:
                continue
            revision = self.latest_revision(project_id, gate, building_id)
            approvals.append(self.approve(revision.id, actor, comment))
        return approvals

    def latest_revision(
        self, project_id: str, gate: ApprovalGate, building_id: str | None = None
    ) -> Revision:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT * FROM revisions WHERE project_id = ? AND gate = ?
                   AND building_id IS ? ORDER BY version DESC LIMIT 1""",
                (project_id, gate, building_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"No {gate} revision for target")
        return self._revision(row)

    def list_approvals(self, project_id: str) -> list[ApprovalSnapshot]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT a.*, CASE WHEN i.approval_id IS NULL THEN 1 ELSE 0 END AS valid
                   FROM approval_snapshots a
                   LEFT JOIN approval_invalidations i ON i.approval_id = a.id
                   WHERE a.project_id = ? ORDER BY a.approved_at""",
                (project_id,),
            ).fetchall()
        return [self._approval(row) for row in rows]

    def audit_timeline(self, project_id: str) -> list[AuditEvent]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events WHERE project_id = ? ORDER BY created_at, id",
                (project_id,),
            ).fetchall()
        return [self._event(row) for row in rows]

    def get_revision(self, revision_id: str) -> Revision:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM revisions WHERE id = ?", (revision_id,)
            ).fetchone()
        if row is None:
            raise KeyError(revision_id)
        return self._revision(row)

    def get_approval(self, approval_id: str) -> ApprovalSnapshot:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT a.*, CASE WHEN i.approval_id IS NULL THEN 1 ELSE 0 END AS valid
                   FROM approval_snapshots a
                   LEFT JOIN approval_invalidations i ON i.approval_id = a.id
                   WHERE a.id = ?""",
                (approval_id,),
            ).fetchone()
        if row is None:
            raise KeyError(approval_id)
        return self._approval(row)

    def _validate_scope(
        self, project_id: str, gate: ApprovalGate, building_id: str | None
    ) -> None:
        with self.database.connect() as connection:
            project = connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if project is None:
                raise KeyError(project_id)
            if gate == ApprovalGate.MAP and building_id is not None:
                raise ValueError("Map revisions must be project-scoped")
            if gate != ApprovalGate.MAP:
                if building_id is None:
                    raise ValueError(f"{gate} revisions require a building")
                building = connection.execute(
                    "SELECT 1 FROM buildings WHERE id = ? AND project_id = ?",
                    (building_id, project_id),
                ).fetchone()
                if building is None:
                    raise KeyError(building_id)

    @staticmethod
    def _invalidate_downstream(
        connection: sqlite3.Connection,
        project_id: str,
        gate: ApprovalGate,
        building_id: str | None,
        now: str,
        revision_id: str,
    ) -> list[str]:
        if gate == ApprovalGate.MAP:
            rows = connection.execute(
                """SELECT a.id FROM approval_snapshots a
                   LEFT JOIN approval_invalidations i ON i.approval_id = a.id
                   WHERE a.project_id = ? AND i.approval_id IS NULL""",
                (project_id,),
            ).fetchall()
        else:
            downstream = (
                (ApprovalGate.REFERENCE, ApprovalGate.VIEW)
                if gate == ApprovalGate.REFERENCE
                else (ApprovalGate.VIEW,)
            )
            placeholders = ",".join("?" for _ in downstream)
            rows = connection.execute(
                f"""SELECT a.id FROM approval_snapshots a
                    LEFT JOIN approval_invalidations i ON i.approval_id = a.id
                    WHERE a.project_id = ? AND a.building_id = ?
                    AND a.gate IN ({placeholders}) AND i.approval_id IS NULL""",
                (project_id, building_id, *downstream),
            ).fetchall()
        ids = [str(row[0]) for row in rows]
        connection.executemany(
            """INSERT INTO approval_invalidations
               (approval_id, caused_by_revision_id, invalidated_at) VALUES (?, ?, ?)""",
            [(approval_id, revision_id, now) for approval_id in ids],
        )
        return ids

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        project_id: str,
        building_id: str | None,
        event_type: str,
        actor: str,
        comment: str,
        changes: Mapping[str, object],
        now: str,
    ) -> None:
        connection.execute(
            """INSERT INTO audit_events
               (id, project_id, building_id, event_type, actor, comment, changes_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"AUD-{uuid4().hex[:10].upper()}", project_id, building_id, event_type,
                actor, comment, json.dumps(changes, ensure_ascii=False, sort_keys=True), now,
            ),
        )

    @staticmethod
    def _revision(row: sqlite3.Row) -> Revision:
        return Revision(
            str(row["id"]), str(row["project_id"]),
            str(row["building_id"]) if row["building_id"] else None,
            ApprovalGate(str(row["gate"])), int(row["version"]),
            str(row["payload_json"]), str(row["content_hash"]), str(row["created_at"]),
        )

    @staticmethod
    def _approval(row: sqlite3.Row) -> ApprovalSnapshot:
        return ApprovalSnapshot(
            str(row["id"]), str(row["revision_id"]), str(row["project_id"]),
            str(row["building_id"]) if row["building_id"] else None,
            ApprovalGate(str(row["gate"])), str(row["actor"]), str(row["comment"]),
            str(row["approved_at"]), bool(row["valid"]),
        )

    @staticmethod
    def _event(row: sqlite3.Row) -> AuditEvent:
        return AuditEvent(
            str(row["id"]), str(row["project_id"]),
            str(row["building_id"]) if row["building_id"] else None,
            str(row["event_type"]), str(row["actor"]), str(row["comment"]),
            str(row["changes_json"]), str(row["created_at"]),
        )
