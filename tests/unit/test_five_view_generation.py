from __future__ import annotations

import json
from pathlib import Path

import pytest

from npe.application.five_view_generation import (
    FiveViewGenerationService,
    PromptTemplate,
    TransientGenerationError,
)
from npe.domain.five_view import FiveViewRequest
from npe.shared.config import AppPaths, Settings


class FakeProvider:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.calls = 0

    def generate(
        self, prompt: str, references: tuple[Path, ...], output_path: Path,
    ) -> dict[str, object]:
        self.calls += 1
        if self.calls <= self.failures:
            raise TransientGenerationError("temporary timeout")
        output_path.write_bytes(b"valid-image-output")
        return {"page_health": "ready", "reference_count": len(references)}


def request_with(reference: Path) -> FiveViewRequest:
    return FiveViewRequest("PRJ-1", "BLD-1", (reference,), 31.5, 9, 170.0)


def test_prompt_contains_geometry_directions_and_material_contract(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"ref")

    prompt = PromptTemplate().render(request_with(reference))

    assert all(direction in prompt for direction in ("FRONT", "BACK", "LEFT", "RIGHT", "TOP"))
    assert "31.50 meters" in prompt
    assert "Floors: 9" in prompt
    assert "colored facade textures" in prompt
    assert "RGB 72,76,82" in prompt


def test_generation_persists_versioned_manifest_hashes_and_output(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"reference-content")
    settings = Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    settings.paths.initialize()
    service = FiveViewGenerationService(settings, FakeProvider(), lambda: "RUN-S4-001")

    result = service.generate(request_with(reference))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    diagnostics = json.loads(result.diagnostics_path.read_text(encoding="utf-8"))

    assert result.output_path.read_bytes() == b"valid-image-output"
    assert manifest["run_id"] == "RUN-S4-001"
    assert manifest["prompt_template_version"]
    assert manifest["provider_version"] == "chatgpt-web-v1"
    assert len(next(iter(manifest["reference_hashes"].values()))) == 64
    assert diagnostics["status"] == "completed"
    assert diagnostics["output_sha256"]


def test_transient_failure_retries_once_then_succeeds(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"ref")
    provider = FakeProvider(failures=1)
    settings = Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    settings.paths.initialize()

    result = FiveViewGenerationService(
        settings, provider, lambda: "RUN-S4-002"
    ).generate(request_with(reference))

    assert provider.calls == 2
    assert result.attempt == 2


def test_second_transient_failure_is_recorded_and_raised(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"ref")
    settings = Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    settings.paths.initialize()
    service = FiveViewGenerationService(
        settings, FakeProvider(failures=2), lambda: "RUN-S4-003"
    )

    with pytest.raises(TransientGenerationError, match="temporary timeout"):
        service.generate(request_with(reference))

    diagnostics = settings.paths.projects / "PRJ-1/five-view/RUN-S4-003/provider-diagnostics.json"
    payload = json.loads(diagnostics.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert len(payload["failures"]) == 2
