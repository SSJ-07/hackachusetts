"""Property-based tests (Hypothesis) for RETURN trips after 24:00 — the classic
midnight / service-day bug (RT-6, steering/gtfs-domain.md).

A GTFS stop_time may read ``24:30:00`` to mean a bus that runs past midnight on
the *same* service day; it must be kept as ``88200`` seconds, never wrapped to
``01800`` (00:30). These properties pin that down for the one direction most
likely to break it: the return home, whose only buses depart in the
``24:00:00``..``26:59:59`` window.

Properties (all over Hypothesis-chosen late-night feeds):
  (a) an appointment ending late is reachable when a 24:xx return exists, and
      ``last_bus_home`` is the > 86400 value, never a wrapped one;
  (b) every leg is monotone — no leg departs before the previous leg arrives,
      and no time silently wraps down into the 00:xx range;
  (c) RAPTOR == CSA == brute force on these late-night feeds;
  (d) the reason string prints hours >= 24 (``24:30:00``), not ``00:30:00``;
  (e) a return whose only bus exceeds the 2h ``max_leg_seconds`` window is NOT
      reported reachable;
  (f) the ``earliest_home_dep`` (>= 05:30) rule does not wrongly reject a 24:xx
      departure — 88200 > 19800, so it must pass (no comparison against a
      wrapped value).

If the engine ever wraps a >= 86400 time, at least one of these fails and
Hypothesis shrinks to the smallest offending departure. No bug is invented: if
nothing fails after a strong search these stand as a regression guard.
"""

from __future__ import annotations

from hypothesis import example, given, settings
from hypothesis import strategies as st

from engine import round_trip
from engine.brute_force import round_trip as bf_rt
from engine.csa import round_trip as csa_rt
from engine.gtfs import Stop, StopTime, Timetable, Trip, fmt_gtfs_time, parse_gtfs_time
from engine.types import DEFAULT_LIMITS, Limits

DATE = "2026-11-12"

# A fixed, generous search budget — midnight bugs hide in specific second values.
MIDNIGHT_SETTINGS = settings(max_examples=600, deadline=None)

# Appointment fixed late in the evening so the *only* way home is a 24:xx bus.
APPT_START = 22 * 3600 + 30 * 60  # 22:30 -> 81000
APPT_MINUTES = 60  # visit ends 23:30 -> 84600
VISIT_END = APPT_START + APPT_MINUTES * 60  # 84600

# Outbound bus (ordinary, same-day) so the trip can only fail on the RETURN.
_OUT_DEP = 79200  # 22:00
_OUT_ARR = 80400  # 22:20 (<= APPT_START - checkin_buffer = 80400)

# Late-night departures live strictly past midnight: 24:00:00..26:59:59.
_SECONDS_IN_DAY = 86400
_late_return_dep = st.integers(min_value=_SECONDS_IN_DAY, max_value=_SECONDS_IN_DAY + 3 * 3600 - 1)
# Return ride duration kept well inside the 2h leg limit for the "reachable" feeds.
_ret_ride = st.integers(min_value=300, max_value=1800)


def _late_feed(ret_dep: int, ret_ride: int) -> Timetable:
    """origin S0, clinic S1. One ordinary outbound; one late-night return that
    departs the clinic at ``ret_dep`` (>= 86400) and rides ``ret_ride`` seconds."""
    stops = {
        "S0": Stop("S0", 42.00, -72.6, "home"),
        "S1": Stop("S1", 42.02, -72.6, "clinic"),
    }
    trips = {
        "OUT": Trip("OUT", "R1", "WKDY"),
        "RET": Trip("RET", "R1", "WKDY"),
    }
    stop_times = [
        StopTime("OUT", 0, "S0", _OUT_DEP, _OUT_DEP),
        StopTime("OUT", 1, "S1", _OUT_ARR, _OUT_ARR),
        StopTime("RET", 0, "S1", ret_dep, ret_dep),
        StopTime("RET", 1, "S0", ret_dep + ret_ride, ret_dep + ret_ride),
    ]
    return Timetable(
        stops=stops, trips=trips, stop_times=stop_times, transfers=[], service_date=DATE
    ).index()


def _legs_monotone(legs) -> bool:
    """No leg departs before the previous leg arrives (causality), and no time
    wraps: a wrap would make a later leg's dep smaller than an earlier arr."""
    prev_arr = None
    for leg in legs:
        if leg.arr < leg.dep:
            return False
        if prev_arr is not None and leg.dep < prev_arr:
            return False
        prev_arr = leg.arr
    return True


@given(ret_dep=_late_return_dep, ret_ride=_ret_ride)
@settings(max_examples=600, deadline=None)
@example(ret_dep=parse_gtfs_time("24:30:00"), ret_ride=1200)  # the canonical 88200 case
def test_late_return_reachable_and_last_bus_not_wrapped(ret_dep: int, ret_ride: int) -> None:
    """(a) reachable, and ``last_bus_home`` is the > 86400 value, never wrapped."""
    tt = _late_feed(ret_dep, ret_ride)
    r = round_trip(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    assert r.reachable, f"late-night return at {fmt_gtfs_time(ret_dep)} should be reachable"
    assert r.last_bus_home == ret_dep, (
        f"last_bus_home wrapped: got {r.last_bus_home} "
        f"({fmt_gtfs_time(r.last_bus_home) if r.last_bus_home is not None else None}), "
        f"expected {ret_dep} ({fmt_gtfs_time(ret_dep)})"
    )
    assert r.last_bus_home >= _SECONDS_IN_DAY, "last_bus_home dropped below 86400 (wrapped)"


@given(ret_dep=_late_return_dep, ret_ride=_ret_ride)
@settings(max_examples=600, deadline=None)
@example(ret_dep=parse_gtfs_time("25:00:00"), ret_ride=600)
def test_leg_times_monotone_and_never_wrap(ret_dep: int, ret_ride: int) -> None:
    """(b) all leg times monotone; none wraps to a 00:xx value."""
    tt = _late_feed(ret_dep, ret_ride)
    r = round_trip(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    assert r.reachable
    assert _legs_monotone(r.out_legs), f"outbound not monotone: {r.out_legs}"
    assert _legs_monotone(r.ret_legs), f"return not monotone: {r.ret_legs}"
    # the return's bus leg carries the true >= 86400 time end to end
    ret_bus = next((leg for leg in r.ret_legs if leg.kind == "bus"), None)
    assert ret_bus is not None
    assert ret_bus.dep == ret_dep and ret_bus.arr == ret_dep + ret_ride, (
        f"return bus time wrapped: {ret_bus.dep}->{ret_bus.arr}, "
        f"expected {ret_dep}->{ret_dep + ret_ride}"
    )


@given(ret_dep=_late_return_dep, ret_ride=_ret_ride)
@settings(max_examples=600, deadline=None)
@example(ret_dep=parse_gtfs_time("26:59:59"), ret_ride=900)
def test_three_routers_agree_on_late_feeds(ret_dep: int, ret_ride: int) -> None:
    """(c) RAPTOR == CSA == brute force on late-night feeds (reachability +
    last_bus_home)."""
    tt = _late_feed(ret_dep, ret_ride)
    r = round_trip(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    c = csa_rt(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    b = bf_rt(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    assert r.reachable == b.reachable == c.reachable, (
        f"routers disagree on reachability at {fmt_gtfs_time(ret_dep)}: "
        f"RAPTOR={r.reachable} CSA={c.reachable} BF={b.reachable}"
    )
    assert r.last_bus_home == b.last_bus_home == c.last_bus_home, (
        f"routers disagree on last_bus_home at {fmt_gtfs_time(ret_dep)}: "
        f"RAPTOR={r.last_bus_home} CSA={c.last_bus_home} BF={b.last_bus_home}"
    )


@given(ret_dep=_late_return_dep, ret_ride=_ret_ride)
@settings(max_examples=600, deadline=None)
@example(ret_dep=parse_gtfs_time("24:30:00"), ret_ride=1200)
def test_reason_prints_hours_past_24(ret_dep: int, ret_ride: int) -> None:
    """(d) the reason string prints hours >= 24 (e.g. '24:30:00'), not '00:30:00'."""
    tt = _late_feed(ret_dep, ret_ride)
    r = round_trip(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    assert r.reachable
    expected = fmt_gtfs_time(ret_dep)  # e.g. "24:30:00"
    hh = ret_dep // 3600
    assert hh >= 24
    assert expected in r.reason, f"reason {r.reason!r} does not contain {expected!r}"
    # the wrapped form must NOT appear
    wrapped = fmt_gtfs_time(ret_dep - _SECONDS_IN_DAY)
    assert wrapped not in r.reason, (
        f"reason {r.reason!r} contains the WRAPPED time {wrapped!r} for a 24:xx bus"
    )


@given(
    ret_dep=_late_return_dep,
    over=st.integers(min_value=1, max_value=4 * 3600),
)
@settings(max_examples=600, deadline=None)
@example(ret_dep=parse_gtfs_time("24:30:00"), over=1)  # one second past the 2h window
def test_return_beyond_max_leg_window_not_reachable(ret_dep: int, over: int) -> None:
    """(e) a return whose only bus exceeds the 2h max_leg_seconds window is NOT
    reachable — and all three routers agree on that."""
    ride = DEFAULT_LIMITS.max_leg_seconds + over  # strictly over 2h
    tt = _late_feed(ret_dep, ride)
    r = round_trip(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    c = csa_rt(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    b = bf_rt(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    assert not r.reachable, "return exceeding the 2h leg window was wrongly reachable"
    assert r.reachable == c.reachable == b.reachable == False


@given(ret_dep=_late_return_dep, ret_ride=_ret_ride)
@settings(max_examples=600, deadline=None)
@example(ret_dep=parse_gtfs_time("24:30:00"), ret_ride=1200)
def test_earliest_home_dep_does_not_reject_late_departure(ret_dep: int, ret_ride: int) -> None:
    """(f) the earliest_home_dep (>= 05:30 = 19800) rule must not reject a 24:xx
    departure. 88200 > 19800, so the trip stays reachable; a wrapped comparison
    (e.g. 01800 < 19800) would wrongly reject it."""
    assert ret_dep > DEFAULT_LIMITS.earliest_home_dep  # by construction
    tt = _late_feed(ret_dep, ret_ride)
    r = round_trip(tt, "S0", "S1", DATE, APPT_START, APPT_MINUTES)
    assert r.reachable, (
        f"earliest_home_dep wrongly rejected a {fmt_gtfs_time(ret_dep)} departure "
        f"(likely compared a wrapped {fmt_gtfs_time(ret_dep - _SECONDS_IN_DAY)} < "
        f"{fmt_gtfs_time(DEFAULT_LIMITS.earliest_home_dep)})"
    )
    assert r.last_bus_home == ret_dep


def test_parse_keeps_past_midnight_literal() -> None:
    """Anchor: the parser keeps 24:30:00 as 88200 and fmt round-trips it."""
    assert parse_gtfs_time("24:30:00") == 88200
    assert parse_gtfs_time("26:59:59") == 26 * 3600 + 59 * 60 + 59
    assert fmt_gtfs_time(88200) == "24:30:00"
    assert fmt_gtfs_time(88200) != "00:30:00"
