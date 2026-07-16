"""Send one non-sensitive MissingReference event using locally configured secrets."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from npe.bootstrap import bootstrap
from npe.domain.inventory import AerialCoverage, FootprintCandidate
from npe.shared.config import AppPaths, Settings


def main() -> None:
    from npe.shared.config import load_settings

    configured = load_settings()
    with tempfile.TemporaryDirectory(prefix="npe-telegram-live-") as directory:
        settings = Settings(
            paths=AppPaths.under(Path(directory)),
            minimum_free_disk_bytes=0,
            telegram_bot_token=configured.telegram_bot_token,
            telegram_chat_id=configured.telegram_chat_id,
        )
        container = bootstrap(settings)
        job = container.workflow.create_job(
            "Live Telegram Verification", 35.7, 51.4, 100, "MAIN", 1
        )
        aerial = Path(directory) / "aerial.png"
        Image.new("RGB", (32, 32)).save(aerial)
        polygon = (
            (51.3999, 35.6999), (51.4001, 35.6999),
            (51.4001, 35.7001), (51.3999, 35.7001),
        )
        building = container.inventory.build(
            job.project_id,
            AerialCoverage(aerial, 51.398, 35.698, 51.402, 35.702),
            [FootprintCandidate(polygon, "live-verification")],
        ).buildings[0]
        container.reference_review.mark_missing(job.project_id, building.id, "live-test")
        result = container.telegram.dispatch_pending()
        print(f"telegram_live_sent={result.sent} failed={result.failed}")
        if result.sent != 1 or result.failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
