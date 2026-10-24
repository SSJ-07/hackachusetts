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
- [x] 7b. RAN `python pipeline/build_cube.py --clinic CHCFC_GREENFIELD --out data/cache/cubes/CHCFC_GREENFIELD.parquet` (M1, 2026-10-24) and merged; `make data` now builds every clinic in clinic_stops.csv. Was: BLOCKED: needs the
  data caches — `data/cache/pvta/`, `origins.parquet`, `stops_walk.parquet` — which are
  git-ignored and built by `make data` (M2's downloads + Census key). Not present on this
  machine. Run once the caches exist.
- [x] 8. M1 review of the `engine/gtfs.py` addition (2026-10-24): additive classmethod, single-feed path untouched; agency prefix applied to every id incl. transfer endpoints; cross-agency walk O(|PVTA stops|·|FRTA stops|) ≈ 2k×400, fine; `max(0, min_transfer_time)` clamp is correct (negative times looped the relax). Multi-feed unit + property + golden suites green; real-feed RAPTOR==CSA differential added (`tests/differential/test_real_feed_agree.py`). One note: `routes` are not carried into the merged Timetable — the engine never reads them, so no change needed.
