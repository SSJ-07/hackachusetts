# Tasks — multi-feed

- [x] 1. `Timetable.from_gtfs_dirs(feeds, date, ...)` in `engine/gtfs.py` — agency-prefixed
  merge, per-feed calendars, cross-agency walk transfers (≤400 m), midnight-safe. Additive;
  single-feed path unchanged.
- [x] 2. Unit tests `tests/unit/test_multifeed_loader.py` — prefixing, per-feed calendar,
  transfer within/beyond radius, no midnight wrap. (MF-1..MF-4, MF-3 ±)
- [x] 3. Golden `tests/golden/test_frta_greenfield_golden.py` — Route 32 trip pinned to the
  real FRTA `stop_times.txt`. (MF-G1)
- [x] 4. Property tests `tests/property/test_multifeed_properties.py` — MF-P2 always;
  MF-P1 / MF-P3 run when the PVTA cache is present, skip otherwise.
- [x] 5. Full suite green locally (328 passed, 5 skipped).

## Remaining (needs other inputs — see "What I need from you")
- [x] 6. Added `CHCFC_GREENFIELD` to `data/manual/clinic_stops.csv`, anchored to
  `frta:2505676` "Main St at Cafe" (96 m from 102 Main St Greenfield, from the real feed).
- [x] 7a. Wired `pipeline/build_cube.py` to load a merged PVTA+FRTA Timetable when the FRTA
  feed is present (falls back to PVTA-only), and to resolve bare PVTA clinic ids to their
  `pvta:` form. Compiles clean.
- [x] 7b. Built and merged. `pipeline/stage_feeds.py` stages `data/cache/pvta` (from
  `data/raw/pvta_gtfs.zip`) and `data/cache/frta` (from `data/manual/frta_minigtfs`);
  `build_cube.py`/`stops_walk.py` prefer `data/cache/frta`, fall back to the committed feed.
  `build_cube.py --clinic CHCFC_GREENFIELD --out data/cache/cubes/CHCFC_GREENFIELD.parquet`
  then `merge_cubes.py`: CHCFC_GREENFIELD 42,504 cells, 11.3% reachable; BAY_GI_SPRINGFIELD
  unchanged at 31.1% (PVTA-only number preserved). `make data` must call
  `pipeline/stage_feeds.py` after `get_data.py`; the Greenfield row in `clinic_stops.csv`
  is then built with every other clinic.
- [x] 8. M1 review of the `engine/gtfs.py` addition (2026-10-24): additive classmethod, single-feed path untouched; agency prefix applied to every id incl. transfer endpoints; cross-agency walk O(|PVTA stops|·|FRTA stops|) ≈ 2k×400, fine; `max(0, min_transfer_time)` clamp is correct (negative times looped the relax). Multi-feed unit + property + golden suites green; real-feed RAPTOR==CSA differential added (`tests/differential/test_real_feed_agree.py`). One note: `routes` are not carried into the merged Timetable — the engine never reads them, so no change needed.
