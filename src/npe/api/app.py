"""FastAPI entrypoint."""

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from npe.bootstrap import Container, bootstrap
from npe.domain.approval import ApprovalGate
from npe.domain.inventory import AerialCoverage, FootprintCandidate


def create_app(container: Container | None = None) -> Any:
    from fastapi import FastAPI

    active = bootstrap() if container is None else container
    app = FastAPI(title="Near Project Environment", version="0.1.0")

    class CreateJobRequest(BaseModel):
        name: str = Field(min_length=1)
        latitude: float = Field(ge=-90, le=90)
        longitude: float = Field(ge=-180, le=180)
        radius_m: int = Field(gt=0, le=200)
        building_code: str = Field(min_length=1)
        target_height_m: float = Field(gt=0)
        output_path: Path | None = None

    class CreateProjectRequest(BaseModel):
        name: str = Field(min_length=1)
        latitude: float = Field(ge=-90, le=90)
        longitude: float = Field(ge=-180, le=180)
        radius_m: int = Field(gt=0, le=200)
        output_path: Path | None = None

    class CreateRevisionRequest(BaseModel):
        gate: ApprovalGate
        payload: dict[str, object]
        actor: str = Field(min_length=1)
        comment: str = ""
        building_id: str | None = None

    class ApproveRequest(BaseModel):
        actor: str = Field(min_length=1)
        comment: str = ""

    class BatchApproveRequest(BaseModel):
        gate: ApprovalGate
        building_ids: list[str]
        excluded_building_ids: list[str] = Field(default_factory=list)
        actor: str = Field(min_length=1)
        comment: str = ""

    class InventoryCandidateRequest(BaseModel):
        polygon: list[tuple[float, float]] = Field(min_length=3)
        source: str = Field(min_length=1)
        floors: int | None = Field(default=None, gt=0)
        height_m: float | None = Field(default=None, gt=0)
        front_bearing_deg: float | None = Field(default=None, ge=0, lt=360)

    class BuildInventoryRequest(BaseModel):
        image_path: Path
        west: float
        south: float
        east: float
        north: float
        candidates: list[InventoryCandidateRequest]

    class UpdateBuildingRequest(BaseModel):
        polygon: list[tuple[float, float]] = Field(min_length=3)
        floors: int | None = Field(default=None, gt=0)
        height_m: float = Field(gt=0)
        front_bearing_deg: float | None = Field(default=None, ge=0, lt=360)

    class ApproveInventoryRequest(BaseModel):
        actor: str = Field(min_length=1)
        comment: str = ""

    class HeightEstimateRequest(BaseModel):
        method: str
        floors: int | None = Field(default=None, gt=0)
        floor_height_m: float = 3.0
        shadow_length_m: float | None = None
        reference_shadow_m: float | None = None
        reference_height_m: float | None = None
        occluded: bool = False
        height_m: float | None = None
        reason: str = ""

    @app.get("/api/v1/health")
    def health() -> dict[str, object]:
        return active.health.inspect().to_dict()

    @app.post("/api/v1/jobs")
    def create_job(request: CreateJobRequest) -> dict[str, object]:
        job = active.workflow.create_job(**request.model_dump())
        return {"run_id": job.run_id, "stage": job.stage}

    @app.get("/api/v1/jobs")
    def list_jobs() -> list[dict[str, object]]:
        return [
            {
                "run_id": job.run_id,
                "project_id": job.project_id,
                "building_id": job.building_id,
                "stage": job.stage,
                "final_fbx_path": str(job.final_fbx_path) if job.final_fbx_path else None,
            }
            for job in active.workflow.list_jobs()
        ]

    @app.get("/api/v1/projects")
    def list_projects() -> list[dict[str, object]]:
        return [
            {
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "latitude": project.latitude,
                "longitude": project.longitude,
                "radius_m": project.radius_m,
                "output_path": str(project.output_path),
                "building_count": project.building_count,
                "completed_jobs": project.completed_jobs,
                "total_jobs": project.total_jobs,
            }
            for project in active.lifecycle.list_projects()
        ]

    @app.post("/api/v1/projects")
    def create_project(request: CreateProjectRequest) -> dict[str, object]:
        project = active.lifecycle.create(**request.model_dump())
        return {
            "id": project.id,
            "status": project.status,
            "building_count": project.building_count,
            "output_path": str(project.output_path),
        }

    @app.post("/api/v1/projects/{project_id}/commands/{command}")
    def project_command(project_id: str, command: str) -> dict[str, object]:
        from fastapi import HTTPException

        commands = {
            "start": active.lifecycle.start,
            "pause": active.lifecycle.pause,
            "resume": active.lifecycle.resume,
            "cancel": active.lifecycle.cancel,
        }
        if command not in commands:
            raise HTTPException(status_code=404, detail="Unknown project command")
        try:
            project = commands[command](project_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Project not found") from error
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"id": project.id, "status": project.status}

    @app.get("/api/v1/events")
    def progress_events(once: bool = False) -> Any:
        from fastapi.responses import StreamingResponse

        def stream() -> Iterator[str]:
            while True:
                projects = active.lifecycle.list_projects()
                payload = [
                    {
                        "id": project.id,
                        "status": project.status,
                        "building_count": project.building_count,
                        "completed_jobs": project.completed_jobs,
                        "total_jobs": project.total_jobs,
                    }
                    for project in projects
                ]
                yield f"event: projects\ndata: {json.dumps(payload)}\n\n"
                if once:
                    return
                time.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/v1/projects/{project_id}/revisions")
    def create_revision(
        project_id: str, request: CreateRevisionRequest
    ) -> dict[str, object]:
        revision = active.approvals.create_revision(
            project_id, request.gate, request.payload, request.actor,
            request.comment, request.building_id,
        )
        return {
            "id": revision.id, "gate": revision.gate, "version": revision.version,
            "content_hash": revision.content_hash,
        }

    @app.post("/api/v1/revisions/{revision_id}/approve")
    def approve_revision(
        revision_id: str, request: ApproveRequest
    ) -> dict[str, object]:
        approval = active.approvals.approve(
            revision_id, request.actor, request.comment
        )
        return {"id": approval.id, "revision_id": approval.revision_id}

    @app.post("/api/v1/projects/{project_id}/approvals/batch")
    def batch_approve(
        project_id: str, request: BatchApproveRequest
    ) -> list[dict[str, object]]:
        approvals = active.approvals.batch_approve(
            project_id, request.gate, request.building_ids,
            request.excluded_building_ids, request.actor, request.comment,
        )
        return [{"id": item.id, "building_id": item.building_id} for item in approvals]

    @app.get("/api/v1/projects/{project_id}/audit")
    def audit_timeline(project_id: str) -> list[dict[str, object]]:
        return [
            {
                "id": event.id,
                "building_id": event.building_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "comment": event.comment,
                "changes_json": event.changes_json,
                "created_at": event.created_at,
            }
            for event in active.approvals.audit_timeline(project_id)
        ]

    @app.post("/api/v1/projects/{project_id}/inventory")
    def build_inventory(
        project_id: str, request: BuildInventoryRequest
    ) -> dict[str, object]:
        from fastapi import HTTPException

        coverage = AerialCoverage(
            request.image_path, request.west, request.south, request.east, request.north
        )
        candidates = [
            FootprintCandidate(
                tuple(item.polygon), item.source, item.floors,
                item.height_m, item.front_bearing_deg,
            )
            for item in request.candidates
        ]
        try:
            result = active.inventory.build(project_id, coverage, candidates)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Project not found") from error
        except (ValueError, FileNotFoundError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "building_count": len(result.buildings),
            "original_aerial": str(result.original_aerial),
            "coded_aerial": str(result.coded_aerial),
            "geojson": str(result.geojson),
            "csv": str(result.csv),
            "buildings": [
                {
                    "id": item.id, "code": item.code,
                    "boundary_intersection": item.boundary_intersection,
                    "height_m": item.height_m,
                }
                for item in result.buildings
            ],
        }

    @app.patch("/api/v1/projects/{project_id}/buildings/{building_id}")
    def update_building(
        project_id: str, building_id: str, request: UpdateBuildingRequest
    ) -> dict[str, object]:
        item = active.inventory.update_building(
            project_id, building_id, polygon=tuple(request.polygon),
            floors=request.floors, height_m=request.height_m,
            front_bearing_deg=request.front_bearing_deg,
        )
        return {"id": item.id, "code": item.code, "height_m": item.height_m}

    @app.delete("/api/v1/projects/{project_id}/buildings/{building_id}", status_code=204)
    def delete_building(project_id: str, building_id: str) -> None:
        active.inventory.soft_delete(project_id, building_id)

    @app.post("/api/v1/projects/{project_id}/inventory/approve")
    def approve_inventory(
        project_id: str, request: ApproveInventoryRequest
    ) -> dict[str, object]:
        approval = active.inventory.approve(project_id, request.actor, request.comment)
        return {"approval_id": approval.id, "revision_id": approval.revision_id}

    @app.post("/api/v1/projects/{project_id}/buildings/{building_id}/height")
    def estimate_height(
        project_id: str, building_id: str, request: HeightEstimateRequest
    ) -> dict[str, object]:
        if request.method == "floor_count" and request.floors is not None:
            estimate = active.height.from_floors(request.floors, request.floor_height_m)
        elif request.method == "calibrated_shadow" and all(
            value is not None for value in (
                request.shadow_length_m, request.reference_shadow_m,
                request.reference_height_m,
            )
        ):
            estimate = active.height.from_calibrated_shadow(
                request.shadow_length_m or 0, request.reference_shadow_m or 0,
                request.reference_height_m or 0, occluded=request.occluded,
            )
        elif request.method == "human_override" and request.height_m is not None:
            estimate = active.height.override(request.height_m, request.floors, request.reason)
        else:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="Evidence does not match height method")
        active.height.apply(project_id, building_id, estimate)
        return {
            "height_m": estimate.height_m, "floors": estimate.floors,
            "minimum_m": estimate.minimum_m, "maximum_m": estimate.maximum_m,
            "method": estimate.method, "confidence": estimate.confidence,
            "evidence": estimate.evidence,
        }

    return app


def main() -> None:
    import uvicorn

    container = bootstrap()
    uvicorn.run(
        create_app(container),
        host=container.settings.api_host,
        port=container.settings.api_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
