"""In-memory GTFS timetable the routers walk.

Pure Python, no pandas, so a test can build a tiny feed by hand and a router
can be exercised in isolation. A loader for a real GTFS directory is provided
for the PVTA feed, but the routers only ever see the `Timetable` object.

Time parsing preserves GTFS times >= 24:00:00 as seconds past local midnight
(the classic midnight bug — see steering/gtfs-domain.md).
"""

from __future__ import annotations

import csv
import datetime as _dt
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field


def parse_gtfs_time(s: str) -> int:
    """'HH:MM:SS' -> seconds since local midnight. HH may be >= 24. Never wraps."""
    s = s.strip()
    if not s:
        raise ValueError("empty GTFS time")
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + int(sec)


def fmt_gtfs_time(secs: int) -> str:
    """Inverse of parse_gtfs_time, for human-readable reasons. Keeps hours >= 24."""
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class Stop:
    stop_id: str
    lat: float
    lon: float
    name: str = ""
    wheelchair_boarding: int = 0


@dataclass(frozen=True)
class StopTime:
    """One trip touching one stop. seq is the stop_sequence (ordering within the trip)."""

    trip_id: str
    seq: int
    stop_id: str
    arr: int  # seconds since local midnight (may be >= 86400)
    dep: int


@dataclass(frozen=True)
class Trip:
    trip_id: str
    route_id: str
    service_id: str
    wheelchair_accessible: int = 0


@dataclass(frozen=True)
class Transfer:
    from_stop: str
    to_stop: str
    min_transfer_time: int  # seconds


@dataclass
class Timetable:
    """The whole feed, resolved to one service date.

    Build it directly in tests, or via `from_gtfs_dir(path, date)` for PVTA.
    After construction, `stop_times_by_stop` and `trip_stop_times` are indexed
    for the routers; call `index()` if you mutate the raw lists by hand.
    """

    stops: dict[str, Stop] = field(default_factory=dict)
    trips: dict[str, Trip] = field(default_factory=dict)
    stop_times: list[StopTime] = field(default_factory=list)
    transfers: list[Transfer] = field(default_factory=list)
    service_date: str = ""  # ISO "YYYY-MM-DD"
    default_min_transfer: int = 60

    # indexes (filled by index())
    trip_stop_times: dict[str, list[StopTime]] = field(default_factory=dict)
    stop_times_by_stop: dict[str, list[StopTime]] = field(default_factory=dict)
    transfers_from: dict[str, list[Transfer]] = field(default_factory=dict)

    def index(self) -> "Timetable":
        """(Re)build the lookup indexes. Idempotent."""
        tst: dict[str, list[StopTime]] = defaultdict(list)
        sbs: dict[str, list[StopTime]] = defaultdict(list)
        for st in self.stop_times:
            tst[st.trip_id].append(st)
            sbs[st.stop_id].append(st)
        for trip_id in tst:
            tst[trip_id].sort(key=lambda s: s.seq)
        for stop_id in sbs:
            sbs[stop_id].sort(key=lambda s: s.dep)
        tf: dict[str, list[Transfer]] = defaultdict(list)
        for t in self.transfers:
            tf[t.from_stop].append(t)
        self.trip_stop_times = dict(tst)
        self.stop_times_by_stop = dict(sbs)
        self.transfers_from = dict(tf)
        return self

    def min_transfer_time(self, from_stop: str, to_stop: str) -> int:
        """Minimum seconds to transfer; the default when transfers.txt is silent."""
        for t in self.transfers_from.get(from_stop, ()):
            if t.to_stop == to_stop:
                return t.min_transfer_time
        return self.default_min_transfer

    # ---- real-feed loader (PVTA) -----------------------------------------

    @classmethod
    def from_gtfs_dir(cls, path: str, date: str, default_min_transfer: int = 60) -> "Timetable":
        """Load a GTFS directory, resolved to one ISO service date.

        Honours calendar.txt AND calendar_dates.txt (exception 1 add, 2 remove).
        """
        active = _active_services(path, date)
        trips: dict[str, Trip] = {}
        with open(os.path.join(path, "trips.txt"), newline="") as f:
            for row in csv.DictReader(f):
                if row["service_id"] not in active:
                    continue
                trips[row["trip_id"]] = Trip(
                    trip_id=row["trip_id"],
                    route_id=row["route_id"],
                    service_id=row["service_id"],
                    wheelchair_accessible=int(row.get("wheelchair_accessible") or 0),
                )
        stops: dict[str, Stop] = {}
        with open(os.path.join(path, "stops.txt"), newline="") as f:
            for row in csv.DictReader(f):
                stops[row["stop_id"]] = Stop(
                    stop_id=row["stop_id"],
                    lat=float(row["stop_lat"]),
                    lon=float(row["stop_lon"]),
                    name=row.get("stop_name", ""),
                    wheelchair_boarding=int(row.get("wheelchair_boarding") or 0),
                )
        stop_times: list[StopTime] = []
        with open(os.path.join(path, "stop_times.txt"), newline="") as f:
            for row in csv.DictReader(f):
                if row["trip_id"] not in trips:
                    continue
                stop_times.append(
                    StopTime(
                        trip_id=row["trip_id"],
                        seq=int(row["stop_sequence"]),
                        stop_id=row["stop_id"],
                        arr=parse_gtfs_time(row["arrival_time"]),
                        dep=parse_gtfs_time(row["departure_time"]),
                    )
                )
        transfers: list[Transfer] = []
        tpath = os.path.join(path, "transfers.txt")
        if os.path.exists(tpath):
            with open(tpath, newline="") as f:
                for row in csv.DictReader(f):
                    if row.get("transfer_type") == "2" and row.get("min_transfer_time"):
                        transfers.append(
                            Transfer(row["from_stop_id"], row["to_stop_id"], int(row["min_transfer_time"]))
                        )
        tt = cls(
            stops=stops,
            trips=trips,
            stop_times=stop_times,
            transfers=transfers,
            service_date=date,
            default_min_transfer=default_min_transfer,
        )
        return tt.index()

    # ---- multi-feed loader (PVTA + FRTA) ---------------------------------

    @classmethod
    def from_gtfs_dirs(
        cls,
        feeds: dict[str, str],
        date: str,
        default_min_transfer: int = 60,
        max_interagency_walk_m: float = 400.0,
        walk_m_per_min: float = 80.0,
    ) -> "Timetable":
        """Load several GTFS directories into ONE Timetable, resolved to `date`.

        `feeds` maps an agency key -> directory path, e.g.
            {"pvta": "data/cache/pvta", "frta": "data/manual/frta_minigtfs"}

        Every id (stop/trip/route/transfer endpoint) is prefixed by its agency key
        ("pvta:1053", "frta:JWO") so ids from different feeds never collide (MF-1).
        Each feed's own calendar/calendar_dates decide which trips are active (MF-2).
        Walking transfers are added between stops of DIFFERENT agencies within
        `max_interagency_walk_m` (MF-3). Times are never wrapped (MF-4).
        """
        merged = cls(service_date=date, default_min_transfer=default_min_transfer)
        per_agency_stops: dict[str, list[Stop]] = {}
        for agency, path in feeds.items():
            sub = cls.from_gtfs_dir(path, date, default_min_transfer=default_min_transfer)
            p = f"{agency}:"
            for sid, s in sub.stops.items():
                ns = Stop(stop_id=p + sid, lat=s.lat, lon=s.lon, name=s.name,
                          wheelchair_boarding=s.wheelchair_boarding)
                merged.stops[ns.stop_id] = ns
                per_agency_stops.setdefault(agency, []).append(ns)
            for tid, t in sub.trips.items():
                merged.trips[p + tid] = Trip(trip_id=p + tid, route_id=p + t.route_id,
                                             service_id=p + t.service_id,
                                             wheelchair_accessible=t.wheelchair_accessible)
            for st in sub.stop_times:
                merged.stop_times.append(StopTime(trip_id=p + st.trip_id, seq=st.seq,
                                                   stop_id=p + st.stop_id, arr=st.arr, dep=st.dep))
            for tf in sub.transfers:
                merged.transfers.append(Transfer(p + tf.from_stop, p + tf.to_stop,
                                                 tf.min_transfer_time))

        # Cross-agency walking transfers (MF-3): only between DIFFERENT agencies.
        agencies = list(per_agency_stops)
        for i in range(len(agencies)):
            for j in range(i + 1, len(agencies)):
                for a in per_agency_stops[agencies[i]]:
                    for b in per_agency_stops[agencies[j]]:
                        d = haversine_m(a.lat, a.lon, b.lat, b.lon)
                        if d <= max_interagency_walk_m:
                            secs = int(math.ceil(d * 1.3 / walk_m_per_min * 60))
                            merged.transfers.append(Transfer(a.stop_id, b.stop_id, secs))
                            merged.transfers.append(Transfer(b.stop_id, a.stop_id, secs))
        return merged.index()


def _active_services(path: str, date: str) -> set[str]:
    """Service_ids active on the ISO date, honouring calendar + calendar_dates."""
    d = _dt.date.fromisoformat(date)
    weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]
    ymd = date.replace("-", "")
    active: set[str] = set()
    cal = os.path.join(path, "calendar.txt")
    if os.path.exists(cal):
        with open(cal, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("start_date", "") <= ymd <= row.get("end_date", "99999999") and row.get(weekday) == "1":
                    active.add(row["service_id"])
    cd = os.path.join(path, "calendar_dates.txt")
    if os.path.exists(cd):
        with open(cd, newline="") as f:
            for row in csv.DictReader(f):
                if row["date"] != ymd:
                    continue
                if row["exception_type"] == "1":
                    active.add(row["service_id"])
                elif row["exception_type"] == "2":
                    active.discard(row["service_id"])
    return active
