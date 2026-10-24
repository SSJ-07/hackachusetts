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
- [ ] 6. Add `CHCFC_GREENFIELD` to `data/manual/clinic_stops.csv` with a real FRTA stop_id
  near 102 Main St Greenfield (candidate: a High St / JWO Transit Center stop from
  `frta_minigtfs/stops.txt`). Needs: confirm the nearest stop_id.
- [ ] 7. `python pipeline/build_cube.py` for CHCFC Greenfield, using a PVTA+FRTA merged
  Timetable. Needs: the PVTA cache (`data/cache/pvta`) present locally or in CI, and a
  confirmation from M2 that `build_cube.py` should call `from_gtfs_dirs` (today it loads a
  single feed — a one-line wiring change M2 or M3 makes together).
- [ ] 8. M1 review of the `engine/gtfs.py` addition before merge.
