"""Differential test on the REAL PVTA feed: RAPTOR == CSA (connection-scan task 6).

The synthetic-feed differential suite proves the routers agree on random tiny networks;
this one checks they still agree on the real network, whose long multi-bus chains are
what exposed the transfer-limit bug (bug-transfer-limit spec). Skipped when the PVTA
cache is absent (CI has no data/cache); marked slow because the full feed is loaded.
"""

from __future__ import annotations

import os
import random

import pytest

from engine import round_trip as raptor_rt
from engine.csa import earliest_arrival as csa_ea
from engine.csa import round_trip as csa_rt
from engine.gtfs import Timetable
from engine.raptor import earliest_arrival as raptor_ea

PVTA_DIR = "data/cache/pvta"
DATE = "2026-11-12"
N_PAIRS = 40

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not os.path.exists(os.path.join(PVTA_DIR, "stops.txt")),
                       reason="PVTA GTFS not extracted to data/cache/pvta"),
]


@pytest.fixture(scope="module")
def pvta() -> Timetable:
    return Timetable.from_gtfs_dir(PVTA_DIR, DATE)


@pytest.fixture(scope="module")
def served_stops(pvta: Timetable) -> list[str]:
    # stops with at least one departure that day
    return sorted(s for s, sts in pvta.stop_times_by_stop.items() if sts)


def test_raptor_equals_csa_round_trips_on_real_feed(pvta, served_stops):
    rng = random.Random(2026)
    disagreements = []
    for _ in range(N_PAIRS):
        origin, clinic = rng.sample(served_stops, 2)
        start = rng.choice((8, 10, 14, 17)) * 3600
        minutes = rng.choice((30, 120))
        r = raptor_rt(pvta, origin, clinic, DATE, start, minutes)
        c = csa_rt(pvta, origin, clinic, DATE, start, minutes)
        if r.reachable != c.reachable:
            disagreements.append((origin, clinic, start, minutes, r.reachable, c.reachable))
    assert not disagreements, f"RAPTOR != CSA on real feed: {disagreements[:5]}"


def test_raptor_equals_csa_earliest_arrival_on_real_feed(pvta, served_stops):
    rng = random.Random(7)
    for origin in rng.sample(served_stops, 3):
        rp = raptor_ea(pvta, {origin: 8 * 3600}, DATE)
        cs = csa_ea(pvta, {origin: 8 * 3600}, DATE)
        mismatched = [s for s in set(rp) | set(cs)
                      if rp.get(s, (None,))[0] != cs.get(s, (None,))[0]]
        assert not mismatched, f"earliest arrival differs from {origin} at {len(mismatched)} stops: {mismatched[:5]}"
