#!/usr/bin/env python3
"""Convert the origins parquet cache into a static GeoJSON for the web map.

Reads ../data/cache/origins.parquet (relative to the repo root, i.e. the parent
of web/) and writes web/public/data/origins.geojson: one Point feature per
block-group origin with properties bg_geoid, carless_adults and ej_flag.

The web app reads this file at runtime from /data/origins.geojson. It is
OPTIONAL: if absent the map shows an accessible "map data not loaded" notice.
web/public/data/ is gitignored, so this is a local build step only — the source
parquet is itself gitignored and absent in CI.

Run with the repo venv python, from anywhere:

    /path/to/repo/.venv/bin/python web/scripts/export_origins.py

Columns used come from docs/contracts.md §1 (origins.parquet).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover - env guard
    sys.stderr.write(
        "pandas is required. Run with the repo venv python "
        "(.venv/bin/python web/scripts/export_origins.py).\n"
    )
    raise SystemExit(2)

# web/scripts/export_origins.py -> web/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "data" / "cache" / "origins.parquet"
OUT = REPO_ROOT / "web" / "public" / "data" / "origins.geojson"

# Required columns from the contract. ej_flag/carless_adults are the map's
# properties; lat/lon place the point.
REQUIRED = ["bg_geoid", "lat", "lon", "carless_adults", "ej_flag"]


def build_feature_collection(df: "pd.DataFrame") -> dict:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(
            f"origins.parquet is missing required columns: {missing}. "
            f"Found: {list(df.columns)}"
        )
    features = []
    for row in df.itertuples(index=False):
        lat = float(getattr(row, "lat"))
        lon = float(getattr(row, "lon"))
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "bg_geoid": str(getattr(row, "bg_geoid")),
                    "carless_adults": int(getattr(row, "carless_adults")),
                    "ej_flag": bool(getattr(row, "ej_flag")),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def main() -> int:
    if not SRC.exists():
        sys.stderr.write(
            f"Source not found: {SRC}\n"
            "This file is gitignored and local-only; nothing to export.\n"
        )
        return 1
    df = pd.read_parquet(SRC)
    fc = build_feature_collection(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc), encoding="utf-8")
    sys.stdout.write(f"Wrote {len(fc['features'])} features to {OUT}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
