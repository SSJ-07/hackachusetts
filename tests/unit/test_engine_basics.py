"""Unit tests for GTFS fundamentals and a golden round trip."""

from __future__ import annotations

from engine import round_trip
from engine.gtfs import fmt_gtfs_time, haversine_m, parse_gtfs_time
from engine.synth import build_grid_feed

DATE = "2026-11-12"


def test_parse_gtfs_time_past_midnight() -> None:
    assert parse_gtfs_time("24:30:00") == 88200
    assert parse_gtfs_time("25:10:00") == 90600
    assert parse_gtfs_time("07:05:30") == 7 * 3600 + 5 * 60 + 30


def test_fmt_gtfs_time_keeps_hours_over_24() -> None:
    assert fmt_gtfs_time(88200) == "24:30:00"
    assert fmt_gtfs_time(90600) == "25:10:00"


def test_haversine_zero_and_known() -> None:
    assert haversine_m(42.0, -72.6, 42.0, -72.6) == 0.0
    # ~1.0 km between grid stops spaced 0.009 deg lat apart
    d = haversine_m(42.0, -72.6, 42.009, -72.6)
    assert 950 < d < 1050


def test_golden_grid_round_trip() -> None:
    """Hand-checked: 4-stop line, 10:00 appt, 60-min visit, half-hourly service.

    Outbound catches a bus arriving before 09:50 check-in; return leaves after
    11:00; a last useful bus home exists.
    """
    tt = build_grid_feed(n_stops=4, headway=1800, travel=600)
    r = round_trip(tt, "S0", "S3", DATE, 10 * 3600, 60)
    assert r.reachable
    assert r.out_legs[-1].arr <= 10 * 3600 - 600
    first_ret_bus = next(l for l in r.ret_legs if l.kind == "bus")
    assert first_ret_bus.dep >= 11 * 3600
    assert r.last_bus_home is not None


def test_unreachable_when_no_return() -> None:
    """One-directional feed: outbound exists, no return -> unreachable."""
    tt = build_grid_feed(n_stops=4, bidirectional=False)
    r = round_trip(tt, "S0", "S3", DATE, 10 * 3600, 60)
    assert not r.reachable
    assert "return" in r.reason.lower()
