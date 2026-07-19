from __future__ import annotations

from pathlib import Path

from scripts.run_sprint6_gate import run_gate


def test_typical_twelve_building_gate(tmp_path: Path) -> None:
    result = run_gate(tmp_path / "gate")
    assert result["passed"] is True
    assert result["building_count"] == 12
    assert result["completed"] == 9
    assert result["missing"] == 2
    assert result["needs_review"] == 1
    assert result["completion_rate"] == 0.75
