"""Plain dataclasses for the Visit Planner (standard library only).

Shapes mirror docs/contracts.md. Times are integer seconds since local midnight of
the service date and may exceed 86400; they are never wrapped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OptionKind(str, Enum):
    """Option kinds fixed by docs/contracts.md §3 (POST /plan)."""

    SLOT = "slot"
    RIDE = "ride"
    TELE = "tele"
    PREP = "prep"
    NONE = "none"


# --------------------------------------------------------------------------- #
# Engine shapes (docs/contracts.md §2).
# TODO(M1 handoff): import these from engine/ once it exports them.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Leg:
    kind: str  # "walk" | "bus"
    from_stop: str  # stop_id or "origin"/"clinic"
    to_stop: str
    route_id: str | None
    dep: int
    arr: int


@dataclass(frozen=True)
class RoundTripResult:
    reachable: bool
    out_legs: tuple[Leg, ...] = ()
    ret_legs: tuple[Leg, ...] = ()
    last_bus_home: int | None = None
    reason: str = ""

    @property
    def travel_window(self) -> tuple[int, int] | None:
        """(leave home, arrive home) in seconds, or None if not a complete round trip."""
        if not (self.reachable and self.out_legs and self.ret_legs):
            return None
        return self.out_legs[0].dep, self.ret_legs[-1].arr


# --------------------------------------------------------------------------- #
# Planner inputs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VisitRule:
    """One visit type from planner/visit_rules.yaml (M3). See steering visit-rules.md."""

    visit_type: str
    duration_min: int
    escort_required: bool
    telehealth_ok: bool
    prep: bool
    recurrence: str | None = None


@dataclass(frozen=True)
class Patient:
    """Synthetic patients only."""

    id: str
    origin_bg: str  # 12-digit block-group GEOID
    lang: str


@dataclass(frozen=True)
class Barriers:
    """Barrier-check answers. Fields follow docs/contracts.md §3."""

    has_transport: bool
    work_shift: tuple[int, int] | None  # (start_hour, end_hour), 24h local; may cross midnight
    childcare: bool
    has_escort: bool
    cost_worry: bool
    language: str


@dataclass(frozen=True)
class CandidateSlot:
    """An appointment slot the clinic could offer."""

    clinic_id: str
    date: str  # ISO service date "YYYY-MM-DD"
    start: int  # seconds since local midnight


# --------------------------------------------------------------------------- #
# Planner outputs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Option:
    kind: OptionKind
    why: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Itinerary:
    out_legs: tuple[Leg, ...] = ()
    ret_legs: tuple[Leg, ...] = ()
    last_bus_home: int | None = None
    plan_b: str | None = None


@dataclass(frozen=True)
class Plan:
    options: tuple[Option, ...]
    itinerary: Itinerary
    pt1_prefill: dict[str, Any]
