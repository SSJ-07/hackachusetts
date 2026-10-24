"""Shared engine value types. The exact shapes from docs/contracts.md §2.

Every router (RAPTOR, CSA, brute force) returns these same types, so the
differential tests can compare them field-for-field.

TIME CONVENTION (non-negotiable, see steering/gtfs-domain.md):
    All times are INTEGER SECONDS SINCE LOCAL MIDNIGHT of the service date.
    GTFS times may exceed 86400 (e.g. "24:30:00" -> 88200). Never wrap them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# An origin is either a block-group GEOID (resolved to walk links via
# stops_walk.parquet) or a raw (lat, lon) the engine snaps to nearby stops.
OriginRef = str | tuple[float, float]
# A clinic is either a clinic_id or a raw (lat, lon).
ClinicRef = str | tuple[float, float]


@dataclass(frozen=True)
class Leg:
    """One segment of a journey. contracts.md §2."""

    kind: str  # "walk" | "bus"
    from_stop: str  # stop_id, or "origin" / "clinic"
    to_stop: str
    route_id: str | None
    dep: int  # seconds since local midnight (may exceed 86400)
    arr: int  # seconds since local midnight (may exceed 86400)


@dataclass
class RoundTripResult:
    """Result of round_trip(...). contracts.md §2."""

    reachable: bool
    out_legs: list[Leg] = field(default_factory=list)  # [] if no outbound
    ret_legs: list[Leg] = field(default_factory=list)  # [] if no return
    last_bus_home: int | None = None  # latest return departure that still gets home
    reason: str = ""


@dataclass(frozen=True)
class Limits:
    """Routing limits. Defaults from contracts.md §2 and steering/gtfs-domain.md.

    All durations in seconds; distances in metres.
    """

    max_transfers: int = 2
    max_leg_seconds: int = 2 * 3600  # <= 2h each way
    max_walk_m: int = 800  # each walk leg <= 800 m
    earliest_home_dep: int = 5 * 3600 + 30 * 60  # >= 05:30
    checkin_buffer: int = 600  # arrive <= start - 600 (10 min)
    walk_m_per_min: float = 80.0  # MVP walk speed
    min_transfer_seconds: int = 60  # default when transfers.txt is silent


DEFAULT_LIMITS = Limits()
