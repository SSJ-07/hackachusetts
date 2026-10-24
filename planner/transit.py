"""Transit check interface + stub (docs/contracts.md §2).

The solver receives a `RoundTripFn` with the same signature as `engine.round_trip`.
Until M1's engine lands, `FixtureRoundTrip` answers from a fixed table. It never
computes or guesses a trip: anything not in the table is reported as unreachable.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from planner.models import Leg, RoundTripResult


class RoundTripFn(Protocol):
    def __call__(
        self, origin: str, clinic: str, date: str, start: int, minutes: int
    ) -> RoundTripResult: ...


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
        out_legs=tuple(leg_from_dict(x) for x in raw.get("out_legs", ())),
        ret_legs=tuple(leg_from_dict(x) for x in raw.get("ret_legs", ())),
        last_bus_home=raw.get("last_bus_home"),
        reason=str(raw.get("reason", "")),
    )


class FixtureRoundTrip:
    """Stub `engine.round_trip`, keyed by (origin, clinic, date, start).

    TODO(M1 handoff): replace with `engine.round_trip`.
    """

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
