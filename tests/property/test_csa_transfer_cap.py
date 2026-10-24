"""Regression guard for bug-csa-transfer-cap (.kiro/specs/bug-csa-transfer-cap/).

The pre-fix CSA kept ONE label per stop (earliest arrival + the bus count of that
label). Under a transfer cap that is not enough: the earliest-arriving label at a
stop may already have spent every allowed bus, while a later-but-shorter label could
still board onward. Keeping only the earliest label silently lost that stop's
downstream. RAPTOR (round-based, exact) found the stops; CSA did not — 21 stops from
2 of 3 random origins on the real PVTA feed (tests/differential/test_real_feed_agree.py).

This is the minimal hand-built feed that shows it: X is reached first by 3 buses
(the cap), later by 1 bus; the onward bus X -> Y leaves after the 1-bus arrival.
Pre-fix CSA: Y unreachable. RAPTOR, brute force and fixed CSA: Y at 08:50 with 2 buses.
"""

from __future__ import annotations

from engine import earliest_arrival as raptor_ea
from engine.brute_force import earliest_arrival as bf_ea
from engine.csa import earliest_arrival as csa_ea
from engine.gtfs import Stop, StopTime, Timetable, Trip
from engine.types import DEFAULT_LIMITS

DATE = "2026-11-12"
H = 3600


def _bus_legs(legs) -> int:
    return sum(1 for leg in legs if leg.kind == "bus")


def cap_trap_feed() -> Timetable:
    stops = {s: Stop(s, 42.0 + i * 0.02, -72.6) for i, s in enumerate("OABXY")}
    hops = [  # trip, from, to, dep, arr
        ("T1", "O", "A", 7 * H, 7 * H + 600),
        ("T2", "A", "B", 7 * H + 1200, 7 * H + 1800),
        ("T3", "B", "X", 7 * H + 2400, 7 * H + 3000),       # X at 07:50 with 3 buses (the cap)
        ("T4", "O", "X", 8 * H, 8 * H + 1800),             # X at 08:30 with 1 bus
        ("T5", "X", "Y", 8 * H + 2400, 8 * H + 3000),       # Y at 08:50 — only via the 1-bus label
    ]
    trips = {t: Trip(t, f"R{t}", "WKDY") for t, *_ in hops}
    sts = []
    for t, a, b, dep, arr in hops:
        sts += [StopTime(t, 0, a, dep, dep), StopTime(t, 1, b, arr, arr)]
    return Timetable(stops=stops, trips=trips, stop_times=sts, service_date=DATE).index()


def test_csa_reaches_y_through_the_later_shorter_label() -> None:
    assert DEFAULT_LIMITS.max_transfers == 2  # the trap is built for a 3-bus cap
    tt = cap_trap_feed()
    rap = raptor_ea(tt, {"O": 0}, DATE)
    csa = csa_ea(tt, {"O": 0}, DATE)
    bf = bf_ea(tt, {"O": 0}, DATE)
    assert "Y" in bf and bf["Y"][0] == 8 * H + 3000
    assert "Y" in rap and rap["Y"][0] == bf["Y"][0]
    assert "Y" in csa and csa["Y"][0] == bf["Y"][0], "CSA lost Y: single-label transfer-cap bug is back"
    assert _bus_legs(csa["Y"][1]) == 2
    # and every router still agrees on every stop
    for s in tt.stops:
        assert rap.get(s, (None,))[0] == csa.get(s, (None,))[0] == bf.get(s, (None,))[0], s


def test_csa_still_respects_the_cap() -> None:
    tt = cap_trap_feed()
    for s, (_arr, legs) in csa_ea(tt, {"O": 0}, DATE).items():
        assert _bus_legs(legs) <= DEFAULT_LIMITS.max_transfers + 1, s
