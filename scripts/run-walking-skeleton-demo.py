"""Repeatable Sprint 1 walking-skeleton demo using an existing Hunyuan GLB."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from npe.application.workflow import BlenderNormalizer
from npe.bootstrap import bootstrap
from npe.shared.config import AppPaths, Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--views", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--normalizer-script", required=True, type=Path)
    args = parser.parse_args()

    settings = Settings(
        paths=AppPaths.under(args.data_root), blender_path=args.blender,
        minimum_free_disk_bytes=0,
    )
    service = bootstrap(settings).workflow
    job = service.create_job("Sprint 1 live demo", 35.7577, 51.4099, 200, "B001", 24)
    view_paths = {
        name: next(args.views.glob(f"{name}.*"))
        for name in ("front", "back", "left", "right", "top")
    }
    service.attach_views(job.run_id, view_paths)
    service.mark_submitted(job.run_id)
    service.register_download(job.run_id, args.model)
    complete = service.normalize(
        job.run_id, BlenderNormalizer(args.blender, args.normalizer_script)
    )
    print(json.dumps({
        "run_id": complete.run_id,
        "stage": complete.stage,
        "final_fbx_path": str(complete.final_fbx_path),
    }, indent=2))


if __name__ == "__main__":
    main()
