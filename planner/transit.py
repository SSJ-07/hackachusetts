"""Transit check interface + stub (docs/contracts.md §2).

The solver receives a `RoundTripFn`: `engine.round_trip` with the timetable already
bound, e.g. `functools.partial(engine.round_trip, timetable)`.

`FixtureRoundTrip` answers from a fixed table for tests and mock mode. It never
computes or guesses a trip: anything not in the table is reported as unreachable.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from engine.types import Leg, RoundTripResult


class RoundTripFn(Protocol):
    def __call__(
        self, origin: str, clinic: str, date: str, start: int, minutes: int
    ) -> RoundTripResult: ...


def travel_window(result: RoundTripResult) -> tuple[int, int] | None:
    """(leave home, arrive home) in seconds, or None if not a complete round trip."""
    if not (result.reachable and result.out_legs and result.ret_legs):
        return None
    return result.out_legs[0].dep, result.ret_legs[-1].arr


def leg_from_dict(raw: Mapping[str, Any]) -> Leg:
    return Leg(
        kind=raw["kind"],
        from_stop=raw["from_stop"],
        to_stop=raw["to_stop"],
        route_id=raw.get("route_id"),
        dep=int(raw["dep"]),
        arr=int(raw["arr"]),
    )


def result_from_dict(raw: Mapping[str, Any]) -> RoundTripResult:
    return RoundTripResult(
        reachable=bool(raw["reachable"]),
        out_legs=[leg_from_dict(x) for x in raw.get("out_legs", ())],
        ret_legs=[leg_from_dict(x) for x in raw.get("ret_legs", ())],
        last_bus_home=raw.get("last_bus_home"),
        reason=str(raw.get("reason", "")),
    )


class FixtureRoundTrip:
    """Stub for `engine.round_trip`, keyed by (origin, clinic, date, start)."""

    def __init__(self, table: Mapping[tuple[str, str, str, int], RoundTripResult]):
        self._table = dict(table)

    @classmethod
    def from_records(cls, records: list[Mapping[str, Any]]) -> FixtureRoundTrip:
        return cls(
            {
                (r["origin"], r["clinic"], r["date"], int(r["start"])): result_from_dict(r["result"])
                for r in records
            }
        )

    def __call__(
        self, origin: str, clinic: str, date: str, start: int, minutes: int
    ) -> RoundTripResult:
        return self._table.get(
            (origin, clinic, date, start),
            RoundTripResult(reachable=False, reason="stub: no fixture for this query"),
        )


class TimetableRoundTrip:
    """Real `RoundTripFn` backed by the engine over the PVTA feed (task 11).

    The planner speaks in `origin_bg` (block-group GEOID) and `clinic_id`; the engine's
    round_trip takes (lat, lon) refs. This adapter resolves both, then calls the one
    authoritative `engine.round_trip` (steering: never re-derive reachability):

      * clinic_id -> PVTA stop -> (lat, lon)   via data/manual/clinic_stops.csv
      * origin_bg -> centroid (lat, lon)       via data/cache/origins.parquet

    A `Timetable` is loaded once per service date and cached (loading per request would
    reparse the whole feed). A clinic or block group not in the maps yields an
    unreachable result WITH A REASON rather than a guessed coordinate — honest, never a
    wrong answer. Pandas/pyarrow are imported lazily so importing this module (and thus
    the API) never requires the pipeline deps when real data is absent.
    """

    def __init__(self, pvta_dir: Path, origins_path: Path, clinic_stops_path: Path):
        self._pvta_dir = pvta_dir
        self._origins_path = origins_path
        self._clinic_stops_path = clinic_stops_path
        self._tt_cache: dict[str, Any] = {}
        self._origins: dict[str, tuple[float, float]] | None = None
        self._clinic_coords: dict[str, tuple[float, float]] | None = None

    @classmethod
    def cache_ready(cls, pvta_dir: Path, origins_path: Path, clinic_stops_path: Path) -> bool:
        """True only when every real-data input for routing is present."""
        return pvta_dir.is_dir() and origins_path.is_file() and clinic_stops_path.is_file()

    def _origins_map(self) -> dict[str, tuple[float, float]]:
        if self._origins is None:
            import pandas as pd  # lazy: pipeline dep, not needed without real data

            df = pd.read_parquet(self._origins_path)
            self._origins = {
                str(r.bg_geoid): (float(r.lat), float(r.lon)) for r in df.itertuples(index=False)
            }
        return self._origins

    def _clinic_map(self) -> dict[str, tuple[float, float]]:
        if self._clinic_coords is None:
            import csv as _csv

            coords: dict[str, tuple[float, float]] = {}
            with self._clinic_stops_path.open(encoding="utf-8", newline="") as handle:
                for row in _csv.DictReader(handle):
                    stop_id = (row.get("stop_id") or "").strip()
                    clinic_id = (row.get("clinic_id") or "").strip()
                    if clinic_id and stop_id:
                        coords[clinic_id] = self._stop_coord(stop_id)
            self._clinic_coords = {k: v for k, v in coords.items() if v is not None}
        return self._clinic_coords

    def _timetable(self, date: str) -> Any:
        tt = self._tt_cache.get(date)
        if tt is None:
            from engine.gtfs import Timetable

            tt = Timetable.from_gtfs_dir(str(self._pvta_dir), date)
            self._tt_cache[date] = tt
        return tt

    def _stop_coord(self, stop_id: str) -> tuple[float, float] | None:
        # Resolve a clinic's anchor stop to a coordinate via any loaded feed date.
        for tt in self._tt_cache.values():
            stop = tt.stops.get(stop_id)
            if stop is not None:
                return (stop.lat, stop.lon)
        return None

    def __call__(
        self, origin: str, clinic: str, date: str, start: int, minutes: int
    ) -> RoundTripResult:
        from engine import round_trip

        # Load the feed for this date first so clinic-stop coordinates can resolve.
        tt = self._timetable(date)
        origin_ll = self._origins_map().get(origin)
        if origin_ll is None:
            return RoundTripResult(reachable=False, reason=f"origin_bg {origin} not in origins.parquet")

        clinic_stop_coords = self._clinic_map()
        clinic_ll = clinic_stop_coords.get(clinic)
        if clinic_ll is None:
            return RoundTripResult(
                reachable=False, reason=f"clinic {clinic} has no mapped PVTA stop (clinic_stops.csv)"
            )
        return round_trip(tt, origin_ll, clinic_ll, date, start, minutes)
