"""Worker process with a durable liveness heartbeat."""

from __future__ import annotations

import argparse
import os
import signal
import time
from pathlib import Path

from npe.bootstrap import bootstrap


def write_heartbeat(path: Path, timestamp: float | None = None) -> None:
    value = time.time() if timestamp is None else timestamp
    temporary = path.with_suffix(".partial")
    temporary.write_text(f"{os.getpid()}\n{value:.6f}\n", encoding="utf-8")
    temporary.replace(path)


def run_worker(once: bool = False, interval_seconds: float = 2.0) -> None:
    container = bootstrap()
    heartbeat = container.settings.paths.runtime / "worker.heartbeat"
    should_stop = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    while not should_stop:
        write_heartbeat(heartbeat)
        if once:
            return
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    run_worker(once=args.once)


if __name__ == "__main__":
    main()

