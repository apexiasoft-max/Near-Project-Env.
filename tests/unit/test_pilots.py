from __future__ import annotations

import json
from pathlib import Path

import pytest

from npe.application.pilots import PilotBlocker, PilotEvidenceService, PilotRun
from npe.shared.config import AppPaths, Settings


def _service(tmp_path: Path) -> PilotEvidenceService:
    return PilotEvidenceService(Settings(paths=AppPaths.under(tmp_path)))


def _pilot(run_id: str, human: float = 180, blockers: tuple[PilotBlocker, ...] = ()) -> PilotRun:
    return PilotRun(
        run_id, run_id, "pilot", True, "dedicated-pc", 12, 600, human, True, blockers
    )


def test_signoff_requires_typical_and_two_real_pilots(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.record(_pilot("PILOT-REAL-001"))
    result = service.evaluate()
    assert not result.passed
    assert not result.typical_validation_passed
    assert result.real_pilot_count == 1


def test_signoff_passes_with_two_pilots_and_75_percent_reduction(tmp_path: Path) -> None:
    service = _service(tmp_path)
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps({"passed": True, "building_count": 12, "runtime_seconds": 60,
                    "active_human_minutes": 0}), encoding="utf-8"
    )
    service.import_typical_gate(gate)
    service.record(_pilot("PILOT-REAL-001", 240))
    service.record(_pilot("PILOT-REAL-002", 240))
    result = service.evaluate()
    assert result.passed
    assert result.human_time_reduction == 0.875
    assert "GO" in service.write_signoff().read_text(encoding="utf-8")


def test_open_critical_blocker_prevents_signoff(tmp_path: Path) -> None:
    service = _service(tmp_path)
    blocker = PilotBlocker("Provider unavailable", "critical", "open", "technical-owner")
    service.record(_pilot("PILOT-REAL-001", blockers=(blocker,)))
    assert service.evaluate().open_critical_blockers == 1


def test_pilot_evidence_is_immutable_and_validated(tmp_path: Path) -> None:
    service = _service(tmp_path)
    run = _pilot("PILOT-REAL-001")
    service.record(run)
    with pytest.raises(FileExistsError):
        service.record(run)
    with pytest.raises(ValueError, match="real project"):
        service.record(PilotRun("PILOT-DEMO-001", "demo", "pilot", False, "pc", 2, 10, 2, True))
