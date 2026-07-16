"""Index only user-provided project reference images with lineage and deduplication."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from npe.domain.reference import ManualPoolItem
from npe.infrastructure.database import Database
from npe.shared.config import Settings

SUPPORTED = frozenset({".png", ".jpg", ".jpeg", ".webp"})


class ManualPoolService:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def inbox(self, project_id: str) -> Path:
        path = self.settings.paths.projects / project_id / "reference-pool" / "inbox"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def scan(self, project_id: str) -> tuple[list[ManualPoolItem], list[dict[str, str]]]:
        inbox = self.inbox(project_id)
        items: list[ManualPoolItem] = []
        failures: list[dict[str, str]] = []
        seen: set[str] = set()
        with self.database.connect() as connection:
            project = connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if project is None:
                raise KeyError(project_id)
            connection.execute(
                "UPDATE manual_pool_items SET active = 0 WHERE project_id = ?", (project_id,)
            )
            paths = sorted(
                inbox.iterdir(),
                key=lambda item: (not item.with_suffix(".json").is_file(), item.name.lower()),
            )
            for path in paths:
                if not path.is_file() or path.suffix.lower() not in SUPPORTED:
                    continue
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in seen:
                    failures.append({"path": str(path), "reason": "duplicate_in_scan"})
                    continue
                seen.add(digest)
                try:
                    with Image.open(path) as image:
                        width, height = image.size
                        image.verify()
                except (UnidentifiedImageError, OSError) as error:
                    failures.append({"path": str(path), "reason": f"invalid_image: {error}"})
                    continue
                metadata = self._metadata(path)
                pixels = width * height
                quality = round(min(1.0, pixels / (1920 * 1080)), 6)
                row = connection.execute(
                    """SELECT id FROM manual_pool_items
                       WHERE project_id = ? AND sha256 = ?""",
                    (project_id, digest),
                ).fetchone()
                item_id = str(row[0]) if row else f"POOL-{uuid4().hex[:10].upper()}"
                values = (
                    str(path.resolve()), width, height, metadata.get("style"),
                    metadata.get("floors"), self._optional_bool(metadata.get("has_balcony")),
                    quality, json.dumps(metadata, sort_keys=True),
                    datetime.now(UTC).isoformat(), item_id,
                )
                if row:
                    connection.execute(
                        """UPDATE manual_pool_items SET original_path = ?, width_px = ?,
                           height_px = ?, style = ?, floors = ?, has_balcony = ?,
                           quality_score = ?, metadata_json = ?, indexed_at = ?, active = 1
                           WHERE id = ?""",
                        values,
                    )
                else:
                    connection.execute(
                        """INSERT INTO manual_pool_items
                           (original_path, width_px, height_px, style, floors, has_balcony,
                            quality_score, metadata_json, indexed_at, id, project_id,
                            sha256, active)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                        (*values, project_id, digest),
                    )
                items.append(
                    ManualPoolItem(
                        item_id, project_id, path.resolve(), digest, width, height,
                        str(metadata["style"]) if metadata.get("style") else None,
                        self._optional_int(metadata.get("floors")),
                        self._optional_bool(metadata.get("has_balcony")), quality,
                    )
                )
        return items, failures

    @staticmethod
    def _metadata(image_path: Path) -> dict[str, object]:
        sidecar = image_path.with_suffix(".json")
        if not sidecar.is_file():
            return {}
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Metadata sidecar must be an object: {sidecar}")
        return payload

    @staticmethod
    def _optional_bool(value: object) -> bool | None:
        return value if isinstance(value, bool) else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None
