from __future__ import annotations

import argparse
import json
from pathlib import Path

from npe.application.pilots import PilotBlocker, PilotEvidenceService, PilotRun
from npe.shared.config import load_settings


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    typical = sub.add_parser("import-typical")
    typical.add_argument("gate", type=Path)
    record = sub.add_parser("record")
    record.add_argument("evidence", type=Path)
    sub.add_parser("evaluate")
    args = parser.parse_args()
    service = PilotEvidenceService(load_settings())
    if args.command == "import-typical":
        print(service.import_typical_gate(args.gate))
        return 0
    if args.command == "record":
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
        blockers = tuple(PilotBlocker(**item) for item in payload.pop("blockers", []))
        print(service.record(PilotRun(**payload, blockers=blockers)))
        return 0
    report = service.write_signoff()
    result = service.evaluate()
    print(report)
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
