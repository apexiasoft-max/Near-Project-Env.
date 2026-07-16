from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from npe.api.app import create_app
from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings
from npe.worker.runner import write_heartbeat


def test_health_endpoint_uses_versioned_loopback_contract(tmp_path: Path) -> None:
    settings = Settings(paths=AppPaths.under(tmp_path), minimum_free_disk_bytes=0)
    container = bootstrap(settings)
    write_heartbeat(settings.paths.runtime / "worker.heartbeat")
    response = TestClient(create_app(container)).get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"status", "database", "disk", "worker", "browser", "blender"}
    assert payload["database"]["status"] == "ok"


def test_project_dashboard_and_progress_event_contract(tmp_path: Path) -> None:
    settings = Settings(paths=AppPaths.under(tmp_path), minimum_free_disk_bytes=0)
    container = bootstrap(settings)
    job = container.workflow.create_job("P", 35.7, 51.4, 100, "B1", 12)
    client = TestClient(create_app(container))

    projects = client.get("/api/v1/projects")
    assert projects.status_code == 200
    assert projects.json()[0]["id"] == job.project_id
    assert projects.json()[0]["status"] == "draft"

    events = client.get("/api/v1/events?once=true")
    assert events.status_code == 200
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: projects" in events.text
    assert job.project_id in events.text
