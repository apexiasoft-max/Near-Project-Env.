"""Reproducible 12-building acceptance run for Gate S6."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from npe.application.delivery import DeliveryMetrics
from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings


def run_gate(output_root: Path) -> dict[str, object]:
    root = output_root.resolve()
    runtime = (root / "runtime").resolve()
    if not runtime.is_relative_to(root):
        raise ValueError("Runtime escaped gate output root")
    if runtime.exists():
        shutil.rmtree(runtime)
    container = bootstrap(Settings(paths=AppPaths.under(runtime), minimum_free_disk_bytes=0))
    started = time.perf_counter()
    project_id = "PRJ-GATE-S6"
    now = datetime.now(UTC).isoformat()
    with container.database.connect() as connection:
        connection.execute(
            """INSERT INTO projects
               (id, name, latitude, longitude, radius_m, status, created_at, updated_at,
                output_path) VALUES (?, 'Gate S6 Typical Tehran', 35.7577, 51.4099, 200,
                'running', ?, ?, ?)""",
            (project_id, now, now, str(runtime / "projects" / project_id)),
        )
    source = runtime / "synthetic-source"
    source.mkdir(parents=True)
    inventory = runtime / "projects" / project_id / "inventory"
    inventory.mkdir(parents=True)
    Image.new("RGB", (128, 128), (70, 76, 82)).save(inventory / "aerial_original.png")
    Image.new("RGB", (128, 128), (70, 76, 82)).save(inventory / "aerial_coded.png")
    expected = {"Completed": 9, "MissingReference": 2, "NeedsReview": 1}
    with container.database.connect() as connection:
        for number in range(1, 13):
            code = f"B{number:03d}"
            building_id = f"BLD-GATE-{number:03d}"
            job_id = f"JOB-GATE-{number:03d}"
            status = "needs_review" if number == 12 else "active"
            connection.execute(
                """INSERT INTO buildings
                   (id, project_id, code, target_height_m, status, created_at, updated_at,
                    floors) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (building_id, project_id, code, 9 + number * 3, status, now, now, 3 + number),
            )
            raw = _artifact(source / f"{code}-raw.glb", f"raw-{code}")
            final = _artifact(source / f"{code}-final.fbx", f"final-{code}")
            has_model = number not in {11, 12}
            job_status = "needs_review" if number == 12 else "completed" if has_model else "active"
            connection.execute(
                """INSERT INTO jobs
                   (id, project_id, building_id, run_id, stage, status,
                    downloaded_model_path, final_fbx_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id, project_id, building_id, f"RUN-GATE-{number:03d}",
                    "completed" if has_model else "normalizing", job_status,
                    str(raw) if number != 12 else None,
                    str(final) if has_model else None, now, now,
                ),
            )
            if number not in {10, 12}:
                reference = _artifact(source / f"{code}-reference.jpg", f"reference-{code}")
                connection.execute(
                    """INSERT INTO reference_candidates
                       (id, building_id, provider, source_id, image_path, width_px, height_px,
                        visibility, occlusion, attribution_score, quality_score, total_score,
                        rank, evidence_json, metadata_json, active, selected, rejected, created_at)
                       VALUES (?, ?, 'google', ?, ?, 1920, 1080, .9, .1, .9, .9, .9,
                               1, '{}', '{\"synthetic\":true}', 1, 1, 0, ?)""",
                    (f"REF-GATE-{number:03d}", building_id, f"google-{code}", str(reference), now),
                )
            if number != 12:
                attempt = f"VIEW-GATE-{number:03d}"
                connection.execute(
                    """INSERT INTO five_view_attempts
                       (id, project_id, building_id, run_id, version, status,
                        guidance_json, created_at)
                       VALUES (?, ?, ?, ?, 1, 'approved', '{}', ?)""",
                    (attempt, project_id, building_id, f"RUN-GATE-{number:03d}", now),
                )
                for direction in ("front", "back", "left", "right", "top"):
                    view = _artifact(source / f"{code}-{direction}.png", f"{code}-{direction}")
                    connection.execute(
                        """INSERT INTO five_view_outputs
                           (attempt_id, direction, image_path, sha256, status, guidance)
                           VALUES (?, ?, ?, ?, 'approved', '')""",
                        (attempt, direction, str(view), _sha256(view)),
                    )
    runtime_seconds = time.perf_counter() - started
    metrics = DeliveryMetrics(
        runtime_seconds=runtime_seconds, active_human_minutes=0, error_count=1
    )
    delivery = container.delivery.assemble(project_id, metrics=metrics)
    statuses = _statuses(delivery.package_path / "overview" / "buildings.csv")
    actual = {name: statuses.count(name) for name in expected}
    checks = {
        "representative_building_count": delivery.building_count == 12,
        "failure_isolation": delivery.completed == 9 and delivery.building_count == 12,
        "status_distribution": actual == expected,
        "coded_folders": len(
            list((delivery.package_path / "buildings").glob("B[0-9][0-9][0-9]"))
        ) == 12,
        "package_manifest": (delivery.package_path / "package_manifest.json").is_file(),
        "html_report": (delivery.package_path / "reports" / "process_report.html").is_file(),
    }
    result: dict[str, object] = {
        "gate": "APE-94", "passed": all(checks.values()), "checks": checks,
        "building_count": delivery.building_count, "completed": delivery.completed,
        "missing": delivery.missing, "needs_review": delivery.needs_review,
        "completion_rate": delivery.completion_rate,
        "active_human_minutes": metrics.active_human_minutes,
        "error_count": metrics.error_count, "runtime_seconds": runtime_seconds,
        "delivery_size_bytes": delivery.size_bytes,
        "delivery_path": str(delivery.package_path.relative_to(root)),
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "gate-s6-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    (root / "gate-s6-report.md").write_text(_markdown(result), encoding="utf-8")
    if not result["passed"]:
        raise RuntimeError("Gate S6 failed")
    return result


def _artifact(path: Path, value: str) -> Path:
    path.write_bytes((value * 4).encode())
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _statuses(path: Path) -> list[str]:
    import csv

    with path.open(encoding="utf-8") as handle:
        return [str(row["status"]) for row in csv.DictReader(handle)]


def _markdown(result: dict[str, object]) -> str:
    checks = result["checks"]
    assert isinstance(checks, dict)
    rows = "\n".join(f"- {'PASS' if value else 'FAIL'} — {name}" for name, value in checks.items())
    return f"""# Gate S6 — Typical Project Acceptance

Result: **{'PASS' if result['passed'] else 'FAIL'}**

{rows}

## Metrics

- Buildings: {result['building_count']}
- Completed: {result['completed']}
- Missing: {result['missing']}
- NeedsReview: {result['needs_review']}
- Completion rate: {float(result['completion_rate']):.1%}
- Active human time: {result['active_human_minutes']} minutes
- Errors: {result['error_count']}
- Runtime: {float(result['runtime_seconds']):.3f} seconds
- Delivery disk size: {result['delivery_size_bytes']} bytes
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/sprint6/gate-s6"))
    args = parser.parse_args()
    result = run_gate(args.output_root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
