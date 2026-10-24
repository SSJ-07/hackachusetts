"""Visit Planner constraint solver (owner: M4). Spec: .kiro/specs/visit-planner/.

Pure function: no FastAPI, no Pydantic, no I/O. Uses only the standard library and
engine.types. The transit check is injected (`RoundTripFn`: `engine.round_trip` with
its timetable bound).

Hard rules (steering visit-rules.md):
  R0 unverified rule  -> any null field in the rulebook entry: a single `none` option.
  R1 escort_required  -> never a transit-only option; offer an escort-aware ride.
  R2 shift            -> no recommended slot overlaps the work shift, travel included.
  R3 telehealth_ok    -> a telehealth swap only when the visit type allows it.
  R4 nothing viable   -> exactly one `none` option with a reason for a navigator.
  R5 output text      -> logistics only (planner.guardrails).
  R6 ranking          -> deterministic; independent of candidate order.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timedelta

from planner.guardrails import assert_logistics_only
from planner.models import (
    Barriers,
    CandidateSlot,
    Itinerary,
    Option,
    OptionKind,
    Patient,
    Plan,
    RoundTripResult,
    VisitRule,
)
from planner.pt1 import Pt1Field, prefill
from planner.transit import RoundTripFn, travel_window

SOLVER_VERSION = "0.1.0"
_DAY = 86_400
_HOUR = 3_600

# Rank of each kind in the output (contract order: slot | ride | tele | prep | none).
KIND_RANK: dict[OptionKind, int] = {kind: i for i, kind in enumerate(OptionKind)}

# Coordinator-facing reasons. Logistics only. These are NOT patient-facing text;
# patient text comes only from human-reviewed templates (M3).
REASONS: dict[str, str] = {
    "slot": "Round trip by transit fits outside the stated work shift.",
    "ride_escort": "This visit type requires an escort home, so a transit-only plan is not offered. "
    "Request an escort-aware ride.",
    "tele": "This visit type allows a telehealth visit.",
    "prep": "This visit type has a prep sheet. Attach the reviewed version in the preferred language.",
    "none_no_candidates": "No candidate slots were provided. Flag for a navigator to call.",
    "none_no_transit": "No candidate slot has a round trip by transit. Flag for a navigator to call.",
    "none_shift": "Every reachable slot overlaps the work shift, including travel. "
    "Flag for a navigator to call.",
    "none_escort": "An escort-aware ride is needed, but no slot could be checked against the work "
    "shift including travel. Flag for a navigator to call.",
    "none_rules_unverified": "Logistics rules for this visit type are not verified yet. "
    "Flag for a navigator to call.",
}


@dataclass(frozen=True)
class _Checked:
    slot: CandidateSlot
    trip: RoundTripResult
    window: tuple[int, int] | None  # (leave home, arrive home), seconds
    shift_conflict: bool

    @property
    def burden(self) -> tuple[int, int]:
        # Known door-to-door time ranks ahead of unknown.
        if self.window is None:
            return (1, 0)
        return (0, self.window[1] - self.window[0])

    @property
    def sort_key(self) -> tuple:
        return (*self.burden, self.slot.date, self.slot.start, self.slot.clinic_id)


def slot_iso(slot: CandidateSlot) -> str:
    """ISO local datetime of the appointment start; start >= 86400 rolls to the next date."""
    base = datetime.combine(Date.fromisoformat(slot.date), datetime.min.time())
    return (base + timedelta(seconds=slot.start)).isoformat()


def shift_intervals(work_shift: tuple[int, int] | None) -> list[tuple[int, int]]:
    """The shift as second intervals over the service day and the next day, so trips with
    times > 86400 and overnight shifts are both covered."""
    if work_shift is None:
        return []
    start, end = work_shift[0] * _HOUR, work_shift[1] * _HOUR
    if start == end:
        return []
    base = [(start, end)] if start < end else [(0, end), (start, _DAY)]
    return [(s + d, e + d) for d in (0, _DAY) for s, e in base]


def overlaps(window: tuple[int, int], intervals: Iterable[tuple[int, int]]) -> bool:
    lo, hi = window
    return any(lo < e and hi > s for s, e in intervals)


def _check(
    patient: Patient,
    rule: VisitRule,
    slots: Iterable[CandidateSlot],
    round_trip: RoundTripFn,
    shift: list[tuple[int, int]],
) -> list[_Checked]:
    checked = []
    for slot in slots:
        trip = round_trip(patient.origin_bg, slot.clinic_id, slot.date, slot.start, rule.duration_min)
        window = travel_window(trip)
        conflict = window is not None and overlaps(window, shift)
        checked.append(_Checked(slot, trip, window, conflict))
    return sorted(checked, key=lambda c: c.sort_key)


def _none_reason(rule: VisitRule, checked: Sequence[_Checked]) -> str:
    if not checked:
        return REASONS["none_no_candidates"]
    if rule.escort_required:
        return REASONS["none_escort"]
    if all(c.window is None for c in checked):
        return REASONS["none_no_transit"]
    return REASONS["none_shift"]


def plan_visit(
    patient: Patient,
    rule: VisitRule,
    barriers: Barriers,
    candidate_slots: Sequence[CandidateSlot],
    round_trip: RoundTripFn,
    pt1_fields: tuple[Pt1Field, ...] = (),
) -> Plan:
    if not rule.is_complete:
        # R0: unknown (null) rules are never guessed. Without a verified escort rule we
        # cannot rule out a transit-only plan, so hand off to a navigator.
        return Plan(
            options=(
                Option(
                    OptionKind.NONE,
                    REASONS["none_rules_unverified"],
                    {"navigator_followup": True, "rules_status": rule.source_status},
                ),
            ),
            itinerary=Itinerary(),
            pt1_prefill={},
        )

    shift = shift_intervals(barriers.work_shift)
    checked = _check(patient, rule, set(candidate_slots), round_trip, shift)

    # VP-21: cost_worry and has_transport never change the FIXED kind order
    # (slot | ride | tele | prep | none, R6) and never gate an option out — doing
    # either would be a logistics judgement we cannot source. They are recorded as
    # navigator-facing flags so the UI and a human can weigh burden and out-of-pocket
    # cost, and they break ties among same-kind slots in favour of the lowest burden.
    access_flags = {
        "cost_sensitive": barriers.cost_worry,
        "no_personal_transport": not barriers.has_transport,
    }

    attend: list[tuple[Option, _Checked | None]] = []
    if rule.escort_required:
        # R1: rides only. The transit round trip is used as a conservative travel-time
        # proxy for the shift check; without any travel estimate the slot is only
        # usable when there is no shift to conflict with.
        for c in checked:
            if c.shift_conflict or (c.window is None and shift):
                continue
            details = {
                "slot": slot_iso(c.slot),
                "clinic_id": c.slot.clinic_id,
                "escort_required": True,
                "has_escort": barriers.has_escort,
                "pt1_request": True,
                **access_flags,
            }
            attend.append((Option(OptionKind.RIDE, REASONS["ride_escort"], details), c))
    else:
        for c in checked:
            if c.window is None or c.shift_conflict:
                continue
            details = {"slot": slot_iso(c.slot), "clinic_id": c.slot.clinic_id, **access_flags}
            attend.append((Option(OptionKind.SLOT, REASONS["slot"], details), c))

    if rule.telehealth_ok:  # R3
        # A telehealth visit removes the trip entirely, so flag it as the zero-travel
        # option when the patient has no transport of their own or is cost-sensitive.
        tele_details = {
            "zero_travel": True,
            "relieves_no_transport": not barriers.has_transport,
            "relieves_cost": barriers.cost_worry,
        }
        attend.append((Option(OptionKind.TELE, REASONS["tele"], tele_details), None))

    # R6: stable order by kind, then by the candidate's burden/sort key.
    attend.sort(key=lambda oc: (KIND_RANK[oc[0].kind], oc[1].sort_key if oc[1] else ()))

    if not attend:  # R4
        options: list[Option] = [
            Option(OptionKind.NONE, _none_reason(rule, checked), {"navigator_followup": True})
        ]
    else:
        options = [o for o, _ in attend]
        # VP-22: a recurring visit (e.g. dialysis 3x/week) is not a one-off. Annotate the
        # top attend option so the UI/navigator plans the repeating pattern. Logistics
        # only: we surface the cadence from the rulebook, never a clinical schedule.
        if rule.recurrence_per_week and options:
            top = options[0]
            options[0] = Option(
                top.kind,
                top.why,
                {
                    **top.details,
                    "recurrence_per_week": rule.recurrence_per_week,
                    "recurrence_note": (
                        f"This visit repeats about {rule.recurrence_per_week}x per week; "
                        "plan the same trip for each session."
                    ),
                },
            )
        if rule.prep:
            options.append(
                Option(
                    OptionKind.PREP,
                    REASONS["prep"],
                    {"language": barriers.language, "template_status": "pending_review"},
                )
            )

    top_slot = next((c for o, c in attend if o.kind is OptionKind.SLOT), None)
    itinerary = (
        Itinerary(
            out_legs=tuple(top_slot.trip.out_legs),
            ret_legs=tuple(top_slot.trip.ret_legs),
            last_bus_home=top_slot.trip.last_bus_home,
            plan_b=None,  # patient-facing text: waits on reviewed templates (M3)
        )
        if top_slot
        else Itinerary()
    )

    top_ride = next((c for o, c in attend if o.kind is OptionKind.RIDE), None)
    pt1 = (
        prefill(pt1_fields, patient, rule, top_ride.slot, barriers.language)
        if top_ride and pt1_fields
        else {}
    )

    plan = Plan(options=tuple(options), itinerary=itinerary, pt1_prefill=pt1)
    assert_logistics_only([[o.why, o.details] for o in plan.options])  # R5
    return plan
