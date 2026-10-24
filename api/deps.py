"""FastAPI dependencies: where each endpoint's data comes from.

`SLOT_TO_STOP_DATA` selects the data mode:
  mock (default) - labelled mocks in api/mocks/ (H1 scaffold).
  real           - real files/engine only. Anything not landed yet returns 503 rather
                   than falling back to mock data silently.
Tests override these dependencies with their own synthetic fixtures.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException, status

from api import mocks
from planner.models import CandidateSlot, VisitRule
from planner.pt1 import Pt1Field, Pt1FieldsError, load_fields
from planner.rules import RulebookError, load_rules
from planner.transit import FixtureRoundTrip, RoundTripFn

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_RULES_PATH = REPO_ROOT / "planner" / "visit_rules.yaml"
REAL_PT1_PATH = REPO_ROOT / "data" / "manual" / "pt1_fields.json"

DataMode = Literal["mock", "real"]
CandidateSlotSource = Callable[[VisitRule], Sequence[CandidateSlot]]


def data_mode() -> DataMode:
    mode = os.environ.get("SLOT_TO_STOP_DATA", "mock")
    if mode not in ("mock", "real"):
        raise RuntimeError(f"SLOT_TO_STOP_DATA must be 'mock' or 'real', got {mode!r}")
    return mode  # type: ignore[return-value]


def _unavailable(what: str) -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"{what} is not available yet.")


# --------------------------------------------------------------------------- #
# /audit, /whatif (M2)
# --------------------------------------------------------------------------- #
def get_audit_data() -> dict[str, Any]:
    if data_mode() == "mock":
        return mocks.load("audit.json")
    raise _unavailable("Reachability cube (M2)")


# --------------------------------------------------------------------------- #
# /provenance
# --------------------------------------------------------------------------- #
def get_provenance_index() -> Mapping[str, Mapping[str, Any]]:
    if data_mode() == "mock":
        return mocks.load("provenance.json")["records"]
    # TODO(M4+M1): build from docs/traceability.md + docs/provenance.jsonl.
    raise _unavailable("Provenance index")


# --------------------------------------------------------------------------- #
# /plan
# --------------------------------------------------------------------------- #
def get_visit_rules() -> dict[str, VisitRule]:
    mock = data_mode() == "mock"
    path = mocks.PLANNER_MOCKS_DIR / "visit_rules.yaml" if mock else REAL_RULES_PATH
    try:
        return load_rules(path)
    except RulebookError as exc:
        raise _unavailable("Visit rulebook (planner/visit_rules.yaml, M3)") from exc


def get_pt1_fields() -> tuple[Pt1Field, ...]:
    mock = data_mode() == "mock"
    path = mocks.PLANNER_MOCKS_DIR / "pt1_fields.json" if mock else REAL_PT1_PATH
    if not mock and not path.is_file():
        return ()  # pt1_prefill stays {} until M3 lands the field list
    try:
        return load_fields(path)
    except Pt1FieldsError as exc:
        raise _unavailable("PT-1 field list") from exc


def get_candidate_slot_source() -> CandidateSlotSource:
    if data_mode() == "real":
        # TODO(M3/M4): read data/manual/clinic_schedules.csv.
        raise _unavailable("Clinic schedules (data/manual/clinic_schedules.csv, M3)")
    by_type = mocks.load("planner/candidate_slots.json")["slots"]

    def source(rule: VisitRule) -> list[CandidateSlot]:
        return [CandidateSlot(**s) for s in by_type.get(rule.visit_type, [])]

    return source


def get_round_trip() -> RoundTripFn:
    if data_mode() == "real":
        # TODO(M1 handoff): return functools.partial(engine.round_trip, timetable) once a
        # PVTA timetable + data/cache/stops_walk.parquet are available.
        raise _unavailable("Routing engine (engine.round_trip, M1)")
    return FixtureRoundTrip.from_records(mocks.load("planner/round_trips.json")["records"])
