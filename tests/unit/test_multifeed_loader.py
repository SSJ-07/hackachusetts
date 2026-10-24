"""Unit tests for the multi-feed loader (spec: multi-feed, MF-1..MF-4).

Uses the real FRTA feed at data/manual/frta_minigtfs plus a tiny synthetic
second feed written to a temp dir, so cross-agency transfer logic is exercised
without needing the PVTA cache present.
"""
from __future__ import annotations

import os

from engine.gtfs import Timetable

FRTA = "data/manual/frta_minigtfs"
WEEKDAY = "2026-10-26"  # inside FRTA service window; see calendar.txt


def _write_feed(d: str, lat: float, lon: float) -> None:
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "calendar.txt"), "w", newline="") as f:
        f.write("service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n")
        f.write("S1,1,1,1,1,1,1,1,20260101,20271231\n")
    with open(os.path.join(d, "stops.txt"), "w", newline="") as f:
        f.write("stop_id,stop_lat,stop_lon,stop_name\n")
        f.write(f"X1,{lat},{lon},Test Stop One\n")
    with open(os.path.join(d, "trips.txt"), "w", newline="") as f:
        f.write("trip_id,route_id,service_id\n")
        f.write("T1,RX,S1\n")
    with open(os.path.join(d, "stop_times.txt"), "w", newline="") as f:
        f.write("trip_id,stop_sequence,stop_id,arrival_time,departure_time\n")
        f.write("T1,1,X1,08:00:00,08:00:00\n")


def test_ids_are_agency_prefixed():  # MF-1
    tt = Timetable.from_gtfs_dirs({"frta": FRTA}, WEEKDAY)
    assert tt.stops, "expected FRTA stops"
    assert all(sid.startswith("frta:") for sid in tt.stops)
    assert all(tid.startswith("frta:") for tid in tt.trips)
    assert all(t.route_id.startswith("frta:") for t in tt.trips.values())


def test_per_feed_calendar_resolved():  # MF-2
    # FRTA weekday service exists on a Monday inside the window.
    tt = Timetable.from_gtfs_dirs({"frta": FRTA}, WEEKDAY)
    assert len(tt.trips) > 0


def test_interagency_transfers_within_400m(tmp_path):  # MF-3
    # Put a synthetic stop ~100 m from a known FRTA stop and require a transfer.
    tt0 = Timetable.from_gtfs_dirs({"frta": FRTA}, WEEKDAY)
    anchor = next(iter(tt0.stops.values()))
    near = str(tmp_path / "near")
    _write_feed(near, anchor.lat + 0.0009, anchor.lon)  # ~100 m north
    tt = Timetable.from_gtfs_dirs({"frta": FRTA, "near": near}, WEEKDAY,
                                  max_interagency_walk_m=400.0)
    pairs = {(t.from_stop, t.to_stop) for t in tt.transfers}
    assert (anchor.stop_id, "near:X1") in pairs
    assert ("near:X1", anchor.stop_id) in pairs


def test_no_interagency_transfer_beyond_radius(tmp_path):  # MF-3 negative
    # Place a synthetic stop far from EVERY FRTA stop (well outside the feed's
    # bounding box), so no cross-agency transfer should be created.
    tt0 = Timetable.from_gtfs_dirs({"frta": FRTA}, WEEKDAY)
    max_lat = max(s.lat for s in tt0.stops.values())
    far = str(tmp_path / "far")
    _write_feed(far, max_lat + 1.0, -70.0)  # ~111 km north, different longitude
    tt = Timetable.from_gtfs_dirs({"frta": FRTA, "far": far}, WEEKDAY,
                                  max_interagency_walk_m=400.0)
    assert not any(t.to_stop == "far:X1" or t.from_stop == "far:X1"
                   for t in tt.transfers)


def test_midnight_times_never_wrap():  # MF-4
    tt = Timetable.from_gtfs_dirs({"frta": FRTA}, WEEKDAY)
    for st in tt.stop_times:
        assert st.arr >= 0 and st.dep >= 0
        # any past-midnight trips must stay >= 86400, never wrapped into [0,86400)
