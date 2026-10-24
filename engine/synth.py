"""Synthetic GTFS builder + access resolution.

`build_grid_feed` and `random_feed` make tiny, fully-controlled timetables for
property and differential tests, where RAPTOR, CSA and brute force must agree.

`access_links` turns an OriginRef/ClinicRef into (stop_id, walk_seconds) pairs
within the walk limit — the entry/exit points every router starts and ends at.
"""

from __future__ import annotations

import random

from engine.gtfs import Stop, StopTime, Timetable, Transfer, Trip, haversine_m
from engine.types import DEFAULT_LIMITS, ClinicRef, Limits, OriginRef


def access_links(
    tt: Timetable,
    ref: OriginRef | ClinicRef,
    limits: Limits = DEFAULT_LIMITS,
) -> list[tuple[str, int]]:
    """Return [(stop_id, walk_seconds)] for every stop within the walk limit of ref.

    ref may be a stop_id (exact, 0 walk), or a (lat, lon). A bare string that is
    not a known stop_id is treated as an unresolved id with no links.
    """
    if isinstance(ref, str):
        if ref in tt.stops:
            return [(ref, 0)]
        return []
    lat, lon = ref
    out: list[tuple[str, int]] = []
    for s in tt.stops.values():
        d = haversine_m(lat, lon, s.lat, s.lon)
        if d <= limits.max_walk_m:
            walk_sec = int(round(d / limits.walk_m_per_min * 60.0))
            out.append((s.stop_id, walk_sec))
    out.sort(key=lambda x: x[1])
    return out


def build_grid_feed(
    *,
    n_stops: int = 4,
    departures: list[int] | None = None,
    headway: int = 1800,
    travel: int = 600,
    service_id: str = "WKDY",
    date: str = "2026-11-12",
    route_id: str = "R1",
    bidirectional: bool = True,
) -> Timetable:
    """A single line of `n_stops` stops in a row, trips in both directions.

    Each outbound trip visits stop 0..n_stops-1; each inbound trip visits
    n_stops-1..0. `travel` seconds between adjacent stops. Stops are ~1 km apart
    on a line so haversine access is predictable. With `bidirectional=True`
    (default) a patient can both reach a clinic and return home.
    """
    if departures is None:
        # all-day half-hourly service 06:00..20:00
        departures = [6 * 3600 + i * headway for i in range((14 * 3600) // headway + 1)]
    stops = {
        f"S{i}": Stop(stop_id=f"S{i}", lat=42.0 + i * 0.009, lon=-72.6, name=f"Stop {i}")
        for i in range(n_stops)
    }
    trips: dict[str, Trip] = {}
    stop_times: list[StopTime] = []
    for ti, dep0 in enumerate(departures):
        # outbound S0 -> S{n-1}
        out_id = f"T{ti}o"
        trips[out_id] = Trip(trip_id=out_id, route_id=route_id, service_id=service_id)
        for seq in range(n_stops):
            t = dep0 + seq * travel
            stop_times.append(StopTime(trip_id=out_id, seq=seq, stop_id=f"S{seq}", arr=t, dep=t))
        if bidirectional:
            # inbound S{n-1} -> S0, same departure clock
            in_id = f"T{ti}i"
            trips[in_id] = Trip(trip_id=in_id, route_id=route_id, service_id=service_id)
            for seq in range(n_stops):
                t = dep0 + seq * travel
                stop_times.append(
                    StopTime(trip_id=in_id, seq=seq, stop_id=f"S{n_stops - 1 - seq}", arr=t, dep=t)
                )
    tt = Timetable(
        stops=stops,
        trips=trips,
        stop_times=stop_times,
        transfers=[],
        service_date=date,
    )
    return tt.index()


def random_feed(seed: int, date: str = "2026-11-12") -> Timetable:
    """A small random multi-route feed for differential testing.

    Deterministic in `seed`. 3-6 stops, 2-3 routes, trips with random departures,
    occasional >24:00 departures to exercise midnight safety, and random
    transfer edges. All three routers must agree on any query over this feed.
    """
    rng = random.Random(seed)
    n = rng.randint(3, 6)
    stops = {
        f"S{i}": Stop(stop_id=f"S{i}", lat=42.0 + i * 0.01, lon=-72.6 + rng.uniform(-0.01, 0.01), name=f"S{i}")
        for i in range(n)
    }
    trips: dict[str, Trip] = {}
    stop_times: list[StopTime] = []
    n_routes = rng.randint(2, 3)
    tid = 0
    for r in range(n_routes):
        route_id = f"R{r}"
        order = list(range(n))
        rng.shuffle(order)
        order = order[: rng.randint(2, n)]
        for _ in range(rng.randint(2, 4)):
            trip_id = f"T{tid}"
            tid += 1
            trips[trip_id] = Trip(trip_id=trip_id, route_id=route_id, service_id="WKDY")
            # sometimes start late enough to cross midnight (>86400)
            base = rng.choice([6 * 3600, 22 * 3600, 23 * 3600 + 1800])
            t = base + rng.randint(0, 3600)
            for seq, _stop_idx in enumerate(order):
                t += rng.randint(300, 1200)
                stop_times.append(
                    StopTime(trip_id=trip_id, seq=seq, stop_id=f"S{order[seq]}", arr=t, dep=t + rng.randint(0, 60))
                )
    transfers: list[Transfer] = []
    for _ in range(rng.randint(0, n)):
        a, b = rng.sample(list(stops), 2)
        transfers.append(Transfer(a, b, rng.choice([60, 120, 300])))
    tt = Timetable(stops=stops, trips=trips, stop_times=stop_times, transfers=transfers, service_date=date)
    return tt.index()
