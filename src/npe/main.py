"""Primary Windows launcher for desktop, API, and worker processes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence


def component_command(component: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--component", component]
    module = {
        "api": "npe.api.app",
        "worker": "npe.worker.runner",
        "desktop": "npe.desktop.app",
    }[component]
    return [sys.executable, "-m", module]


def hidden_creation_flags() -> int:
    if sys.platform != "win32":
        return 0
    return subprocess.CREATE_NO_WINDOW


def launch_all() -> int:
    children = [
        subprocess.Popen(
            component_command("worker"), creationflags=hidden_creation_flags()
        ),
        subprocess.Popen(component_command("api"), creationflags=hidden_creation_flags()),
    ]
    try:
        from npe.desktop.app import main as desktop_main

        desktop_main()
    finally:
        for child in children:
            child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--component", choices=("all", "api", "worker", "desktop"), default="all"
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.component == "all":
        return launch_all()
    if args.component == "api":
        from npe.api.app import main as api_main

        api_main()
        return 0
    if args.component == "worker":
        from npe.worker.runner import run_worker

        run_worker(once=args.once)
        return 0
    from npe.desktop.app import main as desktop_main

    desktop_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
