"""FastAPI entrypoint."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from npe.bootstrap import Container, bootstrap


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

    @app.post("/api/v1/projects/{project_id}/{command}")
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
