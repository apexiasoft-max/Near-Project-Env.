from __future__ import annotations

from pathlib import Path

from npe.bootstrap import bootstrap
from npe.domain.workflow import JobStage
from npe.shared.config import AppPaths, Settings


class FakeNormalizer:
    def normalize(self, source: Path, target: Path, height_m: float) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"FBX" + str(height_m).encode() + source.read_bytes())


def settings_at(root: Path) -> Settings:
    return Settings(paths=AppPaths.under(root), minimum_free_disk_bytes=0)


def make_views(root: Path) -> dict[str, Path]:
    result = {}
    for name in ("front", "back", "left", "right", "top"):
        path = root / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"image-{name}".encode())
        result[name] = path
    return result


def test_end_to_end_job_survives_restart(tmp_path: Path) -> None:
    container = bootstrap(settings_at(tmp_path / "data"))
    job = container.workflow.create_job("P", 35.7, 51.4, 200, "B001", 18.0)
    job = container.workflow.attach_views(job.run_id, make_views(tmp_path / "fixtures"))
    assert job.stage == JobStage.READY_FOR_HUNYUAN
    job = container.workflow.mark_submitted(job.run_id)
    assert job.stage == JobStage.AWAITING_MANUAL_DOWNLOAD

    restarted = bootstrap(settings_at(tmp_path / "data"))
    assert restarted.workflow.get_job(job.run_id).stage == JobStage.AWAITING_MANUAL_DOWNLOAD
    raw = tmp_path / "download.glb"
    raw.write_bytes(b"glb")
    restarted.workflow.register_download(job.run_id, raw)
    complete = restarted.workflow.normalize(job.run_id, FakeNormalizer())
    assert complete.stage == JobStage.COMPLETED
    assert complete.final_fbx_path is not None and complete.final_fbx_path.is_file()


def test_waiting_download_does_not_block_another_job(tmp_path: Path) -> None:
    service = bootstrap(settings_at(tmp_path / "data")).workflow
    first = service.create_job("P1", 35.7, 51.4, 100, "B001", 12)
    service.attach_views(first.run_id, make_views(tmp_path / "one"))
    service.mark_submitted(first.run_id)
    second = service.create_job("P2", 35.8, 51.5, 100, "B002", 15)
    service.attach_views(second.run_id, make_views(tmp_path / "two"))
    assert service.get_job(first.run_id).stage == JobStage.AWAITING_MANUAL_DOWNLOAD
    assert service.get_job(second.run_id).stage == JobStage.READY_FOR_HUNYUAN
