"""Merge per-clinic cubes (data/cache/cubes/*.parquet) into data/cache/cube.parquet.

Building one clinic takes ~9 min (one engine.round_trip per cell), so clinics are
built in parallel — one process per clinic, each writing its own file with
`build_cube.py --clinic X --out data/cache/cubes/X.parquet` — and merged here.

Run:  python pipeline/merge_cubes.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "data" / "cache" / "cubes"
OUT = ROOT / "data" / "cache" / "cube.parquet"
KEY = ["clinic_id", "visit_type", "day", "hour", "bg_geoid"]


def merge(parts_dir: Path = PARTS) -> pd.DataFrame:
    files = sorted(parts_dir.glob("*.parquet"))
    if not files:
        raise SystemExit(f"ERROR: no per-clinic cubes in {parts_dir}")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    dupes = int(df.duplicated(KEY).sum())
    if dupes:
        raise SystemExit(f"ERROR: {dupes} duplicate cube keys across parts (same clinic built twice?)")
    return df


def main() -> None:
    df = merge()
    df.to_parquet(OUT, index=False)
    print(f"[ ok ] wrote {OUT.relative_to(ROOT)}: {len(df):,} cells")
    for clinic, g in df.groupby("clinic_id"):
        print(f"       {clinic}: {len(g):,} cells, {g.reachable.mean():.1%} reachable")


if __name__ == "__main__":
    main()
