"""Build the reachability cube — data/cache/cube.parquet (docs/contracts.md §1).

One row per (clinic_id, visit_type, day, hour, bg_geoid): can a car-less adult in
that block group make the round trip to that clinic for an appointment starting at
`hour` on `day`, given the visit length? Reachability comes ONLY from the engine's
authoritative round_trip (steering: never re-derive it).

Method: one engine.round_trip per (clinic, day, hour, block group), with the block
group resolved by its population-weighted centroid (lat, lon). This is the same call
the differential tests validate, so the cube cannot drift from the router.

A faster two-profile-search version (latest_departure + earliest_arrival) was tried
and DISCARDED: comparing stop membership ignored walk time and timing, and it
under-reported reachability (1.2% flat vs the true ~31%). Re-introduce batching only
with a test proving it equals round_trip cell for cell. Current cost: ~9 min/clinic.

Clinics resolve to PVTA stops via data/manual/clinic_stops.csv (clinic_id -> stop_id),
because the manual clinic files carry addresses, not coordinates. Missing clinics are
skipped with a warning rather than guessed (every number has a real source).

Run:  python pipeline/build_cube.py [--date 2026-11-12] [--clinic BAY_GI_SPRINGFIELD] [--out PATH]
      Parallel: one process per clinic with --out data/cache/cubes/<clinic>.parquet,
      then python pipeline/merge_cubes.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from engine.gtfs import Timetable
from engine import round_trip
from engine.types import DEFAULT_LIMITS

PVTA_DIR = ROOT / "data" / "cache" / "pvta"
ORIGINS = ROOT / "data" / "cache" / "origins.parquet"
STOPS_WALK = ROOT / "data" / "cache" / "stops_walk.parquet"
CLINIC_STOPS = ROOT / "data" / "manual" / "clinic_stops.csv"
OUT = ROOT / "data" / "cache" / "cube.parquet"

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
HOURS = list(range(7, 19))  # 07..18 local, per contract
DEFAULT_VISIT_MIN = 60


def _day_to_date(day: str, anchor: str) -> str:
    """Map a weekday name to a concrete date in the feed's service window."""
    base = dt.date.fromisoformat(anchor)
    target = DAYS.index(day)
    delta = (target - base.weekday()) % 7
    return (base + dt.timedelta(days=delta)).isoformat()


def build_cube(anchor_date: str, only_clinic: str | None = None) -> pd.DataFrame:
    if not CLINIC_STOPS.exists():
        raise SystemExit(
            f"ERROR: {CLINIC_STOPS.relative_to(ROOT)} not found. It maps clinic_id -> PVTA stop_id "
            "(clinic files carry addresses, not coordinates). Create it before building the cube."
        )
    clinics = pd.read_csv(CLINIC_STOPS, dtype=str)
    if only_clinic:
        clinics = clinics[clinics.clinic_id == only_clinic]
    origins = pd.read_parquet(ORIGINS)

    rows: list[dict] = []
    # cache one Timetable per concrete date (service calendar differs by day)
    tt_cache: dict[str, Timetable] = {}

    for c in clinics.itertuples(index=False):
        clinic_id = c.clinic_id
        clinic_stop = c.stop_id
        visit_type = getattr(c, "visit_type", "") or "primary_care"
        visit_min = int(getattr(c, "visit_minutes", "") or DEFAULT_VISIT_MIN)
        for day in DAYS:
            date = _day_to_date(day, anchor_date)
            tt = tt_cache.get(date)
            if tt is None:
                tt = Timetable.from_gtfs_dir(str(PVTA_DIR), date)
                tt_cache[date] = tt
            if clinic_stop not in tt.stops:
                continue  # clinic's anchor stop not in the feed on this date
            cs = tt.stops[clinic_stop]
            clinic_ref = (cs.lat, cs.lon)
            for hour in HOURS:
                start = hour * 3600
                for o in origins.itertuples(index=False):
                    # Authoritative: the engine's round_trip, resolving the block
                    # group by its population-weighted centroid (lat, lon). This is
                    # the SAME call the differential tests validate, so the cube
                    # cannot drift from the router. (Profile-search batching is a
                    # future optimisation only once it is proven equal to this.)
                    r = round_trip(tt, (o.lat, o.lon), clinic_ref, date, start, visit_min)
                    rows.append({
                        "clinic_id": clinic_id, "visit_type": visit_type,
                        "day": day, "hour": hour, "bg_geoid": o.bg_geoid,
                        "reachable": r.reachable, "reason": r.reason,
                    })
    return pd.DataFrame(rows, columns=["clinic_id", "visit_type", "day", "hour", "bg_geoid", "reachable", "reason"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default="2026-11-12", help="anchor date (weekday mapping); inside feed window")
    ap.add_argument("--clinic", default=None, help="build only this clinic_id")
    ap.add_argument("--out", default=None,
                    help="output parquet (default data/cache/cube.parquet). Use one file per clinic "
                         "(data/cache/cubes/<clinic>.parquet) when building clinics in parallel, "
                         "then run pipeline/merge_cubes.py")
    args = ap.parse_args()
    df = build_cube(args.date, args.clinic)
    out = Path(args.out) if args.out else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    n_clin = df.clinic_id.nunique()
    reach = int(df.reachable.sum())
    print(f"[ ok ] wrote {out}: {len(df):,} cells, {n_clin} clinic(s)")
    print(f"       reachable cells: {reach:,} / {len(df):,} ({reach/max(len(df),1):.1%})")


if __name__ == "__main__":
    main()
