# schedule-optimizer — Tasks

Implementation plan. Each task cites the SO ids it satisfies.

- [x] **T1 — weights config.** `config/visit_weights.yaml` with `source`, `default`
  and per-visit-type weights, labelled illustrative. (SO-3)

- [x] **T2 — data access helpers** in `engine/optimizer.py`:
  - `load_weights(path)` → dict + source string. (SO-3)
  - `open_hours(clinic, day)` reading `data/manual/clinics.csv` with the cube-default
    fallback flag. (SO-4)
  - `build_reach_index(cube_slice)` → `(visit_type, hour, bg) -> bool`. (SO-1)
  - `cell_score(...)`, `schedule_score(...)` pure over the index + origins. (SO-1, SO-14)

- [x] **T3 — greedy CELF** `suggest_schedule(cube, origins, clinic, day, k=3)`:
  candidate enumeration (shift ±1..3, in-hours, non-overlap), lazy-evaluation heap,
  commit positive realised gains only, deterministic tie-break by block id. (SO-2,
  SO-5, SO-6, SO-8, SO-9, SO-10, SO-11)

- [x] **T4 — output shaping**: `{change, gain_visit_hours, gain_people, sources}` per
  change, plus baseline/suggested scores and open-hours provenance. (SO-15)

- [x] **T5 — exact oracle** `solve_exact(...)` with OR-Tools CP-SAT, tiny instances
  only, test-only. (SO-12)

- [x] **T6 — errors**: propagate `AuditDataError` for missing cube / empty slice. (SO-16)

- [x] **T7 — unit tests** `tests/unit/test_optimizer.py` on hand-built tiny cubes:
  known best move, never-worse when no gain, open-hours clamp, non-overlap, output shape.

- [x] **T8 — property tests** `tests/property/test_optimizer_properties.py` (Hypothesis):
  never-worse (SO-8), respects hours + block count (SO-4, SO-5), deterministic (SO-11),
  monotone in access (SO-14), greedy ≥ (1−1/e)·CP-SAT optimum (SO-13).

- [x] **T9 — reach-mcp**: wire `reachability`/`what_if`/`suggest_schedule` and the
  `reach://cubes` resource to the real engine; every response carries `sources`;
  missing cube → error payload, not a crash.

## Deferred
- Satellite-clinic day moves (SO-7) — out of scope this release; objective/method
  already admit them as extra candidate moves.
