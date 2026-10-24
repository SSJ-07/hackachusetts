"""Build data/cache/origins.parquet (the block-group origins table).

Run from the repo root:   python pipeline/build_origins.py

Joins three raw sources that scripts/get_data.py already downloaded:
  * ACS 2024 5-year  (data/raw/acs_bg.csv)        -> car-less adults, population, age 65+, limited-English
  * MassGIS EJ 2020  (data/raw/ej_west.json)      -> environmental-justice flag
  * TIGER 2024 BG    (data/raw/tiger_bg/*.dbf)     -> interior point lat/lon per block group

Output columns (see docs/contracts.md -> origins.parquet):
  bg_geoid, lat, lon, carless_adults, pop, ej_flag, lep_pct, age65_pct

METHOD NOTES (also written to docs/methods.md):
  * carless_adults is an ESTIMATE. ACS B25044 counts *households* with no vehicle,
    not adults. We scale adults (18+) by the zero-vehicle household share:
        carless_adults = adults_18plus * (zero_vehicle_hh / all_hh)
  * lat/lon use TIGER's interior point (INTPTLAT/INTPTLON), an honest MVP substitute
    for a true population-weighted centroid.
Uses pandas + pyarrow (parquet) + pyshp (reads the TIGER .dbf without geometry).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import shapefile  # pyshp

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache"
ACS_CSV = RAW / "acs_bg.csv"
EJ_JSON = RAW / "ej_west.json"
TIGER_SHP = RAW / "tiger_bg" / "tl_2024_25_bg.shp"
OUT = CACHE / "origins.parquet"

# ACS variable groups ------------------------------------------------------
# B25044: vehicles available by tenure. _001 = all households,
# _003 = owner-occupied with no vehicle, _010 = renter-occupied with no vehicle.
HH_TOTAL = "B25044_001E"
HH_ZERO_VEH = ["B25044_003E", "B25044_010E"]

POP_TOTAL = "B01003_001E"

# B01001: sex by age. Under-18 male (_003.._006) + female (_027.._030).
UNDER_18 = [f"B01001_{i:03d}E" for i in (3, 4, 5, 6, 27, 28, 29, 30)]
# 65+ male (_020.._025) + female (_044.._049).
AGE_65PLUS = [f"B01001_{i:03d}E" for i in list(range(20, 26)) + list(range(44, 50))]

# C16002: household language. _001 = all households; the _004/_007/_010/_013
# cells are the "limited English speaking household" sub-bins per language group.
LEP_TOTAL = "C16002_001E"
LEP_LIMITED = ["C16002_004E", "C16002_007E", "C16002_010E", "C16002_013E"]


def load_acs() -> pd.DataFrame:
    df = pd.read_csv(ACS_CSV, dtype={"GEOID": str})
    # Every ACS value column is numeric; coerce (Census uses negative codes for
    # missing/annotations, but these block-group count tables are clean).
    value_cols = [c for c in df.columns if c.endswith("E")]
    df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    adults = (df[POP_TOTAL] - df[UNDER_18].sum(axis=1)).clip(lower=0)
    zero_veh_hh = df[HH_ZERO_VEH].sum(axis=1)
    all_hh = df[HH_TOTAL].replace(0, pd.NA)  # avoid divide-by-zero
    zero_veh_share = (zero_veh_hh / all_hh).fillna(0.0)

    out = pd.DataFrame({
        "bg_geoid": df["GEOID"],
        "pop": df[POP_TOTAL].round().astype(int),
        # ESTIMATE: adults scaled by the zero-vehicle household share.
        "carless_adults": (adults * zero_veh_share).round().astype(int),
        "age65_pct": (df[AGE_65PLUS].sum(axis=1) / df[POP_TOTAL].replace(0, pd.NA)).fillna(0.0),
        "lep_pct": (df[LEP_LIMITED].sum(axis=1) / df[LEP_TOTAL].replace(0, pd.NA)).fillna(0.0),
    })
    return out


def load_ej() -> set[str]:
    """Return the set of GEOIDs flagged as Environmental Justice block groups."""
    d = json.loads(EJ_JSON.read_text(encoding="utf-8"))
    flagged = set()
    for feat in d.get("features", []):
        a = feat["attributes"]
        if str(a.get("EJ", "")).strip().lower() == "yes":
            flagged.add(str(a["GEOID"]))
    return flagged


def load_tiger_points() -> pd.DataFrame:
    """Read GEOID + interior point (lat/lon) from the TIGER .dbf, no geometry needed."""
    r = shapefile.Reader(str(TIGER_SHP))
    field_names = [f[0] for f in r.fields[1:]]  # skip the DeletionFlag field
    gi = field_names.index("GEOID")
    lat_i = field_names.index("INTPTLAT")
    lon_i = field_names.index("INTPTLON")
    rows = []
    for rec in r.iterRecords():
        rows.append((str(rec[gi]), float(rec[lat_i]), float(rec[lon_i])))
    return pd.DataFrame(rows, columns=["bg_geoid", "lat", "lon"])


def main() -> None:
    acs = load_acs()
    ej = load_ej()
    tiger = load_tiger_points()

    df = acs.merge(tiger, on="bg_geoid", how="left")
    missing_pts = df["lat"].isna().sum()
    if missing_pts:
        raise SystemExit(f"ERROR: {missing_pts} ACS block groups had no TIGER match. "
                         "GEOID mismatch between ACS and TIGER.")

    df["ej_flag"] = df["bg_geoid"].isin(ej)

    df = df[["bg_geoid", "lat", "lon", "carless_adults", "pop",
             "ej_flag", "lep_pct", "age65_pct"]]
    df = df.sort_values("bg_geoid").reset_index(drop=True)

    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)

    print(f"[ ok ] wrote {OUT.relative_to(ROOT)}: {len(df)} block groups")
    print(f"       EJ block groups:       {int(df['ej_flag'].sum())}")
    print(f"       total car-less adults: {int(df['carless_adults'].sum()):,}")
    print(f"       total population:      {int(df['pop'].sum()):,}")
    print(f"       lat range: {df['lat'].min():.4f}..{df['lat'].max():.4f}  "
          f"lon range: {df['lon'].min():.4f}..{df['lon'].max():.4f}")


if __name__ == "__main__":
    main()
