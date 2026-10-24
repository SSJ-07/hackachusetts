"""Properties for VP-23 (plan B from signed templates) and VP-24 (driver windows).

Spec: .kiro/specs/visit-planner (tasks 17, 18). SYNTHETIC patients, rules and trips only.
"""

from __future__ import annotations

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

from planner.driver_windows import DAY_CODES, DriverWindow
from planner.guardrails import find_banned
from planner.models import Barriers, CandidateSlot, Leg, OptionKind, Patient, RoundTripResult, VisitRule
from planner.plan_b import render
from planner.solver import plan_visit, slot_iso
from planner.transit import FixtureRoundTrip, travel_window

MIN = 60
ORIGIN = "250130000000"
PATIENT = Patient(id="synthetic-p", origin_bg=ORIGIN, lang="en")
TOWNS = ["Hadley", "Southampton", "Nowhere"]
SECTIONS = {
    "later_bus": "There is a later bus home at {{later_bus_time}}.",
    "last_bus": "This is the last bus home today.",
}

settings.register_profile("vp2324", deadline=None, max_examples=200)
settings.load_profile("vp2324")

rules = st.builds(
    VisitRule,
    visit_type=st.just("type-a"),
    duration_min=st.integers(1, 300),
    escort_required=st.booleans(),
    telehealth_ok=st.booleans(),
    prep=st.booleans(),
)
barrier_sets = st.builds(
    Barriers,
    has_transport=st.booleans(),
    work_shift=st.none() | st.tuples(st.integers(0, 24), st.integers(0, 24)),
    childcare=st.booleans(),
    has_escort=st.booleans(),
    cost_worry=st.booleans(),
    language=st.sampled_from(["en", "es"]),
)
slots = st.builds(
    CandidateSlot,
    clinic_id=st.sampled_from(["c1", "c2"]),
    date=st.sampled_from(["2026-11-09", "2026-11-11", "2026-11-14"]),  # mon, wed, sat
    start=st.integers(5 * 60, 20 * 60).map(lambda m: m * MIN),
)


@st.composite
def trips(draw):
    if not draw(st.booleans()):
        return RoundTripResult(reachable=False, reason="synthetic")
    leave = draw(st.integers(4 * 60, 21 * 60)) * MIN
    home = leave + draw(st.integers(1, 6 * 60)) * MIN
    ret_dep = home - MIN
    later = draw(st.integers(0, 120)) * MIN  # 0 => the chosen return is the last bus
    return RoundTripResult(
        reachable=True,
        out_legs=(Leg("bus", "origin", "clinic", "R", leave, leave + MIN),),
        ret_legs=(Leg("bus", "clinic", "origin", "R", ret_dep, home),),
        last_bus_home=ret_dep + later,
        reason="synthetic",
    )


@st.composite
def windows(draw):
    start = draw(st.integers(0, 20 * 60)) * MIN
    end = start + draw(st.integers(1, 12 * 60)) * MIN
    return DriverWindow(
        town=draw(st.sampled_from(TOWNS[:2])), provider="synthetic driver", kind="volunteer_driver",
        days=frozenset(draw(st.sets(st.sampled_from(DAY_CODES), min_size=1))),
        start=start, end=end, notice_days=None, source_url="https://example.org/synthetic", date="2026-10-24",
    )


@st.composite
def scenarios(draw):
    cand = draw(st.lists(slots, max_size=5, unique=True))
    table = {(ORIGIN, s.clinic_id, s.date, s.start): draw(trips()) for s in cand}
    wins = tuple(draw(st.lists(windows(), max_size=4)))
    town = draw(st.sampled_from(TOWNS + [None]))
    return draw(rules), draw(barrier_sets), cand, table, wins, town


def _plan(sc, use_windows=True, sections=None):
    rule, barriers, cand, table, wins, town = sc
    return plan_visit(
        PATIENT, rule, barriers, cand, FixtureRoundTrip(table),
        driver_windows=wins if use_windows else (), patient_town=town, plan_b_sections=sections,
    )


def _covers_oracle(w: DriverWindow, date: str, span: tuple[int, int]) -> bool:
    day = DAY_CODES[dt.date.fromisoformat(date).weekday()]
    return day in w.days and w.start <= span[0] and span[1] <= w.end


def _span(sc, option):
    rule, _, cand, table, _, _ = sc
    s = {(slot_iso(c), c.clinic_id): c for c in cand}[(option.details["slot"], option.details["clinic_id"])]
    window = travel_window(table[(ORIGIN, s.clinic_id, s.date, s.start)])
    return s, window or (s.start, s.start + rule.duration_min * 60)


# ------------------------------------------------------------------ VP-24
@given(scenarios())
def test_vp24_volunteer_ride_only_inside_a_window(sc):
    _, _, _, _, wins, town = sc
    for o in _plan(sc).options:
        if o.kind is not OptionKind.RIDE:
            continue
        s, span = _span(sc, o)
        mine = [w for w in wins if town and w.town.casefold() == town.casefold()]
        hit = any(_covers_oracle(w, s.date, span) for w in mine)
        if o.details["ride_mode"] == "volunteer_driver":
            assert hit and o.details["window"]["source_url"]
        else:
            assert o.details["ride_mode"] == "pt1_broker" and o.details["window"] is None
            assert not hit  # completeness: a covering window is never missed


@given(scenarios())
def test_vp24_windows_never_add_or_drop_options(sc):
    with_w = _plan(sc).options
    without = _plan(sc, use_windows=False).options
    assert [(o.kind, o.details.get("slot")) for o in with_w] == [(o.kind, o.details.get("slot")) for o in without]


@given(scenarios())
def test_escort_still_never_transit_only_with_windows(sc):
    plan = _plan(sc, sections=SECTIONS)
    if sc[0].escort_required:
        assert OptionKind.SLOT not in {o.kind for o in plan.options}
        assert plan.itinerary.plan_b is None and plan.itinerary.out_legs == ()


# ------------------------------------------------------------------ VP-23
@given(scenarios())
def test_vp23_no_signed_template_means_no_plan_b(sc):
    assert _plan(sc, sections=None).itinerary.plan_b is None


@given(scenarios())
def test_vp23_plan_b_only_from_template_and_right_situation(sc):
    plan = _plan(sc, sections=SECTIONS)
    pb = plan.itinerary.plan_b
    if pb is None:
        assert plan.itinerary.ret_legs == ()
        return
    last = plan.itinerary.last_bus_home
    ret_dep = plan.itinerary.ret_legs[0].dep
    if last is not None and last > ret_dep:
        t = last % 86_400
        assert pb == render(SECTIONS, "later_bus", {"later_bus_time": f"{t // 3600:02d}:{t % 3600 // 60:02d}"})
    else:
        assert pb == render(SECTIONS, "last_bus", {})
    assert not find_banned(pb)
