"""Properties for engine/equity.py: 90% intervals from ACS margins of error (M3)."""

from __future__ import annotations

import math

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from engine import audit as engine_audit
from engine.equity import (
    equity_ci,
    interval,
    moe_product,
    moe_proportion,
    moe_sum,
    share_ci,
)

settings.register_profile("equity", deadline=None, max_examples=300)
settings.load_profile("equity")

counts = st.floats(0, 5_000, allow_nan=False)
moes = st.floats(0, 2_000, allow_nan=False)
fracs = st.floats(0, 1, allow_nan=False)


@st.composite
def groups(draw):
    k = draw(st.integers(1, 12))
    w = draw(st.lists(counts, min_size=k, max_size=k))
    m = draw(st.lists(moes, min_size=k, max_size=k))
    f = draw(st.lists(fracs, min_size=k, max_size=k))
    return w, m, f


@given(groups())
def test_every_interval_contains_its_point_estimate(g):
    r = share_ci(*g)
    assert r["lo"] <= r["share"] <= r["hi"]


@given(groups())
def test_interval_is_a_valid_share_range(g):
    r = share_ci(*g)
    assert 0.0 <= r["lo"] <= r["hi"] <= 1.0
    assert r["moe"] >= 0 and math.isfinite(r["moe"])


@given(groups())
def test_zero_margins_give_a_point_interval(g):
    w, _, f = g
    r = share_ci(w, [0.0] * len(w), f)
    assert r["lo"] == r["share"] == r["hi"] and r["moe"] == 0


@given(groups(), st.floats(1.0, 10.0))
def test_more_sampling_error_never_narrows_the_interval(g, k):
    w, m, f = g
    narrow, wide = share_ci(w, m, f), share_ci(w, [x * k for x in m], f)
    # scaling every MOE by k scales the radicand by k²; allow float noise near 0
    assert wide["moe"] >= narrow["moe"] - 1e-6 or wide["moe"] == 1.0


# ACS counts are whole numbers (0 or >= 1)
acs_counts = st.integers(0, 5_000).map(float)


@given(acs_counts, acs_counts, moes, moes)
def test_proportion_moe_is_nonnegative_and_finite(x, y, mx, my):
    v = moe_proportion(min(x, y), y, mx, my)
    assert v >= 0 and math.isfinite(v)


@given(st.floats(-1, 2, allow_nan=False), moes)
def test_interval_clips_but_keeps_valid_estimate(v, m):
    lo, hi = interval(v, m)
    assert 0 <= lo and hi <= 1
    if 0 <= v <= 1:
        assert lo <= v <= hi


def test_one_block_group_share_has_no_sampling_error():
    # numerator and denominator are the same estimate: the share is exact
    for m in (1105.8426807682297, 142.89509757797907, 7.0):
        assert share_ci([1.0], [m], [0.75])["moe"] < 1e-6


def test_handbook_formulas():
    # sum: sqrt(3² + 4²) = 5
    assert moe_sum(3, 4) == 5
    # proportion: p = 20/100, sqrt(10² − 0.04·20²)/100 = sqrt(84)/100
    assert math.isclose(moe_proportion(20, 100, 10, 20), math.sqrt(84) / 100)
    # radicand < 0 -> ratio form with +
    assert math.isclose(moe_proportion(50, 100, 1, 50), math.sqrt(1 + 0.25 * 2500) / 100)
    # product: sqrt(10²·2² + 5²·3²)
    assert math.isclose(moe_product(10, 5, 3, 2), math.sqrt(400 + 225))


# ---------------------------------------------------------------- integration
def _toy():
    origins = pd.DataFrame({
        "bg_geoid": ["a", "b", "c"], "lat": [0, 0, 0], "lon": [0, 0, 0],
        "carless_adults": [100, 50, 10], "pop": [500, 300, 80], "ej_flag": [True, False, True],
        "lep_pct": [0.2, 0.1, 0.0], "age65_pct": [0.3, 0.1, 0.5],
        "carless_adults_moe": [40.0, 30.0, 12.0], "lep_pct_moe": [0.1, 0.05, 0.02],
        "age65_pct_moe": [0.08, 0.04, 0.2],
    })
    rows = []
    for hour in (8, 9, 10):
        for bg, ok in (("a", hour != 9), ("b", True), ("c", False)):
            rows.append({"clinic_id": "X", "visit_type": "t", "day": "mon", "hour": hour,
                         "bg_geoid": bg, "reachable": ok, "reason": ""})
    return pd.DataFrame(rows), origins


def test_audit_ci_shares_equal_the_equity_shares():
    cube, origins = _toy()
    r = engine_audit.audit(cube, origins, "X", "all", "mon")
    for g in ("ej", "lep", "age65", "zero_veh"):
        assert math.isclose(r["equity_ci"][g]["share"], r["equity"][g]["share"], abs_tol=1e-12)
        assert r["equity_ci"][g]["n"] == r["equity"][g]["n"]
        assert r["equity_ci"][g]["lo"] <= r["equity_ci"][g]["share"] <= r["equity_ci"][g]["hi"]


def test_no_moe_columns_means_null_ci():
    cube, origins = _toy()
    plain = origins.drop(columns=["carless_adults_moe", "lep_pct_moe", "age65_pct_moe"])
    assert engine_audit.audit(cube, plain, "X", "all", "mon")["equity_ci"] is None
    assert equity_ci({}, plain) is None
