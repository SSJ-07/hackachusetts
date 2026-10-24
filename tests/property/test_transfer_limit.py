"""Regression guard for bug-transfer-limit (.kiro/specs/bug-transfer-limit/).

The pre-fix RAPTOR read and wrote the same `best` labels inside a round, so one
round could chain several buses and a journey could exceed max_transfers. Found
on the real PVTA feed (Holyoke 4107 -> Baystate 1053: 4 outbound / 6 return
buses, limit 3). Run against the pre-fix code, this property fails and Hypothesis
shrinks it to the minimal case: a chain of n=4 single-hop routes (S0 -> S4 with
4 buses). The pinned @example keeps that exact counterexample in CI forever.
"""

from __future__ import annotations

from hypothesis import example, given, settings
from hypothesis import strategies as st

from engine import earliest_arrival, round_trip
from engine.brute_force import earliest_arrival as bf_earliest_arrival
from engine.csa import earliest_arrival as csa_earliest_arrival
from engine.gtfs import Stop, StopTime, Timetable, Trip
from engine.types import DEFAULT_LIMITS

DATE = "2026-11-12"
MAX_BUSES = DEFAULT_LIMITS.max_transfers + 1


def _bus_legs(legs) -> int:
    return sum(1 for leg in legs if leg.kind == "bus")


def chain_feed(n: int) -> Timetable:
    """n hops S0->S1->...->Sn, each its own route, each departing after the
    previous one arrives — reaching Sn needs exactly n buses."""
    stops = {f"S{i}": Stop(f"S{i}", 42.0 + i * 0.02, -72.6) for i in range(n + 1)}
    trips: dict[str, Trip] = {}
    sts: list[StopTime] = []
    for i in range(n):
        tid = f"T{i}"
        trips[tid] = Trip(tid, f"R{i}", "WKDY")
        dep = 7 * 3600 + i * 900
        sts += [StopTime(tid, 0, f"S{i}", dep, dep), StopTime(tid, 1, f"S{i + 1}", dep + 600, dep + 600)]
    return Timetable(stops=stops, trips=trips, stop_times=sts, service_date=DATE).index()


@settings(max_examples=200, deadline=None)
@given(n=st.integers(min_value=1, max_value=12))
@example(n=4)  # the shrunk counterexample from the bug
def test_no_journey_exceeds_transfer_limit(n: int) -> None:
    tt = chain_feed(n)
    ea = earliest_arrival(tt, {"S0": 0}, DATE)
    for stop, (_arr, legs) in ea.items():
        assert _bus_legs(legs) <= MAX_BUSES, f"n={n}: {stop} reached with {_bus_legs(legs)} buses"
    # a stop that needs more than MAX_BUSES buses must be unreachable, not reached illegally
    if n > MAX_BUSES:
        assert f"S{n}" not in ea


@settings(max_examples=100, deadline=None)
@given(n=st.integers(min_value=1, max_value=8))
@example(n=4)
def test_transfer_limit_agrees_with_oracles(n: int) -> None:
    """RAPTOR, CSA and brute force agree on which chain stops are reachable."""
    tt = chain_feed(n)
    rap = set(earliest_arrival(tt, {"S0": 0}, DATE))
    csa = set(csa_earliest_arrival(tt, {"S0": 0}, DATE))
    bf = set(bf_earliest_arrival(tt, {"S0": 0}, DATE))
    assert rap == csa == bf


def test_round_trip_respects_limit_on_chain() -> None:
    """The original symptom, end to end: a 4-bus-only trip is NOT reachable."""
    tt = chain_feed(4)
    r = round_trip(tt, "S0", "S4", DATE, 12 * 3600, 30)
    assert _bus_legs(r.out_legs) <= MAX_BUSES
    assert not r.reachable
