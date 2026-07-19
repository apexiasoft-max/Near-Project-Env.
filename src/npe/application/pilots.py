"""Immutable pilot evidence and objective MVP sign-off evaluation."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from npe.shared.config import Settings

RUN_ID = re.compile(r"PILOT-[A-Z0-9-]{3,40}")
MANUAL_BASELINE_MINUTES = 4 * 8 * 60


@dataclass(frozen=True)
class PilotBlocker:
    title: str
    severity: str
    status: str
    owner: str


@dataclass(frozen=True)
class PilotRun:
    run_id: str
    project_name: str
    kind: str
    real_project: bool
    workstation: str
    building_count: int
    duration_minutes: float
    active_human_minutes: float
    completed: bool
    blockers: tuple[PilotBlocker, ...] = ()


@dataclass(frozen=True)
class PilotSignoff:
    passed: bool
    typical_validation_passed: bool
    real_pilot_count: int
    open_critical_blockers: int
    average_active_human_minutes: float | None
    human_time_reduction: float | None
    reasons: tuple[str, ...]


class PilotEvidenceService:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.paths.root / "reports" / "pilots"

    def record(self, run: PilotRun) -> Path:
        self._validate(run)
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / f"{run.run_id}.json"
        if target.exists():
            raise FileExistsError(f"Pilot evidence is immutable: {run.run_id}")
        payload = {**asdict(run), "recorded_at": datetime.now(UTC).isoformat()}
        self._write_json(target, payload)
        return target

    def start_session(
        self, run_id: str, project_name: str, project_id: str, *,
        latitude: float, longitude: float, radius_m: int,
    ) -> Path:
        if RUN_ID.fullmatch(run_id) is None:
            raise ValueError("Invalid pilot run ID")
        if not project_name.strip() or not project_id.strip() or radius_m <= 0:
            raise ValueError("Pilot session metadata is invalid")
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / f"{run_id}.session.json"
        if target.exists():
            return target
        self._write_json(target, {
            "run_id": run_id,
            "project_name": project_name,
            "project_id": project_id,
            "latitude": latitude,
            "longitude": longitude,
            "radius_m": radius_m,
            "started_at": datetime.now(UTC).isoformat(),
            "active_human_events": [],
        })
        return target

    def record_human_event(self, run_id: str, activity: str, minutes: float) -> Path:
        if not activity.strip() or minutes <= 0:
            raise ValueError("Human activity and positive minutes are required")
        target = self.root / f"{run_id}.session.json"
        if not target.exists():
            raise FileNotFoundError(f"Pilot session is not started: {run_id}")
        payload = json.loads(target.read_text(encoding="utf-8"))
        payload["active_human_events"].append({
            "activity": activity,
            "minutes": minutes,
            "recorded_at": datetime.now(UTC).isoformat(),
        })
        self._write_json(target, payload)
        return target

    def import_typical_gate(self, gate_result: Path) -> Path:
        payload = json.loads(gate_result.read_text(encoding="utf-8"))
        if payload.get("passed") is not True:
            raise ValueError("Typical gate must have passed")
        count = int(payload.get("building_count", 0))
        run = PilotRun(
            "PILOT-TYPICAL-S6", "Typical Tehran validation", "typical", False,
            "automated-gate", count, float(payload.get("runtime_seconds", 0)) / 60,
            float(payload.get("active_human_minutes", 0)), True,
        )
        target = self.root / f"{run.run_id}.json"
        if target.exists():
            return target
        return self.record(run)

    def list_runs(self) -> list[PilotRun]:
        if not self.root.exists():
            return []
        return [self._load(path) for path in sorted(self.root.glob("PILOT-*.json"))]

    def evaluate(self) -> PilotSignoff:
        runs = self.list_runs()
        typical = any(
            run.kind == "typical" and run.completed and 10 <= run.building_count <= 20
            for run in runs
        )
        pilots = [run for run in runs if run.kind == "pilot" and run.real_project and run.completed]
        critical = [
            blocker
            for run in runs
            for blocker in run.blockers
            if blocker.severity == "critical" and blocker.status not in {"resolved", "accepted"}
        ]
        average = (
            sum(run.active_human_minutes for run in pilots) / len(pilots) if pilots else None
        )
        reduction = None if average is None else 1 - average / MANUAL_BASELINE_MINUTES
        reasons = []
        if not typical:
            reasons.append("Typical 10-20 building validation is missing or failed")
        if len(pilots) < 2:
            reasons.append("Two completed real internal pilots are required")
        if critical:
            reasons.append("Critical blockers remain unresolved or unaccepted")
        if reduction is None or reduction < 0.75:
            reasons.append("Active human time reduction is below 75%")
        return PilotSignoff(
            not reasons, typical, len(pilots), len(critical), average, reduction,
            tuple(reasons),
        )

    def write_signoff(self) -> Path:
        result = self.evaluate()
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / "mvp-signoff.json"
        self._write_json(target, asdict(result))
        report = self.root / "mvp-signoff.md"
        status = "GO" if result.passed else "NOT READY"
        reasons = "\n".join(f"- {reason}" for reason in result.reasons) or "- None"
        reduction = (
            "n/a" if result.human_time_reduction is None
            else f"{result.human_time_reduction:.1%}"
        )
        report.write_text(
            f"""# MVP Sign-off

Status: **{status}**

- Typical validation: {result.typical_validation_passed}
- Completed real pilots: {result.real_pilot_count}
- Open critical blockers: {result.open_critical_blockers}
- Human-time reduction: {reduction}

## Reasons

{reasons}
""",
            encoding="utf-8",
        )
        return report

    @staticmethod
    def _validate(run: PilotRun) -> None:
        if RUN_ID.fullmatch(run.run_id) is None:
            raise ValueError("Invalid pilot run ID")
        if run.kind not in {"typical", "pilot"}:
            raise ValueError("Pilot kind must be typical or pilot")
        if not run.project_name.strip() or not run.workstation.strip():
            raise ValueError("Project name and workstation are required")
        if run.building_count <= 0 or min(run.duration_minutes, run.active_human_minutes) < 0:
            raise ValueError("Pilot metrics must be non-negative")
        if run.active_human_minutes > run.duration_minutes:
            raise ValueError("Active human time cannot exceed total duration")
        if run.kind == "pilot" and not run.real_project:
            raise ValueError("A pilot evidence record must represent a real project")
        for blocker in run.blockers:
            if blocker.severity not in {"low", "medium", "high", "critical"}:
                raise ValueError("Invalid blocker severity")
            if blocker.status not in {"open", "resolved", "accepted"}:
                raise ValueError("Invalid blocker status")
            if not blocker.owner.strip():
                raise ValueError("Every blocker requires an owner")

    @staticmethod
    def _load(path: Path) -> PilotRun:
        payload = json.loads(path.read_text(encoding="utf-8"))
        blockers = tuple(PilotBlocker(**item) for item in payload.get("blockers", []))
        return PilotRun(
            run_id=payload["run_id"], project_name=payload["project_name"],
            kind=payload["kind"], real_project=payload["real_project"],
            workstation=payload["workstation"], building_count=payload["building_count"],
            duration_minutes=payload["duration_minutes"],
            active_human_minutes=payload["active_human_minutes"],
            completed=payload["completed"], blockers=blockers,
        )

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
