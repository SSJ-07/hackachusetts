"""Property-based tests (Hypothesis) for the RAPTOR router.

Properties the router must preserve (steering/gtfs-domain.md, FINAL §8.3):
  - round-trip soundness: a reachable result's legs actually satisfy the
    arrive-by and depart-after constraints
  - the 10-minute check-in buffer is respected
  - midnight / service-day safety: times are never wrapped past 86400
  - causality: within any journey, each leg departs no earlier than the
    previous leg arrives
  - determinism: same inputs -> same result
  - monotone in access: adding a trip never makes a reachable slot unreachable
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from engine import round_trip
from engine.gtfs import StopTime, Timetable, Trip
from engine.synth import build_grid_feed, random_feed
from engine.types import DEFAULT_LIMITS

DATE = "2026-11-12"


def _legs_causal(legs) -> bool:
    for a, b in zip(legs, legs[1:]):
        if b.dep < a.arr:
            return False
    return True


def _no_wrapped_times(legs) -> bool:
    # all times are non-negative seconds; none silently wrapped to a small value
    return all(leg.dep >= 0 and leg.arr >= leg.dep for leg in legs)


@given(seed=st.integers(min_value=0, max_value=5000))
@settings(max_examples=200, deadline=None)
def test_determinism(seed: int) -> None:
    tt = random_feed(seed)
    stops = sorted(tt.stops)
    a = round_trip(tt, stops[0], stops[-1], DATE, 10 * 3600, 60)
    b = round_trip(tt, stops[0], stops[-1], DATE, 10 * 3600, 60)
    assert a == b


@given(seed=st.integers(min_value=0, max_value=5000),
       start=st.integers(min_value=6 * 3600, max_value=19 * 3600),
       minutes=st.integers(min_value=15, max_value=240))
@settings(max_examples=300, deadline=None)
def test_reachable_result_is_sound(seed: int, start: int, minutes: int) -> None:
    tt = random_feed(seed)
    stops = sorted(tt.stops)
    r = round_trip(tt, stops[0], stops[-1], DATE, start, minutes)
    if not r.reachable:
        return
    must_arrive_by = start - DEFAULT_LIMITS.checkin_buffer
    visit_end = start + minutes * 60
    # outbound arrives by the check-in deadline
    assert r.out_legs, "reachable but no outbound legs"
    assert r.out_legs[-1].arr <= must_arrive_by, "outbound arrives after check-in deadline"
    # return departs no earlier than the visit end
    assert r.ret_legs, "reachable but no return legs"
    first_bus = next((l for l in r.ret_legs if l.kind == "bus"), None)
    if first_bus is not None:
        assert first_bus.dep >= visit_end, "return bus departs before the visit ends"
    # causality + midnight safety on both directions
    assert _legs_causal(r.out_legs) and _legs_causal(r.ret_legs)
    assert _no_wrapped_times(r.out_legs) and _no_wrapped_times(r.ret_legs)


@given(start=st.integers(min_value=8 * 3600, max_value=12 * 3600),
       minutes=st.integers(min_value=15, max_value=90))
@settings(max_examples=100, deadline=None)
def test_checkin_buffer_respected(start: int, minutes: int) -> None:
    tt = build_grid_feed(n_stops=4)
    r = round_trip(tt, "S0", "S3", DATE, start, minutes)
    if r.reachable:
        assert r.out_legs[-1].arr <= start - DEFAULT_LIMITS.checkin_buffer


def test_midnight_times_never_wrap() -> None:
    """A trip departing after 24:00 keeps seconds > 86400 end to end."""
    tt = Timetable(
        stops={"A": __import__("engine.gtfs", fromlist=["Stop"]).Stop("A", 42.0, -72.6),
               "B": __import__("engine.gtfs", fromlist=["Stop"]).Stop("B", 42.01, -72.6)},
        trips={"T": Trip("T", "R", "WKDY")},
        stop_times=[StopTime("T", 0, "A", 88200, 88200), StopTime("T", 1, "B", 89400, 89400)],
        service_date=DATE,
    ).index()
    from engine import earliest_arrival
    ea = earliest_arrival(tt, {"A": 0}, DATE)
    assert ea["B"][0] == 89400  # not wrapped to 89400-86400=3000


@given(seed=st.integers(min_value=0, max_value=2000))
@settings(max_examples=100, deadline=None)
def test_monotone_in_access(seed: int) -> None:
    """Adding an extra trip can never make a reachable slot unreachable."""
    tt = random_feed(seed)
    stops = sorted(tt.stops)
    start, minutes = 10 * 3600, 60
    before = round_trip(tt, stops[0], stops[-1], DATE, start, minutes).reachable
    # add a direct early trip stop[0] -> stop[-1] that only helps
    extra_id = "EXTRA"
    tt.trips[extra_id] = Trip(extra_id, "RX", "WKDY")
    tt.stop_times.append(StopTime(extra_id, 0, stops[0], 7 * 3600, 7 * 3600))
    tt.stop_times.append(StopTime(extra_id, 1, stops[-1], 7 * 3600 + 600, 7 * 3600 + 600))
    tt.index()
    after = round_trip(tt, stops[0], stops[-1], DATE, start, minutes).reachable
    if before:
        assert after, "adding a trip made a reachable slot unreachable"
