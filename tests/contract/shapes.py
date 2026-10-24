"""Contract shapes, written directly from docs/contracts.md §2-3.

Deliberately independent of api/schemas.py: these models are the test oracle, so a
drift in the API models fails here. extra="forbid" catches added or renamed fields.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class _C(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


# ---- GET /audit, POST /whatif -------------------------------------------- #
class Cell(_C):
    day: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    hour: int
    share: float
    n: int
    reached: int


class Group(_C):
    share: float
    n: int


class Equity(_C):
    ej: Group
    lep: Group
    age65: Group
    zero_veh: Group


class CIGroup(_C):
    share: float
    lo: float
    hi: float
    moe: float
    n: int


class EquityCI(_C):
    ej: CIGroup
    lep: CIGroup
    age65: CIGroup
    zero_veh: CIGroup


class Source(_C):
    name: str
    vintage: str
    url: str | None = None


class Audit(_C):
    cells: list[Cell]
    equity: Equity
    equity_ci: EquityCI | None  # contracts.md: null when ACS margins are not built
    sources: list[Source]


# ---- POST /plan ------------------------------------------------------------ #
class Leg(_C):
    kind: Literal["walk", "bus"]
    from_stop: str
    to_stop: str
    route_id: str | None
    dep: int
    arr: int


class Option(_C):
    kind: Literal["slot", "ride", "tele", "prep", "none"]
    details: dict[str, Any]
    why: str


class Itinerary(_C):
    out_legs: list[Leg]
    ret_legs: list[Leg]
    last_bus_home: int | None
    plan_b: str | None


class Plan(_C):
    options: list[Option]
    itinerary: Itinerary
    pt1_prefill: dict[str, Any]


# ---- GET /provenance?id ---------------------------------------------------- #
class ProvSource(_C):
    name: str
    vintage: str


class PropertyStatus(_C):
    name: str
    status: str


class Provenance(_C):
    source: ProvSource
    requirement_id: str
    properties: list[PropertyStatus]
    spec_link: str
