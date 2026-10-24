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
    """Earliest arrival per stop via a single connection scan, exact under the
    transfer cap.

    Labels are kept per **vehicle-leg level**: `arr[h][stop]` is the earliest arrival
    at `stop` using at most `h` buses (h = 0 .. max_transfers + 1). A connection
    boarded from level h writes level h + 1. One label per stop is NOT enough once
    transfers are capped: the earliest-arriving label may already have used every
    allowed bus, while a later-but-shorter label could still board onward — keeping
    only the earliest one silently loses that stop's downstream (spec
    bug-csa-transfer-cap, found by RAPTOR != CSA on the real PVTA feed).

    Uses trip reachability per (trip, level): once any stop of a trip is boardable at
    level h, the whole downstream of that trip is reachable at level h + 1. Foot
    transfers are relaxed out of a stop the moment its arrival improves, at the same
    level (walks are not vehicle legs), so a transfer that unlocks a later connection
    is seen within the one scan (connections are in departure order).
    """
    levels = limits.max_transfers + 1  # max vehicle legs
    arr: list[dict[str, int]] = [{} for _ in range(levels + 1)]
    legs_to: list[dict[str, list[Leg]]] = [{} for _ in range(levels + 1)]

    def improve(h: int, stop: str, t: int, legs: list[Leg]) -> bool:
        """Set level h's label and propagate it to every higher level (<= h semantics)."""
        if stop in arr[h] and t >= arr[h][stop]:
            return False
        for lvl in range(h, levels + 1):
            if stop not in arr[lvl] or t < arr[lvl][stop]:
                arr[lvl][stop] = t
                legs_to[lvl][stop] = legs
        return True

    def relax_transfers(h: int, stop: str) -> None:
        # transitive foot-transfer closure out of `stop`, staying on level h
        stack = [stop]
        while stack:
            s = stack.pop()
            for tr in tt.transfers_from.get(s, ()):
                cand = arr[h][s] + tr.min_transfer_time
                legs = legs_to[h][s] + [
                    Leg(kind="walk", from_stop=s, to_stop=tr.to_stop, route_id=None, dep=arr[h][s], arr=cand)
                ]
                if improve(h, tr.to_stop, cand, legs):
                    stack.append(tr.to_stop)

    for s, t in from_stops.items():
        t0 = max(t, depart_after) if depart_after is not None else t
        if improve(0, s, t0, []):
            relax_transfers(0, s)

    # reachable[(trip, level boarded from)] = (board_stop, board_dep, legs_at_board)
    reachable_trip: dict[tuple[str, int], tuple[str, int, list[Leg]]] = {}

    for c in _connections(tt):
        for h in range(levels):  # board from level h, arrive at level h + 1
            key = (c.trip_id, h)
            board = reachable_trip.get(key)
            if board is None:
                here = arr[h].get(c.dep_stop)
                if here is None:
                    continue
                last = legs_to[h][c.dep_stop]
                ready = here + (tt.min_transfer_time(c.dep_stop, c.dep_stop) if (last and last[-1].kind == "bus") else 0)
                if c.dep < ready:
                    continue
                board = (c.dep_stop, c.dep, last)
                reachable_trip[key] = board
            board_stop, board_dep, board_legs = board
            if c.arr - board_dep > limits.max_leg_seconds:
                continue
            legs = board_legs + [
                Leg(kind="bus", from_stop=board_stop, to_stop=c.arr_stop, route_id=c.route_id, dep=board_dep, arr=c.arr)
            ]
            if improve(h + 1, c.arr_stop, c.arr, legs):
                relax_transfers(h + 1, c.arr_stop)

    best = arr[levels]
    return {s: (best[s], legs_to[levels].get(s, [])) for s in best}


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
