import subprocess
import sys
from pathlib import Path

import pytest

from planner.guardrails import GuardrailViolation, assert_logistics_only, find_banned
from planner.models import OptionKind
from planner.solver import REASONS, overlaps, plan_visit, shift_intervals, slot_iso
from tests.unit.planner_fixtures import (
    ESCORT_RULE,
    PATIENT,
    PT1_FIELDS,
    TELE_RULE,
    TRANSIT_RULE,
    barriers,
    round_trips,
    slot,
    trip,
)


def kinds(plan):
    return [o.kind for o in plan.options]


# ---- escort rule ---------------------------------------------------------- #
def test_escort_visit_gets_ride_not_slot():
    s = slot(15.5)
    plan = plan_visit(PATIENT, ESCORT_RULE, barriers(), [s], round_trips({s: trip(15.1, 17.9)}), PT1_FIELDS)
    assert kinds(plan) == [OptionKind.RIDE, OptionKind.PREP]
    assert plan.options[0].details["slot"] == "2026-11-12T15:30:00"
    assert plan.itinerary.out_legs == ()  # no bus itinerary for a ride
    assert plan.pt1_prefill == {"f_member": "synthetic-1", "f_time": "15:30", "f_escort": True, "f_signature": None}


def test_escort_slot_inside_shift_is_dropped():
    early, late = slot(8), slot(15.5)
    rt = round_trips({early: trip(7.0, 10.5), late: trip(15.1, 17.9)})
    plan = plan_visit(PATIENT, ESCORT_RULE, barriers(), [early, late], rt)
    rides = [o for o in plan.options if o.kind is OptionKind.RIDE]
    assert [o.details["slot"] for o in rides] == ["2026-11-12T15:30:00"]


def test_escort_without_travel_estimate_is_ok_when_no_shift():
    s = slot(9)
    plan = plan_visit(PATIENT, ESCORT_RULE, barriers(shift=None), [s], round_trips({}))
    assert kinds(plan)[0] is OptionKind.RIDE


def test_escort_without_travel_estimate_is_dropped_with_shift():
    s = slot(16)
    plan = plan_visit(PATIENT, ESCORT_RULE, barriers(), [s], round_trips({}))
    assert kinds(plan) == [OptionKind.NONE]
    assert plan.options[0].why == REASONS["none_escort"]


# ---- shift rule ----------------------------------------------------------- #
def test_travel_into_shift_excludes_slot():
    s = slot(16)
    # Leaves home at 14:30, inside the 7-15 shift, even though the visit is after it.
    plan = plan_visit(PATIENT, TRANSIT_RULE, barriers(), [s], round_trips({s: trip(14.5, 18)}))
    assert kinds(plan) == [OptionKind.NONE]
    assert plan.options[0].why == REASONS["none_shift"]


def test_leaving_exactly_at_shift_end_is_allowed():
    s = slot(16)
    plan = plan_visit(PATIENT, TRANSIT_RULE, barriers(), [s], round_trips({s: trip(15, 18)}))
    assert kinds(plan) == [OptionKind.SLOT]


# ---- childcare window (VP-20) --------------------------------------------- #
def test_slot_overlapping_childcare_window_is_dropped():
    # No work shift, but a childcare window 15:00-18:00. The trip leaves at 15:30,
    # inside the window, so the slot must not be recommended.
    s = slot(16)
    b = barriers(shift=None, childcare_window=(15, 18))
    plan = plan_visit(PATIENT, TRANSIT_RULE, barriers=b, candidate_slots=[s],
                      round_trip=round_trips({s: trip(15.5, 17.5)}))
    assert kinds(plan) == [OptionKind.NONE]
    assert plan.options[0].why == REASONS["none_shift"]


def test_slot_outside_childcare_window_is_allowed():
    # Childcare window 15:00-18:00; the trip is entirely before it (09:00-11:00).
    s = slot(9.5)
    b = barriers(shift=None, childcare_window=(15, 18))
    plan = plan_visit(PATIENT, TRANSIT_RULE, barriers=b, candidate_slots=[s],
                      round_trip=round_trips({s: trip(9, 11)}))
    assert kinds(plan) == [OptionKind.SLOT]


def test_childcare_window_blocks_untimed_escort_ride():
    # Escort ride with no travel estimate + a childcare window -> cannot verify, dropped.
    s = slot(16)
    b = barriers(shift=None, childcare_window=(15, 18))
    plan = plan_visit(PATIENT, ESCORT_RULE, barriers=b, candidate_slots=[s],
                      round_trip=round_trips({}))
    assert kinds(plan) == [OptionKind.NONE]
    assert plan.options[0].why == REASONS["none_escort"]


def test_overnight_shift_and_after_midnight_trip():
    # Shift 22:00-06:00. A trip arriving home at 24:30 (88200 s) overlaps it.
    intervals = shift_intervals((22, 6))
    assert overlaps((20 * 3600, 88200), intervals)
    assert not overlaps((7 * 3600, 21 * 3600), intervals)


def test_slot_itinerary_uses_best_ranked_slot():
    a, b = slot(16), slot(17)
    rt = round_trips({a: trip(15.0, 19.0, 21), b: trip(16.0, 18.5, 20)})
    plan = plan_visit(PATIENT, TRANSIT_RULE, barriers(), [a, b], rt)
    assert [o.details["slot"] for o in plan.options] == ["2026-11-12T17:00:00", "2026-11-12T16:00:00"]
    assert plan.itinerary.last_bus_home == 20 * 3600


# ---- telehealth + none ---------------------------------------------------- #
def test_telehealth_offered_only_when_allowed():
    s = slot(16)
    rt = round_trips({s: trip(15, 18)})
    assert OptionKind.TELE in kinds(plan_visit(PATIENT, TELE_RULE, barriers(), [s], rt))
    assert OptionKind.TELE not in kinds(plan_visit(PATIENT, TRANSIT_RULE, barriers(), [s], rt))


@pytest.mark.parametrize("field", ["duration_min", "escort_required", "telehealth_ok", "prep"])
def test_unverified_rule_hands_off_to_navigator(field):
    from dataclasses import replace

    rule = replace(TRANSIT_RULE, **{field: None})
    s = slot(16)
    plan = plan_visit(PATIENT, rule, barriers(), [s], round_trips({s: trip(15, 18)}))
    assert kinds(plan) == [OptionKind.NONE]
    assert plan.options[0].why == REASONS["none_rules_unverified"]


def test_no_candidates_gives_single_none_and_no_prep():
    plan = plan_visit(PATIENT, ESCORT_RULE, barriers(), [], round_trips({}))
    assert kinds(plan) == [OptionKind.NONE]
    assert plan.options[0].why == REASONS["none_no_candidates"]
    assert plan.options[0].details == {"navigator_followup": True}


def test_unreachable_gives_none_no_transit():
    s = slot(16)
    plan = plan_visit(PATIENT, TRANSIT_RULE, barriers(), [s], round_trips({}))
    assert plan.options[0].why == REASONS["none_no_transit"]


# ---- helpers + guardrails ------------------------------------------------- #
def test_slot_iso_rolls_past_midnight():
    assert slot_iso(slot(24.5)) == "2026-11-13T00:30:00"


def test_reasons_are_logistics_only():
    assert_logistics_only(list(REASONS.values()))


@pytest.mark.parametrize("text", ["You are eligible", "Not ELIGIBLE", "she qualifies", "diagnosis pending"])
def test_guardrail_catches_banned_wording(text):
    assert find_banned(text)
    with pytest.raises(GuardrailViolation):
        assert_logistics_only({"why": text})


def test_planner_does_not_import_web_frameworks():
    root = Path(__file__).resolve().parents[2]
    code = (
        "import sys, planner.solver, planner.rules, planner.pt1, planner.transit; "
        "bad = [m for m in ('fastapi', 'pydantic', 'starlette', 'api') if m in sys.modules]; "
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], cwd=root, check=True)
