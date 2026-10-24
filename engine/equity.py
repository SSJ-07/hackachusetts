"""90% confidence intervals for the /audit equity splits (owner: M3).

The equity numbers rest on ACS 5-year ESTIMATES, which carry sampling error. This
module carries the published 90% margins of error (MOE) through every step of the
car-less-adult estimate to a 90% interval on each group's reachable share.

Method: U.S. Census Bureau, "Understanding and Using American Community Survey Data:
What All Data Users Need to Know" (2020), ch. 8, "Calculating Measures of Error for
Derived Estimates". With MOE_x the published 90% margin of x:

    sum / difference  A = Σ a_i          MOE_A = sqrt(Σ MOE_i²)
    proportion        p = X / Y (X ⊆ Y)  MOE_p = sqrt(MOE_X² − p²·MOE_Y²) / Y
                      (if the radicand is negative, use the ratio formula with +)
    product           C = A · B          MOE_C = sqrt(A²·MOE_B² + B²·MOE_A²)
    90% interval      [x − MOE_x, x + MOE_x], clipped to the valid range

Assumption (as in the handbook): errors in different block groups / tables are
independent. Covariance is ignored, so intervals are approximations, not exact.

Per block group (mirrors pipeline/build_origins.py):
    adults  A = P − U                 (P = B01003_001, U = under-18 cells of B01001)
    zero-vehicle share  s = Z / H     (Z = B25044_003 + _010, H = B25044_001)
    carless adults      C = A · s
    lep_pct  l = L / T                (C16002 limited-English / all households)
    age65_pct q = S / P               (B01001 65+ cells / total pop)
Group weight w = C (zero_veh), C·ej, C·l (lep), C·q (age65); reachable share of a group
= Σ f·w / Σ w with f = fraction of the clinic's hours a block group is reachable (exact,
from the cube). Only w carries sampling error.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ACS_EST_PATH = ROOT / "data" / "raw" / "acs_bg.csv"
ACS_MOE_PATH = ROOT / "data" / "raw" / "acs_bg_moe.csv"

HH_TOTAL = "B25044_001"
HH_ZERO_VEH = ["B25044_003", "B25044_010"]
POP_TOTAL = "B01003_001"
UNDER_18 = [f"B01001_{i:03d}" for i in (3, 4, 5, 6, 27, 28, 29, 30)]
AGE_65PLUS = [f"B01001_{i:03d}" for i in list(range(20, 26)) + list(range(44, 50))]
LEP_TOTAL = "C16002_001"
LEP_LIMITED = ["C16002_004", "C16002_007", "C16002_010", "C16002_013"]
TABLES = [HH_TOTAL, *HH_ZERO_VEH, POP_TOTAL, *UNDER_18, *AGE_65PLUS, LEP_TOTAL, *LEP_LIMITED]

GROUPS = ("ej", "lep", "age65", "zero_veh")
MOE_COLUMNS = ("carless_adults_moe", "lep_pct_moe", "age65_pct_moe")


# --------------------------------------------------------------------------- #
# Census formulas (scalars; numpy-friendly)
# --------------------------------------------------------------------------- #
def moe_sum(*moes: float) -> float:
    return math.sqrt(sum(m * m for m in moes))


def moe_proportion(x: float, y: float, moe_x: float, moe_y: float) -> float:
    """MOE of p = x/y where x is a subset of y. Falls back to the ratio form (Census rule)."""
    if y <= 0:
        return 0.0
    p = x / y
    a, b = moe_x * moe_x, p * p * moe_y * moe_y
    rad = a - b
    # Exact cancellation (e.g. a one-block-group share, where moe_x = p·moe_y) leaves
    # only float noise either side of 0; that is 0, not a case for the ratio fallback.
    if abs(rad) <= 1e-9 * max(a, b):
        rad = 0.0
    if rad < 0:
        rad = a + b
    return math.sqrt(rad) / y


def moe_product(a: float, b: float, moe_a: float, moe_b: float) -> float:
    return math.sqrt(a * a * moe_b * moe_b + b * b * moe_a * moe_a)


def interval(value: float, moe: float, lo: float = 0.0, hi: float = 1.0) -> tuple[float, float]:
    """90% interval value ± moe, clipped to [lo, hi]. Always contains `value` when lo<=value<=hi."""
    return max(lo, value - moe), min(hi, value + moe)


def _clean_moe(v: float) -> float:
    # ACS annotation codes are large negatives; -555555555 = "controlled, no sampling
    # error" (0). Any other negative = MOE not available: treated as 0 and counted.
    return float(v) if v >= 0 else 0.0


# --------------------------------------------------------------------------- #
# per block group
# --------------------------------------------------------------------------- #
def bg_moe(est: pd.DataFrame, moe: pd.DataFrame) -> pd.DataFrame:
    """Per-block-group estimates + 90% MOE for carless_adults, lep_pct, age65_pct.

    est / moe: indexed by bg_geoid, columns = TABLES (estimate / MOE values).
    """
    rows = []
    for geoid in est.index:
        e = est.loc[geoid]
        m = moe.loc[geoid] if geoid in moe.index else pd.Series(0.0, index=TABLES)
        mm = {k: _clean_moe(m[k]) for k in TABLES}
        missing = sum(1 for k in TABLES if m[k] < 0)

        P, moe_P = float(e[POP_TOTAL]), mm[POP_TOTAL]
        U = float(sum(e[k] for k in UNDER_18))
        moe_U = moe_sum(*(mm[k] for k in UNDER_18))
        A_raw = P - U
        A = max(A_raw, 0.0)
        moe_A = moe_sum(moe_P, moe_U)

        H, moe_H = float(e[HH_TOTAL]), mm[HH_TOTAL]
        Z = float(sum(e[k] for k in HH_ZERO_VEH))
        moe_Z = moe_sum(*(mm[k] for k in HH_ZERO_VEH))
        s = Z / H if H > 0 else 0.0
        moe_s = moe_proportion(Z, H, moe_Z, moe_H)

        C = A * s
        moe_C = moe_product(A, s, moe_A, moe_s)

        T, moe_T = float(e[LEP_TOTAL]), mm[LEP_TOTAL]
        L = float(sum(e[k] for k in LEP_LIMITED))
        moe_L = moe_sum(*(mm[k] for k in LEP_LIMITED))
        lep = L / T if T > 0 else 0.0
        moe_lep = moe_proportion(L, T, moe_L, moe_T)

        S = float(sum(e[k] for k in AGE_65PLUS))
        moe_S = moe_sum(*(mm[k] for k in AGE_65PLUS))
        q = S / P if P > 0 else 0.0
        moe_q = moe_proportion(S, P, moe_S, moe_P)

        rows.append({
            "bg_geoid": str(geoid), "carless_adults_est": C, "carless_adults_moe": moe_C,
            "lep_pct_est": lep, "lep_pct_moe": moe_lep, "age65_pct_est": q, "age65_pct_moe": moe_q,
            "moe_missing": missing,
        })
    return pd.DataFrame(rows)


def _read_acs(path: Path, suffix: str) -> pd.DataFrame:
    with path.open(encoding="utf-8") as f:
        recs = list(csv.DictReader(f))
    data = {r["GEOID"]: {t: float(r[t + suffix]) for t in TABLES} for r in recs}
    return pd.DataFrame.from_dict(data, orient="index")


def load_bg_moe(est_path: Path = ACS_EST_PATH, moe_path: Path = ACS_MOE_PATH) -> pd.DataFrame | None:
    """Per-block-group MOE frame, or None when the MOE file is absent (CI has no data/raw)."""
    if not (est_path.is_file() and moe_path.is_file()):
        return None
    return bg_moe(_read_acs(est_path, "E"), _read_acs(moe_path, "M"))


# --------------------------------------------------------------------------- #
# group intervals
# --------------------------------------------------------------------------- #
def share_ci(w: list[float], w_moe: list[float], f: list[float]) -> dict[str, Any]:
    """Reachable share R/N with R = Σ f·w, N = Σ w, and its 90% interval.

    f in [0, 1] is exact (from the cube); only w carries sampling error. R is part of N,
    so the proportion formula applies (with the Census ratio fallback).
    """
    n = float(sum(w))
    if n <= 0:
        return {"share": 0.0, "lo": 0.0, "hi": 0.0, "moe": 0.0, "n": 0}
    r = float(sum(fi * wi for fi, wi in zip(f, w)))
    moe_r = math.sqrt(sum((fi * mi) ** 2 for fi, mi in zip(f, w_moe)))
    moe_n = math.sqrt(sum(mi * mi for mi in w_moe))
    share = min(max(r / n, 0.0), 1.0)
    # A share's margin above 1 says nothing more than "anywhere in [0, 1]"; cap it so a
    # tiny group (n << 1) cannot emit an infinite or absurd MOE.
    moe = min(moe_proportion(r, n, moe_r, moe_n), 1.0)
    lo, hi = interval(share, moe)
    return {"share": share, "lo": lo, "hi": hi, "moe": moe, "n": int(round(n))}


def group_weights(origins: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    """(weight, weight MOE) per equity group, from origins joined with bg MOE columns."""
    C, mC = origins.carless_adults.astype(float), origins.carless_adults_moe.astype(float)
    ej = origins.ej_flag.astype(bool).astype(float)
    l, ml = origins.lep_pct.astype(float), origins.lep_pct_moe.astype(float)
    q, mq = origins.age65_pct.astype(float), origins.age65_pct_moe.astype(float)
    prod = lambda a, b, ma, mb: ((a * mb) ** 2 + (b * ma) ** 2) ** 0.5  # noqa: E731
    return {
        "ej": (C * ej, mC * ej),
        "lep": (C * l, prod(C, l, mC, ml)),
        "age65": (C * q, prod(C, q, mC, mq)),
        "zero_veh": (C, mC),
    }


def equity_ci(reach_frac: dict[str, float], origins: pd.DataFrame) -> dict[str, dict[str, Any]] | None:
    """90% CI for every equity group. reach_frac: bg_geoid -> fraction of hours reachable.

    Returns None when origins carries no MOE columns (MOE data not built)."""
    if not all(c in origins.columns for c in MOE_COLUMNS):
        return None
    f = [float(reach_frac.get(bg, 0.0)) for bg in origins.bg_geoid]
    return {
        g: share_ci(list(w), list(m), f)
        for g, (w, m) in group_weights(origins).items()
    }
