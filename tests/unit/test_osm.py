from pathlib import Path

from npe.infrastructure.osm import building_candidates


def test_building_candidates_parse_geometry_and_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "map.osm"
    source.write_text(
        """<osm><node id="1" lat="35.0" lon="51.0"/>
        <node id="2" lat="35.0" lon="51.1"/><node id="3" lat="35.1" lon="51.1"/>
        <way id="7"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/>
        <tag k="building" v="yes"/><tag k="building:levels" v="6"/>
        <tag k="height" v="18 m"/></way></osm>""",
        encoding="utf-8",
    )
    candidates = building_candidates(source)
    assert len(candidates) == 1
    assert len(candidates[0].polygon) == 3
    assert candidates[0].source == "osm:7"
    assert candidates[0].floors == 6
    assert candidates[0].height_m == 18
