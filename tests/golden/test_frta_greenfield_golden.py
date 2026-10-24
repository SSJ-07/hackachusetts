"""Golden test (spec multi-feed MF-G1): a hand-checked FRTA trip.

Pinned against data/manual/frta_minigtfs/stop_times.txt (the real published feed,
Trillium / Mobility Database mdb-429). If FRTA republishes and this trip changes,
update the expected values from the new feed and note it here.
"""
from __future__ import annotations

from engine.gtfs import Timetable, fmt_gtfs_time

FRTA = "data/manual/frta_minigtfs"
WEEKDAY = "2026-10-26"

# Route 32 (Orange) trip, verified against stop_times.txt on the 2026-08-13 feed.
TRIP = "frta:t_6151913_b_86595_tn_0"
EXPECTED_FIRST_STOPS = [
    ("frta:2505652", "Orange Center", "17:40:00"),
    ("frta:2505739", "E River St at Orange Food Pantry", "17:40:54"),
    ("frta:2505620", "WalMart Plaza Orange", "17:45:00"),
    ("frta:4254435", "Community Health Center", "17:53:42"),
]


def test_frta_route32_golden_first_stops():
    tt = Timetable.from_gtfs_dirs({"frta": FRTA}, WEEKDAY)
    assert TRIP in tt.trip_stop_times, "golden trip missing — feed may have changed"
    assert tt.trips[TRIP].route_id == "frta:32"
    got = tt.trip_stop_times[TRIP][:4]
    for st, (sid, name, dep) in zip(got, EXPECTED_FIRST_STOPS):
        assert st.stop_id == sid
        assert tt.stops[st.stop_id].name == name
        assert fmt_gtfs_time(st.dep) == dep
