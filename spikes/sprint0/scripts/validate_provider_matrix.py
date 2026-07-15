"""Validate the Sprint 0 provider observation matrix using the stdlib only."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROVIDERS = {"google", "neshan"}
ACCESS_STATES = {"accessible", "blocked", "login_required", "captcha", "error"}
CONFIDENCE = {"none", "low", "medium", "high"}
IMAGERY_TYPES = {"aerial", "street", "360"}


class MatrixValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MatrixValidationError(message)


def validate_matrix(data: dict[str, Any], require_complete: bool = False) -> None:
    _require(data.get("schema_version") == 1, "schema_version must be 1")
    sites = data.get("sites")
    _require(isinstance(sites, list) and len(sites) >= 5, "at least five sites are required")

    site_ids: set[str] = set()
    for index, site in enumerate(sites):
        prefix = f"sites[{index}]"
        site_id = site.get("site_id")
        _require(isinstance(site_id, str) and site_id, f"{prefix}.site_id is required")
        _require(site_id not in site_ids, f"duplicate site_id: {site_id}")
        site_ids.add(site_id)

        latitude = site.get("latitude")
        longitude = site.get("longitude")
        _require(isinstance(latitude, (int, float)) and -90 <= latitude <= 90, f"{site_id}: invalid latitude")
        _require(isinstance(longitude, (int, float)) and -180 <= longitude <= 180, f"{site_id}: invalid longitude")

        observations = site.get("observations")
        _require(isinstance(observations, list), f"{site_id}: observations must be a list")
        seen_providers: set[str] = set()
        for observation in observations:
            provider = observation.get("provider")
            _require(provider in PROVIDERS, f"{site_id}: unsupported provider {provider!r}")
            _require(provider not in seen_providers, f"{site_id}: duplicate {provider} observation")
            seen_providers.add(provider)
            _require(observation.get("access_state") in ACCESS_STATES, f"{site_id}/{provider}: invalid access_state")
            _require(observation.get("attribution_confidence") in CONFIDENCE, f"{site_id}/{provider}: invalid confidence")
            imagery = observation.get("imagery_types", [])
            _require(isinstance(imagery, list) and set(imagery) <= IMAGERY_TYPES, f"{site_id}/{provider}: invalid imagery_types")
            _require(isinstance(observation.get("failure_modes", []), list), f"{site_id}/{provider}: failure_modes must be a list")
            _require(isinstance(observation.get("evidence_refs", []), list), f"{site_id}/{provider}: evidence_refs must be a list")

        if require_complete:
            _require(seen_providers == PROVIDERS, f"{site_id}: observations required for Google and Neshan")


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        print("usage: validate_provider_matrix.py PATH [--require-complete]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    require_complete = len(argv) == 3 and argv[2] == "--require-complete"
    try:
        validate_matrix(json.loads(path.read_text(encoding="utf-8")), require_complete=require_complete)
    except (OSError, json.JSONDecodeError, MatrixValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

