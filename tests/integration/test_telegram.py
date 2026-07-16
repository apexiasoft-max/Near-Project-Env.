from __future__ import annotations

from pathlib import Path

from PIL import Image

from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate
from npe.infrastructure.telegram import TelegramNotifier
from npe.shared.config import AppPaths, Settings


def test_pending_intervention_is_sent_once_without_leaking_token(tmp_path: Path) -> None:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    job = container.workflow.create_job("P", 35.7, 51.4, 100, "MAIN", 1)
    aerial = tmp_path / "aerial.png"
    Image.new("RGB", (32, 32)).save(aerial)
    polygon = ((51.3999, 35.6999), (51.4001, 35.6999),
               (51.4001, 35.7001), (51.3999, 35.7001))
    building = container.inventory.build(
        job.project_id,
        AerialCoverage(aerial, 51.398, 35.698, 51.402, 35.702),
        [FootprintCandidate(polygon, "fixture")],
    ).buildings[0]
    container.reference_review.mark_missing(job.project_id, building.id, "system")
    calls: list[tuple[str, dict[str, str]]] = []

    def fake(method: str, payload: dict[str, str]) -> dict[str, object]:
        calls.append((method, payload))
        return {"ok": True, "result": {"message_id": 1}}

    notifier = TelegramNotifier(container.database, "secret-token", "123", fake)
    assert notifier.dispatch_pending().sent == 1
    assert notifier.dispatch_pending().sent == 0
    assert calls[0][0] == "sendMessage"
    assert "MissingReference" in calls[0][1]["text"]
    assert "secret-token" not in str(calls)


def test_chat_id_can_be_discovered_after_start_message(tmp_path: Path) -> None:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )

    def fake(_method: str, _payload: dict[str, str]) -> dict[str, object]:
        return {"ok": True, "result": [{"message": {"chat": {"id": 456}}}]}

    notifier = TelegramNotifier(container.database, "token", None, fake)
    assert notifier.discover_chat_id() == "456"
