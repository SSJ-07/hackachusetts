"""SYNTHETIC test fixtures for planner tests. Not real clinics, rules, trips, or patients."""

from __future__ import annotations

from planner.models import Barriers, CandidateSlot, Leg, Patient, RoundTripResult, VisitRule
from planner.pt1 import Pt1Field
from planner.transit import FixtureRoundTrip

H = 3600
DATE = "2026-11-12"
ORIGIN = "250130000000"  # tract 000000: cannot match a real block group
CLINIC = "test-clinic"

ESCORT_RULE = VisitRule("test-escort", duration_min=120, escort_required=True, telehealth_ok=False, prep=True)
TRANSIT_RULE = VisitRule("test-transit", duration_min=60, escort_required=False, telehealth_ok=False, prep=False)
TELE_RULE = VisitRule("test-tele", duration_min=30, escort_required=False, telehealth_ok=True, prep=False)

PATIENT = Patient(id="synthetic-1", origin_bg=ORIGIN, lang="es")


def barriers(shift=(7, 15), has_escort=False, language="es") -> Barriers:
    return Barriers(
        has_transport=False,
        work_shift=shift,
        childcare=False,
        has_escort=has_escort,
        cost_worry=False,
        language=language,
    )


def slot(start_h: float, clinic: str = CLINIC) -> CandidateSlot:
    return CandidateSlot(clinic_id=clinic, date=DATE, start=int(start_h * H))


def trip(leave_h: float, home_h: float, last_bus_h: float | None = None) -> RoundTripResult:
    leave, home = int(leave_h * H), int(home_h * H)
    return RoundTripResult(
        reachable=True,
        out_legs=(Leg("bus", "origin", "clinic", "T1", leave, leave + 1800),),
        ret_legs=(Leg("bus", "clinic", "origin", "T1", home - 1800, home),),
        last_bus_home=int(last_bus_h * H) if last_bus_h else None,
        reason="test",
    )


def round_trips(entries: dict[CandidateSlot, RoundTripResult]) -> FixtureRoundTrip:
    return FixtureRoundTrip({(ORIGIN, s.clinic_id, s.date, s.start): r for s, r in entries.items()})


PT1_FIELDS = (
    Pt1Field("f_member", "patient.id"),
    Pt1Field("f_time", "visit.start_time"),
    Pt1Field("f_escort", "visit.escort_required"),
    Pt1Field("f_signature", None),
)
