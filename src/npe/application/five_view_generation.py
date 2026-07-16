"""Versioned five-view prompt assembly and retry orchestration."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from npe.domain.five_view import REQUIRED_DIRECTIONS, FiveViewRequest, GenerationResult
from npe.shared.config import Settings

PROMPT_VERSION = "2026-07-16.1"
PROVIDER_VERSION = "chatgpt-web-v1"
MAX_ATTEMPTS = 2


class TransientGenerationError(RuntimeError):
    """A generation failure that is safe to retry."""


class GenerationProvider(Protocol):
    def generate(
        self, prompt: str, references: tuple[Path, ...], output_path: Path,
    ) -> dict[str, object]: ...


@dataclass(frozen=True)
class PromptTemplate:
    version: str = PROMPT_VERSION

    def render(self, request: FiveViewRequest) -> str:
        floors = "unknown; infer from references" if request.floors is None else str(request.floors)
        bearing = (
            "unknown; use the visible main entrance as FRONT"
            if request.front_bearing_deg is None
            else f"{request.front_bearing_deg:.1f} degrees"
        )
        directions = ", ".join(direction.upper() for direction in REQUIRED_DIRECTIONS)
        return (
            f"Five-view contract {self.version}. Generate one consistent architectural sheet "
            f"of this exact referenced building with panels: {directions}. Target height: "
            f"{request.target_height_m:.2f} meters. Floors: {floors}. Front bearing: {bearing}. "
            "Preserve the real architectural identity, geometry, openings, balconies, massing, "
            "colored facade textures, materials and scale across every view. Do not make the "
            "building white, gray, clay, monochrome or untextured. Use a uniform dark neutral-gray "
            "studio background, approximately RGB 72,76,82, with clear silhouette separation. "
            "Use orthographic-like cameras; center the complete uncropped building at 65-85% of "
            "each panel. Add no sky, street, vegetation, neighbors, labels, people, vehicles or "
            "ground clutter. Return a single image sheet only."
        )


class FiveViewGenerationService:
    def __init__(
        self, settings: Settings, provider: GenerationProvider,
        run_id_factory: Callable[[], str],
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.run_id_factory = run_id_factory
        self.template = PromptTemplate()

    def generate(self, request: FiveViewRequest) -> GenerationResult:
        request.validate()
        run_id = self.run_id_factory()
        root = self.settings.paths.projects / request.project_id / "five-view" / run_id
        root.mkdir(parents=True, exist_ok=False)
        prompt = self.template.render(request)
        hashes = {str(path.resolve()): _sha256(path) for path in request.reference_paths}
        manifest_path = root / "input-manifest.json"
        output_path = root / "original-sheet.png"
        diagnostics_path = root / "provider-diagnostics.json"
        manifest = {
            "schema_version": 1,
            "run_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "project_id": request.project_id,
            "building_id": request.building_id,
            "prompt_template_version": self.template.version,
            "provider_version": PROVIDER_VERSION,
            "required_directions": list(REQUIRED_DIRECTIONS),
            "target_height_m": request.target_height_m,
            "floors": request.floors,
            "front_bearing_deg": request.front_bearing_deg,
            "reference_hashes": hashes,
            "prompt": prompt,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        failures: list[dict[str, object]] = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                diagnostics = self.provider.generate(prompt, request.reference_paths, output_path)
                if not output_path.is_file() or output_path.stat().st_size == 0:
                    raise TransientGenerationError("provider returned no output")
                payload = {
                    "run_id": run_id,
                    "attempt": attempt,
                    "status": "completed",
                    "provider": diagnostics,
                    "failures": failures,
                    "output_sha256": _sha256(output_path),
                    "completed_at": datetime.now(UTC).isoformat(),
                }
                diagnostics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                return GenerationResult(
                    run_id, attempt, output_path, manifest_path, diagnostics_path
                )
            except TransientGenerationError as error:
                failures.append({"attempt": attempt, "error": str(error)})
                if attempt == MAX_ATTEMPTS:
                    diagnostics_path.write_text(
                        json.dumps(
                            {"run_id": run_id, "status": "failed", "failures": failures},
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    raise
        raise AssertionError("unreachable")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
