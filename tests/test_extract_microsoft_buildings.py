from scripts.extract_microsoft_buildings import (
    local_xy,
    polygon_intersects_radius,
    segment_distance_to_origin,
)


def test_local_xy_uses_east_and_north_metres() -> None:
    east, north = local_xy(51.001, 35.001, 51.0, 35.0)

    assert 90 < east < 92
    assert 110 < north < 112


def test_segment_crossing_radius_is_detected_when_vertices_are_outside() -> None:
    distance = segment_distance_to_origin((-20.0, 5.0), (20.0, 5.0))

    assert distance == 5.0
    assert polygon_intersects_radius(
        [(-20.0, 5.0), (20.0, 5.0), (20.0, 10.0), (-20.0, 10.0)],
        6.0,
    )


def test_polygon_outside_radius_is_rejected() -> None:
    assert not polygon_intersects_radius(
        [(20.0, 20.0), (30.0, 20.0), (30.0, 30.0), (20.0, 30.0)],
        10.0,
    )
