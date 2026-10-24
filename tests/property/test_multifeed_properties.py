"""Property tests for the multi-feed loader (spec multi-feed MF-P1..MF-P3).

MF-P2 (agency prefix integrity) runs on the FRTA feed alone.
MF-P1 (never worse) and MF-P3 (no-service identity) need the PVTA cache; they
skip when data/cache/pvta is absent so local runs without the big feed still pass,
while CI with the cache present exercises them.
"""
from __future__ import annotations

import os

import pytest

from engine.gtfs import Timetable

FRTA = "data/manual/frta_minigtfs"
PVTA = "data/cache/pvta"
WEEKDAY = "2026-10-26"
KNOWN_PREFIXES = ("pvta:", "frta:", "near:", "far:")


def test_mf_p2_every_id_has_one_agency_prefix():
    tt = Timetable.from_gtfs_dirs({"frta": FRTA}, WEEKDAY)
    for sid in tt.stops:
        assert sid.startswith("frta:") and sid.count(":") >= 1
    for tid, t in tt.trips.items():
        assert tid.startswith("frta:")
        assert t.route_id.startswith("frta:")
    for st in tt.stop_times:
        assert st.stop_id.startswith("frta:")
        assert st.trip_id.startswith("frta:")


@pytest.mark.skipif(not os.path.isdir(PVTA), reason="PVTA cache not present")
def test_mf_p3_no_service_identity_to_pvta_only():
    # A date outside FRTA's service window -> merged == PVTA-only.
    out_of_window = "2026-01-05"
    only = Timetable.from_gtfs_dir(PVTA, out_of_window)
    merged = Timetable.from_gtfs_dirs({"pvta": PVTA, "frta": FRTA}, out_of_window)
    # strip the pvta: prefix the merged loader adds, then compare trip id sets
    merged_trips = {t[len("pvta:"):] for t in merged.trips if t.startswith("pvta:")}
    assert merged_trips == set(only.trips)
    assert not any(t.startswith("frta:") for t in merged.trips)


@pytest.mark.skipif(not os.path.isdir(PVTA), reason="PVTA cache not present")
def test_mf_p1_merged_has_all_pvta_trips():
    only = Timetable.from_gtfs_dir(PVTA, WEEKDAY)
    merged = Timetable.from_gtfs_dirs({"pvta": PVTA, "frta": FRTA}, WEEKDAY)
    merged_pvta = {t[len("pvta:"):] for t in merged.trips if t.startswith("pvta:")}
    # adding FRTA never drops a PVTA trip
    assert set(only.trips).issubset(merged_pvta)
