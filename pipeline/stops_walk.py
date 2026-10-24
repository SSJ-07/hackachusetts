"""Build data/cache/stops_walk.parquet (walk links from origins to nearby PVTA stops).

Run from the repo root:   python pipeline/stops_walk.py

For every block-group origin, find the PVTA stops within 800 m straight-line and
estimate the walk time.

Inputs:
  * data/cache/origins.parquet   (bg_geoid, lat, lon)  -- from build_origins.py
  * data/raw/pvta_gtfs.zip       (stops.txt)           -- from get_data.py

Output columns (see docs/contracts.md -> stops_walk.parquet):
  bg_geoid, stop_id, walk_min

METHOD (MVP, see docs/methods.md):
  distance        = haversine straight-line metres between origin and stop
  keep            = distance <= 800 m
  walk_min        = distance * 1.3 (detour factor) / 80 (metres per minute)
A true walk network (OSM) is the stretch upgrade; straight-line x 1.3 is the honest MVP.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
ORIGINS = CACHE / "origins.parquet"
GTFS_ZIP = ROOT / "data" / "raw" / "pvta_gtfs.zip"
# FRTA (rural Franklin County) feed, unzipped. Its stop ids are written with the
# "frta:" prefix used by Timetable.from_gtfs_dirs; PVTA ids stay bare for
# backward compatibility with existing consumers. (spec: multi-feed)
_FRTA_CACHE_STOPS = ROOT / "data" / "cache" / "frta" / "stops.txt"  # pipeline/stage_feeds.py
FRTA_STOPS = (_FRTA_CACHE_STOPS if _FRTA_CACHE_STOPS.is_file()
              else ROOT / "data" / "manual" / "frta_minigtfs" / "stops.txt")
OUT = CACHE / "stops_walk.parquet"

MAX_WALK_M = 800.0       # max straight-line distance to a usable stop
DETOUR = 1.3             # straight-line -> on-the-ground walking distance factor
METRES_PER_MIN = 80.0    # ~4.8 km/h walking speed
EARTH_R = 6_371_000.0    # metres


def _parse_stops(rows, prefix: str = "") -> list[tuple[str, float, float]]:
    recs = []
    for r in rows:
        # location_type 0 or blank = a real boarding stop (skip stations/entrances).
        if (r.get("location_type") or "0").strip() not in ("", "0"):
            continue
        lat, lon = (r.get("stop_lat") or "").strip(), (r.get("stop_lon") or "").strip()
        if not lat or not lon:
            continue
        recs.append((prefix + r["stop_id"].strip(), float(lat), float(lon)))
    return recs


def load_stops() -> pd.DataFrame:
    with zipfile.ZipFile(GTFS_ZIP) as z:
        recs = _parse_stops(csv.DictReader(io.TextIOWrapper(z.open("stops.txt"), "utf-8-sig")))
    if FRTA_STOPS.exists():
        with FRTA_STOPS.open(encoding="utf-8-sig", newline="") as f:
            recs += _parse_stops(csv.DictReader(f), prefix="frta:")
    return pd.DataFrame(recs, columns=["stop_id", "stop_lat", "stop_lon"])


def haversine_m(lat1, lon1, lat2, lon2):
    """Vectorised great-circle distance in metres (arrays broadcast)."""
    rlat1, rlat2 = np.radians(lat1), np.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(rlat1) * np.cos(rlat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_R * np.arcsin(np.sqrt(a))


def main() -> None:
    origins = pd.read_parquet(ORIGINS)
    stops = load_stops()

    o_lat = origins["lat"].to_numpy()
    o_lon = origins["lon"].to_numpy()
    s_lat = stops["stop_lat"].to_numpy()
    s_lon = stops["stop_lon"].to_numpy()

    # ~800 m is about 0.0073 deg latitude; pre-filter by a latitude band so we only
    # haversine plausible pairs instead of all 506 x ~1980.
    lat_band = (MAX_WALK_M / 111_320.0) * 1.2  # small safety margin

    out_bg, out_stop, out_min = [], [], []
    for i in range(len(origins)):
        near = np.abs(s_lat - o_lat[i]) <= lat_band
        if not near.any():
            continue
        idx = np.nonzero(near)[0]
        d = haversine_m(o_lat[i], o_lon[i], s_lat[idx], s_lon[idx])
        within = d <= MAX_WALK_M
        for j, keep in zip(idx, within):
            if keep:
                dist = haversine_m(o_lat[i], o_lon[i], s_lat[j], s_lon[j])
                out_bg.append(origins["bg_geoid"].iloc[i])
                out_stop.append(stops["stop_id"].iloc[j])
                out_min.append(round(float(dist) * DETOUR / METRES_PER_MIN, 2))

    df = pd.DataFrame({"bg_geoid": out_bg, "stop_id": out_stop, "walk_min": out_min})
    df = df.sort_values(["bg_geoid", "walk_min"]).reset_index(drop=True)

    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)

    n_bg_with = df["bg_geoid"].nunique()
    n_bg_total = len(origins)
    print(f"[ ok ] wrote {OUT.relative_to(ROOT)}: {len(df):,} walk links")
    print(f"       block groups with >=1 stop within 800 m: {n_bg_with} / {n_bg_total}")
    print(f"       block groups with NO stop (transit desert): {n_bg_total - n_bg_with}")
    if len(df):
        print(f"       stops per block group: min {df.groupby('bg_geoid').size().min()}, "
              f"median {int(df.groupby('bg_geoid').size().median())}, "
              f"max {df.groupby('bg_geoid').size().max()}")
        print(f"       walk_min range: {df['walk_min'].min():.2f} .. {df['walk_min'].max():.2f}")


if __name__ == "__main__":
    main()
