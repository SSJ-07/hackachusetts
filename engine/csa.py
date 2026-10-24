"""Connection Scan Algorithm (CSA) router — second independent implementation.

CSA sorts every elementary connection (one vehicle hop from stop A to stop B)
by departure time and scans them once, relaxing earliest-arrival labels. It is
a structurally different algorithm from RAPTOR, so RAPTOR == CSA on random
feeds is strong evidence both are correct (differential testing). Same public
signatures as engine.raptor.
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class Connection:
    trip_id: str
    route_id: str | None
    dep_stop: str
    arr_stop: str
    dep: int
    arr: int


def _connections(tt: Timetable) -> list[Connection]:
    conns: list[Connection] = []
    for trip_id, sts in tt.trip_stop_times.items():
        route_id = tt.trips[trip_id].route_id if trip_id in tt.trips else None
        for a, b in zip(sts, sts[1:]):
            conns.append(Connection(trip_id, route_id, a.stop_id, b.stop_id, a.dep, b.arr))
    conns.sort(key=lambda c: c.dep)
    return conns


def earliest_arrival(
    tt: Timetable,
    from_stops: dict[str, int],
    date: str,
    depart_after: int | None = None,
    limits: Limits = DEFAULT_LIMITS,
) -> dict[str, Label]:
    """Earliest arrival per stop via a single connection scan.

    Uses trip reachability: once any stop of a trip is boardable, the whole
    downstream of that trip is reachable. Foot transfers are relaxed out of a
    stop the moment that stop's arrival improves, so a transfer that unlocks a
    later connection is seen within the one scan (connections are in dep order).
    """
    arr: dict[str, int] = {}
    legs_to: dict[str, list[Leg]] = {}
    hops: dict[str, int] = {}  # vehicle legs used to reach the stop

    def improve(stop: str, t: int, legs: list[Leg], h: int) -> bool:
        if stop not in arr or t < arr[stop]:
            arr[stop] = t
            legs_to[stop] = legs
            hops[stop] = h
            return True
        return False

    def relax_transfers(stop: str) -> None:
        # transitive foot-transfer closure out of `stop`
        stack = [stop]
        while stack:
            s = stack.pop()
            for tr in tt.transfers_from.get(s, ()):
                cand = arr[s] + tr.min_transfer_time
                legs = legs_to[s] + [
                    Leg(kind="walk", from_stop=s, to_stop=tr.to_stop, route_id=None, dep=arr[s], arr=cand)
                ]
                if improve(tr.to_stop, cand, legs, hops[s]):
                    stack.append(tr.to_stop)

    for s, t in from_stops.items():
        t0 = max(t, depart_after) if depart_after is not None else t
        if improve(s, t0, [], 0):
            relax_transfers(s)

    # reachable[trip] = (board_stop, board_dep, legs_at_board, hops_at_board)
    reachable_trip: dict[str, tuple[str, int, list[Leg], int]] = {}

    for c in _connections(tt):
        board = None
        # (a) continue a trip we already boarded
        if c.trip_id in reachable_trip:
            board = reachable_trip[c.trip_id]
        # (b) or board it fresh at its dep stop if we are there in time
        here = arr.get(c.dep_stop)
        if here is not None and board is None:
            ready = here + (tt.min_transfer_time(c.dep_stop, c.dep_stop)
                            if (legs_to.get(c.dep_stop) and legs_to[c.dep_stop][-1].kind == "bus") else 0)
            if c.dep >= ready and hops[c.dep_stop] + 1 <= limits.max_transfers + 1:
                board = (c.dep_stop, c.dep, legs_to[c.dep_stop], hops[c.dep_stop])
                reachable_trip[c.trip_id] = board
        if board is None:
            continue
        board_stop, board_dep, board_legs, board_hops = board
        if c.arr - board_dep > limits.max_leg_seconds:
            continue
        if board_hops + 1 > limits.max_transfers + 1:
            continue
        legs = board_legs + [
            Leg(kind="bus", from_stop=board_stop, to_stop=c.arr_stop, route_id=c.route_id, dep=board_dep, arr=c.arr)
        ]
        if improve(c.arr_stop, c.arr, legs, board_hops + 1):
            relax_transfers(c.arr_stop)

    return {s: (arr[s], legs_to.get(s, [])) for s in arr}


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
    """Round trip via CSA. Same semantics as engine.raptor.round_trip."""
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
