"""Schedule-optimizer correctness properties (Hypothesis). All cubes are synthetic.

SO-8  never-worse: suggested score >= baseline; blocks stay within open hours and
      the block count is preserved.
SO-5  same number of blocks.
SO-4  respects open hours.
SO-11 deterministic: same inputs -> identical ranked list, order-independent.
SO-14 monotone in access: flipping some (bg,hour) false->true never lowers the score.
SO-13 greedy >= (1 - 1/e) * CP-SAT optimum on tiny instances.
"""

from __future__ import annotations

import math

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from engine import optimizer as opt

settings.register_profile("optimizer", deadline=None, max_examples=150)
settings.load_profile("optimizer")

UNIT_WEIGHTS = {"default": 1.0, "weights": {}, "source": "test", "vintage": "test"}
ONE_MINUS_INV_E = 1.0 - 1.0 / math.e

HOURS = list(range(7, 13))  # 7..12, tiny universe so CP-SAT is instant
BGS = ["a", "b", "c"]


def _cube_from_matrix(reach: dict[int, dict[str, bool]], clinic="C", day="mon",
                      visit_type="colonoscopy") -> pd.DataFrame:
    rows = [{"clinic_id": clinic, "visit_type": visit_type, "day": day, "hour": int(h),
             "bg_geoid": bg, "reachable": bool(v), "reason": ""}
            for h, bgs in reach.items() for bg, v in bgs.items()]
    df = pd.DataFrame(rows)
    df["bg_geoid"] = df["bg_geoid"].astype(str)
    df["hour"] = df["hour"].astype(int)
    df["reachable"] = df["reachable"].astype(bool)
    return df


def _origins(ca: dict[str, int], ej: dict[str, bool]) -> pd.DataFrame:
    rows = [{"bg_geoid": bg, "lat": 42.0, "lon": -72.0, "carless_adults": ca[bg],
             "pop": ca[bg] * 2, "ej_flag": ej[bg], "lep_pct": 0.1, "age65_pct": 0.1}
            for bg in ca]
    df = pd.DataFrame(rows)
    df["bg_geoid"] = df["bg_geoid"].astype(str)
    return df


# a reachability matrix over HOURS x BGS, carless adults, ej flags, baseline blocks
@st.composite
def instance(draw):
    reach = {h: {bg: draw(st.booleans()) for bg in BGS} for h in HOURS}
    ca = {bg: draw(st.integers(1, 50)) for bg in BGS}
    ej = {bg: draw(st.booleans()) for bg in BGS}
    n_blocks = draw(st.integers(1, 3))
    blocks = tuple(sorted(draw(st.sampled_from(HOURS)) for _ in range(n_blocks)))
    blocks = tuple(sorted(set(blocks)))  # dedupe (no overlap in baseline)
    k = draw(st.integers(0, 3))
    return reach, ca, ej, list(blocks), k


@given(instance())
def test_never_worse_and_constraints(inst):
    reach, ca, ej, blocks, k = inst
    cube = _cube_from_matrix(reach)
    origins = _origins(ca, ej)
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=k,
                             weights=UNIT_WEIGHTS, baseline_blocks=blocks)
    # SO-8 never worse
    assert r["suggested_score"] >= r["baseline_score"] - 1e-9
    # SO-5 same number of blocks
    assert len(r["suggested_blocks"]) == len(blocks)
    # SO-4 within open hours (cube-default range here)
    allowed = set(r["open_hours"])
    assert all(h in allowed for h in r["suggested_blocks"])
    # SO-6 no overlap
    assert len(set(r["suggested_blocks"])) == len(r["suggested_blocks"])
    # SO-9 at most k changes
    assert len(r["changes"]) <= k


@given(instance())
def test_deterministic_and_order_independent(inst):
    reach, ca, ej, blocks, k = inst
    cube = _cube_from_matrix(reach)
    origins = _origins(ca, ej)
    r1 = opt.suggest_schedule(cube, origins, "C", "mon", k=k,
                              weights=UNIT_WEIGHTS, baseline_blocks=blocks)
    # shuffle the cube rows and the origins rows -> must not change the result (SO-11)
    cube2 = cube.sample(frac=1.0, random_state=7).reset_index(drop=True)
    origins2 = origins.sample(frac=1.0, random_state=13).reset_index(drop=True)
    r2 = opt.suggest_schedule(cube2, origins2, "C", "mon", k=k,
                              weights=UNIT_WEIGHTS, baseline_blocks=blocks)
    assert [c["change"] for c in r1["changes"]] == [c["change"] for c in r2["changes"]]
    assert r1["suggested_blocks"] == r2["suggested_blocks"]


@given(instance(), st.integers(0, len(HOURS) * len(BGS)))
def test_monotone_in_access(inst, flips):
    # Flip some (hour,bg) cells from False->True; baseline score must not decrease (SO-14).
    reach, ca, ej, blocks, k = inst
    base_cube = _cube_from_matrix(reach)
    origins = _origins(ca, ej)
    m0 = opt.ScoreModel(base_cube, origins, "C", "mon", weights=UNIT_WEIGHTS)
    s0 = m0.score(blocks)

    # produce an improved matrix: turn up to `flips` False cells into True
    cells = [(h, bg) for h in HOURS for bg in BGS if not reach[h][bg]]
    cells = cells[:flips]
    reach2 = {h: dict(reach[h]) for h in HOURS}
    for h, bg in cells:
        reach2[h][bg] = True
    m1 = opt.ScoreModel(_cube_from_matrix(reach2), origins, "C", "mon", weights=UNIT_WEIGHTS)
    s1 = m1.score(blocks)
    assert s1 >= s0 - 1e-9


@given(instance())
def test_greedy_coverage_within_one_minus_inv_e_of_exact(inst):
    # SO-13: the (1-1/e) bound is a theorem for the ADDITIVE coverage formulation
    # "open k hours to maximize sum cell(h)" (monotone submodular), NOT for swaps.
    reach, ca, ej, blocks, k = inst
    cube = _cube_from_matrix(reach)
    origins = _origins(ca, ej)
    model = opt.ScoreModel(cube, origins, "C", "mon", weights=UNIT_WEIGHTS)
    model.baseline_blocks = tuple(blocks)
    allowed_list, _ = opt.open_hours("C", "mon", model.cube_hours)
    allowed = set(allowed_list)
    kk = max(1, k)  # the bound is about selecting kk hours; kk>=1
    g = opt.greedy_select_hours(model, allowed, kk)
    ex = opt.exact_select_hours(model, allowed, kk)
    assert g["score"] <= ex["score"] + 1e-9           # greedy never beats exact
    if ex["score"] > 1e-9:
        assert g["score"] >= ONE_MINUS_INV_E * ex["score"] - 1e-6


@given(instance())
def test_swap_optimizer_never_exceeds_its_own_optimum(inst):
    # the product swap path never beats the exact swap optimum under the same k.
    reach, ca, ej, blocks, k = inst
    cube = _cube_from_matrix(reach)
    origins = _origins(ca, ej)
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=k,
                             weights=UNIT_WEIGHTS, baseline_blocks=blocks)
    model = opt.ScoreModel(cube, origins, "C", "mon", weights=UNIT_WEIGHTS)
    model.baseline_blocks = tuple(blocks)
    allowed_list, _ = opt.open_hours("C", "mon", model.cube_hours)
    exact = opt.solve_exact(model, set(allowed_list), k=k)
    assert r["suggested_score"] <= exact["score"] + 1e-6
    # exact (with k moves allowed, 0 moves feasible) is at least the baseline.
    assert exact["score"] >= r["baseline_score"] - 1e-9
