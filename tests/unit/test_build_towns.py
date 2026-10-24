"""Unit tests for pipeline/build_towns.py (block group -> town, no shapely)."""

from __future__ import annotations

import pandas as pd
from hypothesis import given, strategies as st

from pipeline.build_towns import assign, normalise_town, point_in_ring, point_in_shape

SQUARE = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
HOLE = [(0.4, 0.4), (0.6, 0.4), (0.6, 0.6), (0.4, 0.6), (0.4, 0.4)]


def test_normalise_town_strips_tiger_suffixes():
    assert normalise_town("Agawam Town") == "Agawam"
    assert normalise_town("Greenfield") == "Greenfield"
    assert normalise_town(" Palmer Town ") == "Palmer"


@given(st.floats(min_value=-2, max_value=3), st.floats(min_value=-2, max_value=3))
def test_point_in_unit_square(x, y):
    inside = 0.0 < x < 1.0 and 0.0 < y < 1.0
    on_edge = x in (0.0, 1.0) or y in (0.0, 1.0)
    if not on_edge:
        assert point_in_ring(x, y, SQUARE) == inside


def test_hole_flips_parity():
    assert point_in_shape(0.2, 0.2, [SQUARE, HOLE]) is True
    assert point_in_shape(0.5, 0.5, [SQUARE, HOLE]) is False


def _town(name, x0, y0, x1, y1, county="Franklin"):
    ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    return {"town": name, "town_geoid": name.upper(), "county": county, "rings": [ring],
            "bbox": (x0, y0, x1, y1), "int_pt": ((x0 + x1) / 2, (y0 + y1) / 2)}


def test_assign_polygon_then_nearest_fallback():
    towns = [_town("West", 0, 0, 1, 1), _town("East", 1, 0, 2, 1)]
    origins = pd.DataFrame([
        {"bg_geoid": "A", "lon": 0.5, "lat": 0.5},   # inside West
        {"bg_geoid": "B", "lon": 1.7, "lat": 0.2},   # inside East
        {"bg_geoid": "C", "lon": 1.9, "lat": 1.3},   # outside both -> nearest = East
    ])
    out = assign(origins, towns).set_index("bg_geoid")
    assert out.loc["A", "town"] == "West" and out.loc["A", "method"] == "polygon"
    assert out.loc["B", "town"] == "East"
    assert out.loc["C", "town"] == "East" and out.loc["C", "method"] == "nearest"
    assert set(out.columns) == {"town", "town_geoid", "county", "method"}
