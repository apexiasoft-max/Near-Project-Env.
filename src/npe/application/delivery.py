"""Deterministic, traceable project delivery package assembly."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from npe.domain.five_view import REQUIRED_DIRECTIONS
from npe.infrastructure.database import Database
from npe.shared.config import Settings

BUILDING_CODE = re.compile(r"B\d{3,}")


@dataclass(frozen=True)
class DeliveryMetrics:
    runtime_seconds: float = 0
    active_human_minutes: float = 0
    error_count: int = 0


@dataclass(frozen=True)
class DeliverySummary:
    package_path: Path
    building_count: int
    completed: int
    missing: int
    needs_review: int
    completion_rate: float
    size_bytes: int


@dataclass(frozen=True)
class _Artifact:
    artifact_type: str
    source: Path
    destination: Path
    producer_stage: str
    parent_artifact_ids: tuple[str, ...] = ()


class DeliveryPackageService:
    """Build a replaceable delivery snapshot without mutating source artifacts."""

    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def assemble(
        self,
        project_id: str,
        *,
        destination: Path | None = None,
        metrics: DeliveryMetrics | None = None,
    ) -> DeliverySummary:
        metrics = metrics or DeliveryMetrics()
        project = self._project(project_id)
        root = self._safe_destination(
            destination or self.settings.paths.projects / project_id / "delivery"
        )
        staging = root.with_name(f".{root.name}.partial-{uuid4().hex}")
        staging.mkdir(parents=True)
        try:
            rows = self._buildings(project_id)
            results: list[dict[str, object]] = []
            self._copy_overview(project_id, staging)
            for row in rows:
                results.append(self._assemble_building(project_id, row, staging))
            self._write_buildings_csv(staging, results)
            summary = self._summary(staging, results, metrics)
            self._write_project_metadata(staging, project, summary, metrics)
            self._write_report(staging, project, results, summary, metrics)
            self._write_package_manifest(staging)
            summary = self._summary(staging, results, metrics)
            self._replace(root, staging)
            return DeliverySummary(root, *summary)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def _assemble_building(
        self, project_id: str, row: dict[str, object], package: Path
    ) -> dict[str, object]:
        code = str(row["code"])
        if BUILDING_CODE.fullmatch(code) is None:
            raise ValueError(f"Unsafe building code: {code}")
        building_root = package / "buildings" / code
        references = self._references(str(row["id"]))
        views = self._views(str(row["id"]))
        raw_model = self._optional_file(row.get("downloaded_model_path"))
        final_model = self._optional_file(row.get("final_fbx_path"))
        artifacts: list[_Artifact] = []
        for index, reference in enumerate(references, start=1):
            artifacts.append(
                _Artifact(
                    "reference",
                    reference,
                    Path("references") / "selected" / f"{index:02d}{reference.suffix.lower()}",
                    "reference_review",
                )
            )
        for direction, source in views.items():
            artifacts.append(
                _Artifact(
                    f"approved_view_{direction}", source,
                    Path("generated") / "approved" / f"{direction}{source.suffix.lower()}",
                    "five_view_review",
                )
            )
        if raw_model is not None:
            artifacts.append(
                _Artifact(
                    "raw_model", raw_model,
                    Path("model") / "raw" / f"{code}{raw_model.suffix.lower()}",
                    "hunyuan_download",
                )
            )
        if final_model is not None:
            artifacts.append(
                _Artifact(
                    "final_fbx", final_model, Path("model") / "final" / f"{code}.fbx",
                    "fbx_normalization",
                )
            )
        manifest = self._copy_artifacts(project_id, str(row["id"]), building_root, artifacts)
        complete = (
            bool(references)
            and set(views) == set(REQUIRED_DIRECTIONS)
            and raw_model is not None
            and final_model is not None
        )
        source_status = str(row["status"])
        job_status = str(row.get("job_status") or "")
        status = (
            "Completed"
            if complete
            else "NeedsReview"
            if "needs_review" in {source_status, job_status}
            else "MissingReference"
        )
        metadata: dict[str, object] = {
            "building_id": row["id"],
            "project_id": project_id,
            "code": code,
            "status": status,
            "source_status": source_status,
            "target_height_m": row["target_height_m"],
            "floors": row["floors"],
            "front_bearing_deg": row["front_bearing_deg"],
            "artifact_count": len(manifest),
        }
        self._write_json(building_root / "metadata.json", metadata)
        self._write_json(building_root / "manifest.json", {"artifacts": manifest})
        return metadata

    def _copy_artifacts(
        self,
        project_id: str,
        building_id: str,
        root: Path,
        artifacts: list[_Artifact],
    ) -> list[dict[str, object]]:
        manifest: list[dict[str, object]] = []
        for artifact in artifacts:
            source = artifact.source.resolve(strict=True)
            target = (root / artifact.destination).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError("Artifact destination escaped building root")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            relative = target.relative_to(root.parent.parent).as_posix()
            digest = _sha256(target)
            artifact_id = f"ART-{digest[:16].upper()}"
            manifest.append(
                {
                    "artifact_id": artifact_id,
                    "project_id": project_id,
                    "building_id": building_id,
                    "artifact_type": artifact.artifact_type,
                    "relative_path": relative,
                    "sha256": digest,
                    "size_bytes": target.stat().st_size,
                    "producer_stage": artifact.producer_stage,
                    "parent_artifact_ids": list(artifact.parent_artifact_ids),
                }
            )
        return sorted(manifest, key=lambda item: str(item["relative_path"]))

    def _copy_overview(self, project_id: str, package: Path) -> None:
        source = self.settings.paths.projects / project_id / "inventory"
        overview = package / "overview"
        overview.mkdir(parents=True)
        originals = sorted(source.glob("aerial_original.*"))
        if originals:
            shutil.copy2(originals[0], overview / f"aerial_original{originals[0].suffix.lower()}")
        coded = source / "aerial_coded.png"
        if coded.is_file():
            shutil.copy2(coded, overview / "aerial_coded.png")

    def _project(self, project_id: str) -> dict[str, object]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise KeyError(project_id)
        return dict(row)

    def _buildings(self, project_id: str) -> list[dict[str, object]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT b.*, j.status AS job_status, j.downloaded_model_path,
                          j.final_fbx_path
                   FROM buildings b
                   LEFT JOIN jobs j ON j.id = (
                     SELECT j2.id FROM jobs j2 WHERE j2.building_id = b.id
                     ORDER BY j2.updated_at DESC LIMIT 1
                   )
                   WHERE b.project_id = ? AND b.deleted_at IS NULL ORDER BY b.code""",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _references(self, building_id: str) -> list[Path]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT image_path FROM reference_candidates
                   WHERE building_id = ? AND selected = 1 AND rejected = 0 AND active = 1
                   ORDER BY rank, id""",
                (building_id,),
            ).fetchall()
        return [path for row in rows if (path := Path(str(row[0]))).is_file()]

    def _views(self, building_id: str) -> dict[str, Path]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT o.direction, o.image_path FROM five_view_outputs o
                   JOIN five_view_attempts a ON a.id = o.attempt_id
                   WHERE a.building_id = ? AND a.status = 'approved' AND o.status = 'approved'
                   AND a.version = (SELECT MAX(version) FROM five_view_attempts
                                    WHERE building_id = ? AND status = 'approved')""",
                (building_id, building_id),
            ).fetchall()
        return {
            str(row[0]): path for row in rows if (path := Path(str(row[1]))).is_file()
        }

    def _safe_destination(self, destination: Path) -> Path:
        result = destination.expanduser().resolve()
        projects_root = self.settings.paths.projects.resolve()
        if not result.is_relative_to(projects_root):
            raise ValueError("Delivery destination must be under the projects root")
        return result

    @staticmethod
    def _optional_file(value: object) -> Path | None:
        if value is None or not str(value):
            return None
        path = Path(str(value))
        return path if path.is_file() else None

    @staticmethod
    def _replace(root: Path, staging: Path) -> None:
        backup = root.with_name(f".{root.name}.previous")
        if backup.exists():
            shutil.rmtree(backup)
        if root.exists():
            os.replace(root, backup)
        try:
            os.replace(staging, root)
        except BaseException:
            if backup.exists():
                os.replace(backup, root)
            raise
        shutil.rmtree(backup, ignore_errors=True)

    @staticmethod
    def _summary(
        staging: Path, results: list[dict[str, object]], metrics: DeliveryMetrics
    ) -> tuple[int, int, int, int, float, int]:
        del metrics
        count = len(results)
        completed = sum(item["status"] == "Completed" for item in results)
        missing = sum(item["status"] == "MissingReference" for item in results)
        review = sum(item["status"] == "NeedsReview" for item in results)
        rate = completed / count if count else 0.0
        size = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        return count, completed, missing, review, rate, size

    @staticmethod
    def _write_buildings_csv(package: Path, results: list[dict[str, object]]) -> None:
        target = package / "overview" / "buildings.csv"
        with target.open("w", newline="", encoding="utf-8") as handle:
            fields = (
                "building_id", "code", "status", "target_height_m", "floors",
                "front_bearing_deg", "artifact_count",
            )
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows({field: item.get(field) for field in fields} for item in results)

    @staticmethod
    def _write_project_metadata(
        package: Path,
        project: dict[str, object],
        summary: tuple[int, int, int, int, float, int],
        metrics: DeliveryMetrics,
    ) -> None:
        DeliveryPackageService._write_json(
            package / "project.json",
            {
                "id": project["id"], "name": project["name"],
                "latitude": project["latitude"], "longitude": project["longitude"],
                "radius_m": project["radius_m"],
                "generated_at": datetime.now(UTC).isoformat(),
                "summary": {
                    "building_count": summary[0], "completed": summary[1],
                    "missing": summary[2], "needs_review": summary[3],
                    "completion_rate": summary[4], "size_bytes": summary[5],
                },
                "metrics": asdict(metrics),
            },
        )

    @staticmethod
    def _write_report(
        package: Path,
        project: dict[str, object],
        results: list[dict[str, object]],
        summary: tuple[int, int, int, int, float, int],
        metrics: DeliveryMetrics,
    ) -> None:
        rows = "".join(
            "<tr>" + "".join(
                f"<td>{html.escape(str(item.get(key) or ''))}</td>"
                for key in ("code", "status", "target_height_m", "floors", "artifact_count")
            ) + "</tr>"
            for item in results
        )
        content = f"""<!doctype html><html><head><meta charset=\"utf-8\">
<title>Delivery report</title><style>body{{font:14px Arial;margin:32px;color:#20242a}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:8px;border:1px solid #ccd2d8}}
.metric{{display:inline-block;margin:0 20px 20px 0}}</style></head><body>
<h1>{html.escape(str(project['name']))}</h1>
<div class=\"metric\">Completed: {summary[1]}/{summary[0]}</div>
<div class=\"metric\">Missing: {summary[2]}</div>
<div class=\"metric\">Needs review: {summary[3]}</div>
<div class=\"metric\">Completion: {summary[4]:.1%}</div>
<div class=\"metric\">Runtime: {metrics.runtime_seconds:.1f}s</div>
<div class=\"metric\">Active human: {metrics.active_human_minutes:.1f}m</div>
<div class=\"metric\">Errors: {metrics.error_count}</div>
<table><thead><tr><th>Code</th><th>Status</th><th>Height (m)</th><th>Floors</th>
<th>Artifacts</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""
        target = package / "reports" / "process_report.html"
        target.parent.mkdir(parents=True)
        target.write_text(content, encoding="utf-8")

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _write_package_manifest(package: Path) -> None:
        entries = []
        for path in sorted(item for item in package.rglob("*") if item.is_file()):
            relative = path.relative_to(package).as_posix()
            entries.append(
                {
                    "relative_path": relative,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        DeliveryPackageService._write_json(
            package / "package_manifest.json", {"files": entries}
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
