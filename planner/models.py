"""Plain dataclasses for the Visit Planner (standard library + engine types only).

Leg and RoundTripResult are the engine's own types (docs/contracts.md §2), so the
planner and M1's router share one definition. Times are integer seconds since local
midnight of the service date and may exceed 86400; they are never wrapped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.types import Leg, RoundTripResult

__all__ = [
    "Barriers",
    "CandidateSlot",
    "Itinerary",
    "Leg",
    "Option",
    "OptionKind",
    "Patient",
    "Plan",
    "RoundTripResult",
    "VisitRule",
]


class OptionKind(str, Enum):
    """Option kinds fixed by docs/contracts.md §3 (POST /plan)."""

    SLOT = "slot"
    RIDE = "ride"
    TELE = "tele"
    PREP = "prep"
    NONE = "none"


# --------------------------------------------------------------------------- #
# Planner inputs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VisitRule:
    """One visit type from planner/visit_rules.yaml (M3). See steering visit-rules.md.

    None means "not verified yet" and is never read as 0 or false.
    """

    visit_type: str
    duration_min: int | None
    escort_required: bool | None
    telehealth_ok: bool | None
    prep: bool | None
    recurrence_per_week: int | None = None
    source_status: str = "todo"

    @property
    def is_complete(self) -> bool:
        """True when every field the solver needs has a value."""
        return None not in (self.duration_min, self.escort_required, self.telehealth_ok, self.prep)


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
