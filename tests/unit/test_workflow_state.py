from __future__ import annotations

import pytest

from npe.domain.workflow import JobStage, ensure_transition


def test_valid_and_invalid_job_transitions() -> None:
    ensure_transition(JobStage.AWAITING_VIEWS, JobStage.READY_FOR_HUNYUAN)
    with pytest.raises(ValueError):
        ensure_transition(JobStage.AWAITING_VIEWS, JobStage.COMPLETED)
