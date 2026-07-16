"""Persistent walking-skeleton use cases."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from npe.domain.project import ProjectStatus, validate_project_input
from npe.domain.workflow import Job, JobStage, ensure_transition
from npe.infrastructure.database import Database
from npe.shared.config import Settings

VIEW_NAMES = ("front", "back", "left", "right", "top")


class ModelNormalizer(Protocol):
    def normalize(self, source: Path, target: Path, height_m: float) -> None: ...


class BlenderNormalizer:
    def __init__(self, blender_path: Path, script_path: Path) -> None:
        self.blender_path = blender_path
        self.script_path = script_path

    def normalize(self, source: Path, target: Path, height_m: float) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [
            str(self.blender_path), "--background", "--python", str(self.script_path),
            "--", "--input", str(source), "--output", str(target),
            "--report", str(target.with_suffix(".verification.json")),
            "--target-height-m", str(height_m),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)


class WalkingSkeletonService:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def create_job(
        self, name: str, latitude: float, longitude: float, radius_m: int,
        building_code: str, target_height_m: float,
        output_path: Path | None = None,
    ) -> Job:
        now = datetime.now(UTC).isoformat()
        project_id = f"PRJ-{uuid4().hex[:8].upper()}"
        building_id = f"BLD-{uuid4().hex[:8].upper()}"
        job_id = f"JOB-{uuid4().hex[:8].upper()}"
        run_id = f"RUN-{uuid4().hex[:10].upper()}"
        resolved_output = (
            output_path.expanduser().resolve()
            if output_path is not None
            else (self.settings.paths.projects / project_id).resolve()
        )
        validate_project_input(name, latitude, longitude, radius_m, resolved_output)
        if not building_code.strip():
            raise ValueError("Building code is required")
        if target_height_m <= 0:
            raise ValueError("Target height must be positive")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO projects
                   (id, name, latitude, longitude, radius_m, status, created_at, updated_at,
                    output_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, name.strip(), latitude, longitude, radius_m,
                    ProjectStatus.DRAFT, now, now, str(resolved_output),
                ),
            )
            connection.execute(
                """INSERT INTO buildings
                   (id, project_id, code, target_height_m, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (building_id, project_id, building_code, target_height_m, "active", now, now),
            )
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, project_id, building_id, run_id, JobStage.AWAITING_VIEWS,
                 "active", None, None, None, now, now),
            )
        return self.get_job(run_id)

    def attach_views(self, run_id: str, views: Mapping[str, Path]) -> Job:
        if set(views) != set(VIEW_NAMES):
            raise ValueError(f"Exactly these views are required: {', '.join(VIEW_NAMES)}")
        job = self.get_job(run_id)
        ensure_transition(job.stage, JobStage.READY_FOR_HUNYUAN)
        approved = self._building_root(job) / "generated" / "approved"
        approved.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, object] = {"run_id": run_id, "views": {}}
        output_views = manifest["views"]
        assert isinstance(output_views, dict)
        for name in VIEW_NAMES:
            source = views[name]
            if not source.is_file():
                raise FileNotFoundError(source)
            target = approved / f"{name}{source.suffix.lower()}"
            shutil.copy2(source, target)
            output_views[name] = {
                "path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()
            }
        manifest_path = approved / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self._transition(run_id, JobStage.READY_FOR_HUNYUAN, input_manifest=manifest_path)
        return self.get_job(run_id)

    def mark_submitted(self, run_id: str) -> Job:
        self._transition(run_id, JobStage.AWAITING_MANUAL_DOWNLOAD)
        return self.get_job(run_id)

    def register_download(self, run_id: str, source: Path) -> Job:
        job = self.get_job(run_id)
        ensure_transition(job.stage, JobStage.NORMALIZING)
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix.lower() not in {".fbx", ".glb", ".gltf"}:
            raise ValueError("Downloaded model must be FBX, GLB, or GLTF")
        target = self._building_root(job) / "models" / "raw" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f"{target.name}.partial")
        shutil.copy2(source, partial)
        if partial.stat().st_size < 16:
            partial.unlink(missing_ok=True)
            raise ValueError("Downloaded model is empty or incomplete")
        partial.replace(target)
        receipt = target.with_suffix(f"{target.suffix}.receipt.json")
        receipt.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "source_name": source.name,
                    "size_bytes": target.stat().st_size,
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "registered_at": datetime.now(UTC).isoformat(),
                    "capture_mode": "manual_download",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self._transition(run_id, JobStage.NORMALIZING, downloaded_model_path=target)
        return self.get_job(run_id)

    def normalize(self, run_id: str, normalizer: ModelNormalizer) -> Job:
        job = self.get_job(run_id)
        if job.stage != JobStage.NORMALIZING or job.downloaded_model_path is None:
            raise ValueError("Job is not ready for normalization")
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT target_height_m FROM buildings WHERE id = ?", (job.building_id,)
            ).fetchone()
        assert row is not None
        target = self._building_root(job) / "models" / "final" / f"{job.run_id}.fbx"
        normalizer.normalize(job.downloaded_model_path, target, float(row[0]))
        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError("Normalizer did not create a valid FBX artifact")
        self._transition(run_id, JobStage.COMPLETED, final_fbx_path=target)
        return self.get_job(run_id)

    def list_jobs(self) -> list[Job]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_job(self, run_id: str) -> Job:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._row_to_job(row)

    def _building_root(self, job: Job) -> Path:
        return self.settings.paths.projects / job.project_id / "buildings" / job.building_id

    def _transition(self, run_id: str, target: JobStage, **paths: Path) -> None:
        job = self.get_job(run_id)
        ensure_transition(job.stage, target)
        assignments = ["stage = ?", "updated_at = ?"]
        values: list[object] = [target, datetime.now(UTC).isoformat()]
        for column, value in paths.items():
            assignments.append(f"{column} = ?")
            values.append(str(value))
        values.append(run_id)
        with self.database.connect() as connection:
            connection.execute(
                f"UPDATE jobs SET {', '.join(assignments)} WHERE run_id = ?", values
            )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        values = dict(row)

        def path(key: str) -> Path | None:
            value = values[key]
            return Path(str(value)) if value else None
        return Job(
            id=values["id"], project_id=values["project_id"],
            building_id=values["building_id"], run_id=values["run_id"],
            stage=JobStage(values["stage"]), input_manifest=path("input_manifest"),
            downloaded_model_path=path("downloaded_model_path"),
            final_fbx_path=path("final_fbx_path"),
        )
