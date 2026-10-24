"""Brute-force round-trip router — the ground-truth oracle (tiny feeds only).

Correctness by construction, not speed. We expand the feed into a connection
graph and run a label-setting search (Dijkstra-like over arrival time, bounded
by transfers). RAPTOR must agree with this on every random tiny feed; any
divergence is a RAPTOR bug. Same public signatures as engine.raptor so the
differential tests swap one for the other.
"""

from __future__ import annotations

import heapq

from engine.gtfs import Timetable, fmt_gtfs_time
from engine.synth import access_links
from engine.types import (
    DEFAULT_LIMITS,
    ClinicRef,
    Leg,
    Limits,
    OriginRef,
    RoundTripResult,
)

Label = tuple[int, list[Leg]]


def earliest_arrival(
    tt: Timetable,
    from_stops: dict[str, int],
    date: str,
    depart_after: int | None = None,
    limits: Limits = DEFAULT_LIMITS,
) -> dict[str, Label]:
    """Best (arrival, legs) per stop by exhaustive label-setting search.

    State = (arrival_time, stop, transfers_used, last_leg_was_bus). We pop the
    earliest arrival first; the first time we settle a stop is its optimum.
    """
    srcs = {s: (max(t, depart_after) if depart_after is not None else t) for s, t in from_stops.items()}
    # priority queue of (time, seq, stop, transfers, rode_bus_last, legs);
    # `seq` is a monotonic tiebreaker so the legs list is never compared.
    pq: list[tuple[int, int, str, int, bool, list[Leg]]] = []
    counter = 0
    for s, t in srcs.items():
        heapq.heappush(pq, (t, counter, s, 0, False, []))
        counter += 1
    best: dict[str, Label] = {}
    settled: set[str] = set()

    while pq:
        t, _seq, stop, transfers, rode_bus, legs = heapq.heappop(pq)
        if stop in settled:
            continue
        settled.add(stop)
        best[stop] = (t, legs)
        if transfers >= limits.max_transfers + 1:
            continue
        # ride every trip boardable at `stop` at/after t (+ transfer buffer if we just rode a bus)
        ready = t + (tt.min_transfer_time(stop, stop) if rode_bus else 0)
        for st in tt.stop_times_by_stop.get(stop, ()):
            if st.dep < ready:
                continue
            # ride this trip forward from st to every later stop on the trip
            seq_list = tt.trip_stop_times.get(st.trip_id, ())
            for nxt in seq_list:
                if nxt.seq <= st.seq:
                    continue
                if nxt.arr - st.dep > limits.max_leg_seconds:
                    break  # ordered by seq, so arrivals only grow
                if nxt.stop_id in settled:
                    continue
                nlegs = legs + [
                    Leg(kind="bus", from_stop=stop, to_stop=nxt.stop_id,
                        route_id=tt.trips[st.trip_id].route_id if st.trip_id in tt.trips else None,
                        dep=st.dep, arr=nxt.arr)
                ]
                heapq.heappush(pq, (nxt.arr, counter, nxt.stop_id, transfers + 1, True, nlegs))
                counter += 1
        # foot transfers
        for tr in tt.transfers_from.get(stop, ()):
            if tr.to_stop in settled:
                continue
            arr = t + tr.min_transfer_time
            nlegs = legs + [Leg(kind="walk", from_stop=stop, to_stop=tr.to_stop, route_id=None, dep=t, arr=arr)]
            heapq.heappush(pq, (arr, counter, tr.to_stop, transfers, rode_bus, nlegs))
            counter += 1
    return best


def _one_way(tt, origin_links, dest_links, depart_after, arrive_by, limits, o_label, d_label):
    if not origin_links or not dest_links:
        return None
    base = depart_after if depart_after is not None else min(
        (st.dep for sts in tt.trip_stop_times.values() for st in sts), default=0
    )
    from_stops: dict[str, int] = {}
    seed_legs: dict[str, list[Leg]] = {}
    for sid, walk in origin_links:
        ready = base + walk
        if sid not in from_stops or ready < from_stops[sid]:
            from_stops[sid] = ready
            seed_legs[sid] = [Leg(kind="walk", from_stop=o_label, to_stop=sid, route_id=None, dep=base, arr=ready)]
    best = earliest_arrival(tt, from_stops, "", None, limits)
    chosen = None
    for sid, walk in dest_links:
        lab = best.get(sid)
        if lab is None:
            continue
        arr = lab[0] + walk
        if arrive_by is not None and arr > arrive_by:
            continue
        legs = list(seed_legs.get(sid, [])) + list(lab[1])
        if walk > 0:
            legs = legs + [Leg(kind="walk", from_stop=sid, to_stop=d_label, route_id=None, dep=arr - walk, arr=arr)]
        if chosen is None or arr < chosen[0]:
            chosen = (arr, legs)
    return chosen


def round_trip(
    tt: Timetable,
    origin: OriginRef,
    clinic: ClinicRef,
    date: str,
    start: int,
    minutes: int,
    limits: Limits = DEFAULT_LIMITS,
) -> RoundTripResult:
    """Ground-truth round trip. Same semantics as engine.raptor.round_trip."""
    if tt.service_date and tt.service_date != date:
        return RoundTripResult(False, [], [], None, f"feed is for {tt.service_date}, not {date}")
    o = access_links(tt, origin, limits)
    c = access_links(tt, clinic, limits)
    if not o or not c:
        return RoundTripResult(False, [], [], None, "no walkable stop at origin or clinic")

    must_arrive_by = start - limits.checkin_buffer
    visit_end = start + minutes * 60

    out = _one_way(tt, o, c, None, must_arrive_by, limits, "origin", "clinic")
    ret = _one_way(tt, c, o, visit_end, None, limits, "clinic", "home")
    out_legs = out[1] if out else []
    ret_legs = ret[1] if ret else []

    last_bus_home = None
    if ret_legs:
        buses = [l for l in ret_legs if l.kind == "bus"]
        last_bus_home = buses[0].dep if buses else None
        if last_bus_home is not None and last_bus_home < limits.earliest_home_dep:
            ret_legs, last_bus_home = [], None

    reachable = bool(out_legs) and bool(ret_legs)
    reason = (
        f"arrive {fmt_gtfs_time(out[0])} ok; return after {fmt_gtfs_time(visit_end)}"
        if reachable else ("no outbound in time" if not out_legs else "no return after visit")
    )
    return RoundTripResult(reachable, out_legs, ret_legs, last_bus_home, reason)
