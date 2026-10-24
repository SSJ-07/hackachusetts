"""Assign every block-group origin to its town — data/cache/bg_towns.parquet.

The rural lens joins the cube (per block group) to the hand-collected rural tables
(per town: dial-a-ride, Council on Aging drivers, PT-1). Nothing in the ACS/TIGER
block-group files names the town, so we point-in-polygon each origin against the
TIGER county-subdivision shapes (MA towns == county subdivisions).

Inputs
  data/cache/origins.parquet               bg_geoid, lat, lon (population-weighted point)
  data/raw/tiger_cousub/tl_2024_25_cousub  TIGER 2024 county subdivisions, MA
  data/raw/ej_west.json                    MassGIS EJ 2020 (MUNICIPALITY) — cross-check only
Output
  data/cache/bg_towns.parquet              bg_geoid, town, town_geoid, county, method

`method` is "polygon" when the point fell inside a town shape, "nearest" when it did
not (a point on a river/boundary edge) and we fell back to the nearest town interior
point. Pure stdlib + pyshp: no shapely, so the ray-casting test is written out here.

Run:  python pipeline/build_towns.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd
import shapefile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.paths import cache_dir  # noqa: E402

RAW = ROOT / "data" / "raw"
COUSUB_SHP = RAW / "tiger_cousub" / "tl_2024_25_cousub.shp"
EJ_JSON = RAW / "ej_west.json"
ORIGINS = cache_dir() / "origins.parquet"
OUT = cache_dir() / "bg_towns.parquet"

COUNTIES = {"011": "Franklin", "013": "Hampden", "015": "Hampshire"}


def normalise_town(name: str) -> str:
    """TIGER names some municipalities 'Agawam Town'; the rural tables say 'Agawam'."""
    name = name.strip()
    for suffix in (" Town", " city", " City"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    """Even-odd ray casting. `ring` is a closed list of (x=lon, y=lat) points."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def shape_rings(shape) -> list[list[tuple[float, float]]]:
    pts = shape.points
    parts = list(shape.parts) + [len(pts)]
    return [pts[parts[k]:parts[k + 1]] for k in range(len(parts) - 1)]


def point_in_shape(lon: float, lat: float, rings) -> bool:
    # Even-odd over every ring handles holes (a hole flips the parity back).
    return sum(point_in_ring(lon, lat, r) for r in rings) % 2 == 1


def load_towns() -> list[dict]:
    r = shapefile.Reader(str(COUSUB_SHP))
    towns = []
    for sr in r.iterShapeRecords():
        rec = sr.record
        if rec["COUNTYFP"] not in COUNTIES:
            continue
        xs = [p[0] for p in sr.shape.points]
        ys = [p[1] for p in sr.shape.points]
        towns.append({
            "town": normalise_town(rec["NAME"]),
            "town_geoid": str(rec["GEOID"]),
            "county": COUNTIES[rec["COUNTYFP"]],
            "rings": shape_rings(sr.shape),
            "bbox": (min(xs), min(ys), max(xs), max(ys)),
            "int_pt": (float(rec["INTPTLON"]), float(rec["INTPTLAT"])),
        })
    return towns


def assign(origins: pd.DataFrame, towns: list[dict]) -> pd.DataFrame:
    rows = []
    for o in origins.itertuples(index=False):
        lon, lat = float(o.lon), float(o.lat)
        hit = None
        for t in towns:
            x0, y0, x1, y1 = t["bbox"]
            if x0 <= lon <= x1 and y0 <= lat <= y1 and point_in_shape(lon, lat, t["rings"]):
                hit = t
                break
        method = "polygon"
        if hit is None:
            method = "nearest"
            hit = min(towns, key=lambda t: math.hypot(t["int_pt"][0] - lon, t["int_pt"][1] - lat))
        rows.append({"bg_geoid": str(o.bg_geoid), "town": hit["town"], "town_geoid": hit["town_geoid"],
                     "county": hit["county"], "method": method})
    return pd.DataFrame(rows)


def cross_check_ej(df: pd.DataFrame) -> tuple[int, int]:
    """Compare with MassGIS MUNICIPALITY where present. Returns (compared, mismatched)."""
    if not EJ_JSON.exists():
        return 0, 0
    ej = {str(f["attributes"]["GEOID"]): normalise_town(f["attributes"]["MUNICIPALITY"])
          for f in json.loads(EJ_JSON.read_text(encoding="utf-8")).get("features", [])}
    both = df[df.bg_geoid.isin(ej)]
    mism = int((both.town != both.bg_geoid.map(ej)).sum())
    return len(both), mism


def main() -> None:
    if not COUSUB_SHP.exists():
        sys.exit(f"ERROR: {COUSUB_SHP} missing — run scripts/get_data.py (tiger_cousub)")
    if not ORIGINS.exists():
        sys.exit(f"ERROR: {ORIGINS} missing — run pipeline/build_origins.py first")
    origins = pd.read_parquet(ORIGINS)
    towns = load_towns()
    df = assign(origins, towns)
    assert len(df) == len(origins) and df.bg_geoid.is_unique
    df.to_parquet(OUT, index=False)
    compared, mism = cross_check_ej(df)
    n_near = int((df.method == "nearest").sum())
    print(f"[ ok ] wrote {OUT.relative_to(ROOT)}: {len(df)} block groups -> {df.town.nunique()} towns "
          f"({n_near} by nearest-point fallback)")
    print(f"       cross-check vs MassGIS EJ municipality: {compared} compared, {mism} mismatched")
    if compared and mism > compared * 0.02:
        sys.exit("ERROR: more than 2% of towns disagree with MassGIS — check the shapes/CRS")


if __name__ == "__main__":
    main()
