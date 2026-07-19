"""Parse local OpenStreetMap XML into reviewable building candidates."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from npe.domain.inventory import FootprintCandidate


def building_candidates(path: Path) -> list[FootprintCandidate]:
    root = ET.parse(path).getroot()
    nodes = {
        node.attrib["id"]: (float(node.attrib["lon"]), float(node.attrib["lat"]))
        for node in root.findall("node")
    }
    candidates: list[FootprintCandidate] = []
    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        if "building" not in tags:
            continue
        polygon = tuple(
            nodes[reference.attrib["ref"]]
            for reference in way.findall("nd")
            if reference.attrib["ref"] in nodes
        )
        if len(polygon) > 1 and polygon[0] == polygon[-1]:
            polygon = polygon[:-1]
        if len(polygon) < 3:
            continue
        floors = _positive_int(tags.get("building:levels"))
        height = _height_m(tags.get("height"))
        candidates.append(FootprintCandidate(
            polygon, f"osm:{way.attrib['id']}", floors=floors, height_m=height,
        ))
    return candidates


def _positive_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        result = int(float(value))
    except ValueError:
        return None
    return result if result > 0 else None


def _height_m(value: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.lower().replace("meters", "").replace("meter", "").replace("m", "")
    try:
        result = float(normalized.strip())
    except ValueError:
        return None
    return result if result > 0 else None
