"""Rural lens: the "no option at all" verdict per block group (GET /rural).

The cube answers "can a car-less adult in this block group reach a clinic hour by bus
and get home?". It cannot say what a town with NO bus has instead — dial-a-ride,
Council on Aging drivers, MassHealth PT-1 — or that it has nothing. The hand-collected
rural tables (data/manual/rural_options.csv, rural_coverage.csv; M3, one row per
Franklin/Hampshire town, every row cited) say that. This module joins the two through
data/cache/bg_towns.parquet (pipeline/build_towns.py).

Verdict per block group, in this order:
  transit        some cube cell (any clinic × day × hour) is reachable AND returnable
  assisted_only  no transit cell, but the town has dial-a-ride / COA driver / PT-1
  none           no transit cell and the town's row says has_any_option == FALSE
  not_assessed   no transit cell and the town is not in the rural table (Hampden towns)

Reachability comes ONLY from the cube (engine.round_trip); this module never re-derives
it. Every number carries a source + vintage (sources()).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from engine.audit import NO_STOP_REASON, AuditDataError, sources as audit_sources
from engine.paths import ROOT, cache_dir

RURAL_OPTIONS_PATH = ROOT / "data" / "manual" / "rural_options.csv"
RURAL_COVERAGE_PATH = ROOT / "data" / "manual" / "rural_coverage.csv"

VERDICTS = ("transit", "assisted_only", "none", "not_assessed")
TOWN_COLS = ["town", "county", "coverage_tier", "has_any_option", "dial_a_ride", "coa_driver",
             "pt1", "source_url", "verified_by", "date"]


class RuralDataError(AuditDataError):
    """Requested town has no block groups in the data."""


def towns_path() -> Path:
    return cache_dir() / "bg_towns.parquet"


def load_towns(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_parquet(path or towns_path())
    df["bg_geoid"] = df["bg_geoid"].astype(str)
    return df


def load_coverage(path: Path = RURAL_COVERAGE_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    df["has_any_option"] = df["has_any_option"].str.strip().str.upper() == "TRUE"
    return df


def load_options(path: Path = RURAL_OPTIONS_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("")


def _key(town: str) -> str:
    return town.strip().casefold()


def _bg_transit(cube: pd.DataFrame) -> pd.DataFrame:
    """Per block group over EVERY cube cell: share reachable + 'no stop at all'."""
    if cube.empty:
        return pd.DataFrame(columns=["bg_geoid", "transit_share", "desert"]).set_index("bg_geoid")
    return cube.groupby("bg_geoid").agg(
        transit_share=("reachable", "mean"),
        desert=("reason", lambda r: bool((r == NO_STOP_REASON).all())),
    )


def _verdict(transit_share: float, in_table: bool, has_any_option: bool) -> str:
    if transit_share > 0:
        return "transit"
    if not in_table:
        return "not_assessed"
    return "assisted_only" if has_any_option else "none"


def rural(cube: pd.DataFrame, origins: pd.DataFrame, towns: pd.DataFrame,
          coverage: pd.DataFrame, options: pd.DataFrame, town: str | None = None) -> dict[str, Any]:
    """The full GET /rural payload (optionally for one town)."""
    j = origins[["bg_geoid", "lat", "lon", "carless_adults"]].merge(
        towns[["bg_geoid", "town", "county"]], on="bg_geoid", how="left")
    j["town"] = j["town"].fillna("")
    j["county"] = j["county"].fillna("")
    towns_available = sorted(t for t in j.town.unique() if t)

    if town is not None:
        j = j[j.town.map(_key) == _key(town)]
        if j.empty:
            raise RuralDataError(f"no block groups for town={town!r}")

    cov = coverage.copy()
    cov["town_key"] = cov.town.map(_key)  # itertuples renames _-prefixed columns
    cov_by_town = {r.town_key: r for r in cov.itertuples(index=False)}

    j = j.merge(_bg_transit(cube), left_on="bg_geoid", right_index=True, how="left")
    j["transit_share"] = j["transit_share"].fillna(0.0).clip(0.0, 1.0)
    j["desert"] = j["desert"].fillna(False).astype(bool)

    features = []
    for r in j.itertuples(index=False):
        c = cov_by_town.get(_key(r.town))
        verdict = _verdict(float(r.transit_share), c is not None, bool(c.has_any_option) if c else False)
        features.append({
            "bg_geoid": str(r.bg_geoid), "town": r.town, "county": r.county,
            "lat": float(r.lat), "lon": float(r.lon), "carless_adults": int(r.carless_adults),
            "transit_share": float(r.transit_share), "desert": bool(r.desert),
            "verdict": verdict, "coverage_tier": c.coverage_tier if c else "not_assessed",
        })

    by_verdict = {v: {"n_bg": 0, "carless_adults": 0} for v in VERDICTS}
    for f in features:
        by_verdict[f["verdict"]]["n_bg"] += 1
        by_verdict[f["verdict"]]["carless_adults"] += f["carless_adults"]
    summary = {"n_bg": len(features), "carless_adults": int(sum(f["carless_adults"] for f in features)),
               "by_verdict": by_verdict}

    in_scope = {_key(t) for t in j.town.unique()}
    opts = []
    for r in cov.itertuples(index=False):
        if r.town_key in in_scope:
            opts.append({k: (bool(getattr(r, k)) if k == "has_any_option" else (getattr(r, k) or None))
                         for k in TOWN_COLS})
    opts.sort(key=lambda o: o["town"])

    return {"town": town, "features": features, "summary": summary, "options": opts,
            "towns_available": towns_available, "sources": sources(coverage, options)}


def sources(coverage: pd.DataFrame | None = None, options: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    def _vintage(df: pd.DataFrame | None) -> str:
        if df is None or df.empty or "date" not in df:
            return "unknown"
        dates = [d for d in df["date"].astype(str) if d]
        return max(dates) if dates else "unknown"

    return audit_sources() + [
        {"name": "rural_options.csv (dial-a-ride / COA / PT-1 per town, M3)", "vintage": _vintage(options),
         "url": "https://pvpc.org/wp-content/uploads/2025/05/Franklin-Region-Transportation-Inventory.pdf"},
        {"name": "rural_coverage.csv (coverage tier + has_any_option, derived)", "vintage": _vintage(coverage),
         "url": None},
        {"name": "TIGER/Line 2024 county subdivisions (block group -> town)", "vintage": "2024",
         "url": "https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/"},
    ]
