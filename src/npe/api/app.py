"""FastAPI entrypoint."""

from __future__ import annotations

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
