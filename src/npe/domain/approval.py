"""Versioned approval and audit domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ApprovalGate(StrEnum):
    MAP = "map"
    REFERENCE = "reference"
    VIEW = "view"


@dataclass(frozen=True)
class Revision:
    id: str
    project_id: str
    building_id: str | None
    gate: ApprovalGate
    version: int
    payload_json: str
    content_hash: str
    created_at: str


@dataclass(frozen=True)
class ApprovalSnapshot:
    id: str
    revision_id: str
    project_id: str
    building_id: str | None
    gate: ApprovalGate
    actor: str
    comment: str
    approved_at: str
    valid: bool


@dataclass(frozen=True)
class AuditEvent:
    id: str
    project_id: str
    building_id: str | None
    event_type: str
    actor: str
    comment: str
    changes_json: str
    created_at: str
