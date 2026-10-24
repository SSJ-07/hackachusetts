# Reachability cube — tasks

Status is honest: `[x]` is implemented and tested today; `[ ]` is explicitly **not
done**. Requirement ids in parentheses trace to `requirements.md`.

## Done

- [x] Cube schema + offline builder, one `round_trip` per cell, centroid-resolved block
  groups, `clinic_stops.csv` clinic anchors, missing-clinic skip. (RC-1…RC-7) —
  `pipeline/build_cube.py`
- [x] Discarded profile-search shortcut documented; guarded against reintroduction
  without a cell-for-cell equality test. (RC-8) — `design.md §2.3`, `build_cube.py`
- [x] Single aggregation path `engine/audit.py`: loaders, community filter, car-less
  weighting, equity groups, `audit()`, `whatif()`, `sources()`. (RC-9…RC-16) —
  `engine/audit.py`
- [x] `GET /audit` real mode via `engine.audit.audit`; `AuditDataError → 404`;
  mock mode unchanged. (RC-14, RC-17, RC-18, RC-20) — `api/routers/audit.py`
- [x] `POST /whatif` real mode via `engine.audit.whatif`; unknown clinic → 404, bad
  block/hour → 422; same `AuditResponse` shape. (RC-16, RC-21) — `api/routers/whatif.py`
- [x] `get_audit_data` returns mock payload or cached real cube+origins; 503 when
  parquet missing; overridable by tests. (RC-18, RC-19, RC-22) — `api/deps.py`
- [x] Unit tests on a tiny hand-built cube + origins injected via
  `dependency_overrides` (shares in [0,1], car-less weighting, equity groups, sources
  with vintage, whatif changes the hour set, unknown clinic 404). (RC-10…RC-16, RC-20,
  RC-21, RC-22) — `tests/unit/test_audit_api.py`
- [x] Real-cube contract test, skipped when `cube.parquet` is absent, asserting the
  hourly share is not flat (max−min > 0.05) for `BAY_GI_SPRINGFIELD thu`. (RC-11, RC-18,
  RC-23) — `tests/contract/test_audit_real.py`
- [x] Provenance: source + vintage on every number. (RC-15, RC-23) — `engine/audit.sources`

## Not done (explicit gaps)

- [ ] **Multi-clinic cubes.** The cache holds exactly one clinic
  (`BAY_GI_SPRINGFIELD`). Building more clinics is supported by `build_cube.py` but has
  not been run; `/audit` for any other clinic returns 404 in real mode. (RC-1, RC-4)
- [ ] **Build speedup.** The cube costs ~9 min/clinic (one `round_trip` per cell). No
  faster path is in place — the profile-search shortcut was discarded as inaccurate and
  must not return without a cell-for-cell equality proof. (RC-8)
- [ ] **FRTA / other agencies.** Only the PVTA GTFS feed is modelled. FRTA and any other
  regional transit agency are out of scope for the current cube. (RC-6)
