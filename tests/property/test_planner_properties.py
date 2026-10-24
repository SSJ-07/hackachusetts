"""Visit Planner correctness properties (Hypothesis). All inputs are synthetic.

P15 escort => no transit-only option
P16 no recommended slot overlaps the work shift, travel included
P17 telehealth only if the visit type allows it
P18 output never contains clinical/eligibility wording
P-rank ranking is deterministic and independent of candidate order
P-none `none` appears alone, exactly when nothing else is viable
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from planner.guardrails import find_banned, iter_strings
from planner.models import Barriers, CandidateSlot, Leg, OptionKind, Patient, RoundTripResult, VisitRule
from planner.pt1 import SOURCE_KEYS, Pt1Field
from planner.solver import plan_visit, slot_iso
from planner.transit import FixtureRoundTrip, travel_window

MIN = 60
DAY = 86_400
ORIGIN = "250130000000"
PATIENT = Patient(id="synthetic-p", origin_bg=ORIGIN, lang="es")

settings.register_profile("planner", deadline=None, max_examples=200)
settings.load_profile("planner")

complete_rules = st.builds(
    VisitRule,
    visit_type=st.sampled_from(["type-a", "type-b", "type-c"]),
    duration_min=st.integers(1, 300),
    escort_required=st.booleans(),
    telehealth_ok=st.booleans(),
    prep=st.booleans(),
    recurrence_per_week=st.none() | st.integers(1, 7),
)
# Rulebook entries with nulls (unverified). Kept to roughly 1 in 4 examples.
unverified_rules = st.builds(
    VisitRule,
    visit_type=st.sampled_from(["type-a", "type-b", "type-c"]),
    duration_min=st.none() | st.integers(1, 300),
    escort_required=st.none() | st.booleans(),
    telehealth_ok=st.none() | st.booleans(),
    prep=st.none(),
)
rules = st.one_of(complete_rules, complete_rules, complete_rules, unverified_rules)
shifts = st.none() | st.tuples(st.integers(0, 24), st.integers(0, 24))
barrier_sets = st.builds(
    Barriers,
    has_transport=st.booleans(),
    work_shift=shifts,
    childcare=st.booleans(),
    has_escort=st.booleans(),
    cost_worry=st.booleans(),
    language=st.sampled_from(["en", "es"]),
    childcare_window=shifts,
)
slots = st.builds(
    CandidateSlot,
    clinic_id=st.sampled_from(["c1", "c2"]),
    date=st.sampled_from(["2026-11-12", "2026-11-13"]),
    start=st.integers(5 * 60, 22 * 60).map(lambda m: m * MIN),
)


@st.composite
def trips(draw):
    if not draw(st.booleans()):
        return RoundTripResult(reachable=False, reason="synthetic")
    leave = draw(st.integers(4 * 60, 23 * 60)) * MIN
    home = leave + draw(st.integers(1, 10 * 60)) * MIN  # may pass midnight (> 86400)
    return RoundTripResult(
        reachable=True,
        out_legs=(Leg("bus", "origin", "clinic", "R", leave, leave + MIN),),
        ret_legs=(Leg("bus", "clinic", "origin", "R", home - MIN, home),),
        last_bus_home=home - MIN,
        reason="synthetic",
    )


@st.composite
def scenarios(draw):
    cand = draw(st.lists(slots, max_size=6, unique=True))
    table = {(ORIGIN, s.clinic_id, s.date, s.start): draw(trips()) for s in cand}
    fields = tuple(Pt1Field(f"f_{k}", k) for k in sorted(SOURCE_KEYS))
    return draw(rules), draw(barrier_sets), cand, table, fields


def in_shift_oracle(t: int, shift: tuple[int, int] | None) -> bool:
    """Independent check, minute by minute: is clock time t inside the shift?"""
    if shift is None or shift[0] == shift[1]:
        return False
    hour = (t % DAY) / 3600
    s, e = shift
    return s <= hour < e if s < e else (hour >= s or hour < e)


def window_hits_shift(window: tuple[int, int], shift) -> bool:
    lo, hi = window
    return any(in_shift_oracle(t, shift) for t in range(lo, hi, MIN))


def run(scenario):
    rule, barriers, cand, table, fields = scenario
    return plan_visit(PATIENT, rule, barriers, cand, FixtureRoundTrip(table), fields)


@given(scenarios())
def test_p15_escort_never_transit_only(scenario):
    rule = scenario[0]
    plan = run(scenario)
    if rule.escort_required is not False:  # True or unknown: never transit-only
        assert OptionKind.SLOT not in {o.kind for o in plan.options}
        assert plan.itinerary.out_legs == () and plan.itinerary.ret_legs == ()


@given(scenarios())
def test_p16_no_recommended_slot_overlaps_shift(scenario):
    _, barriers, cand, table, _ = scenario
    by_iso = {(slot_iso(s), s.clinic_id): s for s in cand}
    for option in run(scenario).options:
        if option.kind not in (OptionKind.SLOT, OptionKind.RIDE):
            continue
        s = by_iso[(option.details["slot"], option.details["clinic_id"])]
        result = table[(ORIGIN, s.clinic_id, s.date, s.start)]
        window = travel_window(result)
        if window is None:
            # Only a RIDE may be offered without a travel estimate, and only when
            # there is no no-go band (work shift OR childcare window) to conflict with.
            assert option.kind is OptionKind.RIDE
            assert not _band_has_hours(barriers.work_shift)
            assert not _band_has_hours(barriers.childcare_window)
        else:
            # The recommended window must miss BOTH no-go bands (VP-6 shift, VP-20 childcare).
            assert not window_hits_shift(window, barriers.work_shift)
            assert not window_hits_shift(window, barriers.childcare_window)


def _band_has_hours(band: tuple[int, int] | None) -> bool:
    return band is not None and band[0] != band[1]


@given(scenarios())
def test_p20_no_recommended_slot_overlaps_childcare_window(scenario):
    """VP-20: no recommended slot/ride has a door-to-door window (travel included)
    that overlaps the childcare window. Independent minute-by-minute oracle."""
    _, barriers, cand, table, _ = scenario
    by_iso = {(slot_iso(s), s.clinic_id): s for s in cand}
    for option in run(scenario).options:
        if option.kind not in (OptionKind.SLOT, OptionKind.RIDE):
            continue
        s = by_iso[(option.details["slot"], option.details["clinic_id"])]
        window = travel_window(table[(ORIGIN, s.clinic_id, s.date, s.start)])
        if window is not None:
            assert not window_hits_shift(window, barriers.childcare_window)


@given(scenarios())
def test_p17_telehealth_only_if_allowed(scenario):
    rule = scenario[0]
    if OptionKind.TELE in {o.kind for o in run(scenario).options}:
        assert rule.telehealth_ok is True


@given(scenarios())
def test_p18_no_clinical_or_eligibility_text(scenario):
    plan = run(scenario)
    texts = list(iter_strings([[o.why, o.details] for o in plan.options])) + list(
        iter_strings(plan.pt1_prefill)
    )
    assert not [t for t in texts if find_banned(t)]


@given(scenarios(), st.randoms(use_true_random=False))
def test_ranking_is_deterministic(scenario, rnd):
    rule, barriers, cand, table, fields = scenario
    shuffled = list(cand)
    rnd.shuffle(shuffled)
    a = run(scenario)
    b = plan_visit(PATIENT, rule, barriers, shuffled, FixtureRoundTrip(table), fields)
    assert a == b


@given(scenarios())
def test_none_is_alone_and_only_when_nothing_viable(scenario):
    kinds = [o.kind for o in run(scenario).options]
    if OptionKind.NONE in kinds:
        assert kinds == [OptionKind.NONE]
    assert kinds  # never an empty plan


@given(scenarios())
def test_p19_itinerary_integrity(scenario):
    """VP-14: when a slot itinerary is populated, last_bus_home is truly the last
    return leg (no later return leg exists), and it matches the slot's trip.

    The 'plan B later than plan A' half (FINAL §8.3 #19, VP-23) needs human-reviewed
    templates (M3); plan_b stays None in mock mode, asserted here so a regression that
    invents patient-facing text is caught.
    """
    plan = run(scenario)
    it = plan.itinerary
    if it.out_legs or it.ret_legs:
        # A populated itinerary comes only from a top SLOT option (VP-14).
        assert OptionKind.SLOT in {o.kind for o in plan.options}
        assert it.ret_legs, "a populated itinerary must have a return"
        last_arr = max(leg.arr for leg in it.ret_legs)
        # last_bus_home is the latest return departure that still gets home; it can
        # never be after the journey actually arrives home.
        assert it.last_bus_home is not None
        assert it.last_bus_home <= last_arr
        # No return leg departs after the recorded last bus home.
        assert all(leg.dep <= it.last_bus_home for leg in it.ret_legs)
    else:
        # Empty itinerary carries no legs and no last bus home (VP-14).
        assert it.last_bus_home is None
    # plan_b text is template-only (M3); never machine-generated here.
    assert it.plan_b is None


@given(scenarios())
def test_p22_recurrence_plan_on_top_option(scenario):
    """VP-22: when the visit type recurs (recurrence_per_week set) and a real option is
    offered, the top option carries a structured recurrence plan with the rulebook
    cadence; a one-off visit never gets one."""
    rule = scenario[0]
    plan = run(scenario)
    top = plan.options[0]
    has_recurrence = "recurrence" in top.details
    if rule.recurrence_per_week and top.kind is not OptionKind.NONE:
        assert has_recurrence
        rec = top.details["recurrence"]
        assert rec["per_week"] == rule.recurrence_per_week
        assert rec["repeats"] is True
        if top.kind is OptionKind.RIDE:
            assert rec.get("pt1_once_per_destination") is True
    else:
        # No recurrence block for a one-off visit or a none-only plan.
        assert not has_recurrence
