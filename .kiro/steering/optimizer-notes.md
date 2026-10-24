---
inclusion: auto
name: Optimizer notes
description: Schedule optimization, coverage objective, satellite clinic day, "suggest best schedule", greedy vs CP-SAT, block shifts and clinic-hour constraints
---

# Schedule optimizer — objective, constraints, bounds

Powers **"Suggest best schedule"** in Clinic Audit. Lives in `engine/` and is exposed via
`reach-mcp` `suggest_schedule(clinic, k)`. The `schedule-optimizer` spec is authoritative
for exact requirements; this file is the working summary.

## Decision variables
- Shift an existing clinic block by **±1–3 hours**, and/or
- Add **at most one satellite day** at a candidate site.
- Return up to **K** changes (default K = 3), ranked by marginal gain.

## Objective
Maximize **reachable visit-hours for EJ car-less adults**, weighted by visit priority:

```
score(schedule) = Σ_blocks Σ_bg  w(visit_type) · carless_adults(bg) · ej(bg) · reachable(bg, block)
```

- `reachable` comes from the cube (`data/cache/cube.parquet`) using the authoritative
  round-trip definition in `docs/contracts.md` §2. Never re-derive reachability here.
- Priority weights `w` live in config with a source; colonoscopy follow-up, prenatal and
  dialysis weigh more. Weights are **illustrative** until sourced.

## Constraints (hard)
- Stay within the clinic's posted open hours.
- Keep the same number of blocks (and block lengths) per week.
- No two blocks overlap for the same provider/room.
- Satellite day only at sites in the candidate list.

## Method and bounds
- **Greedy with lazy evaluation** (CELF). The objective is a coverage function: monotone
  and submodular under "add a change", so greedy is within **(1 − 1/e)** of optimal for the
  cardinality-constrained case. Block *moves* that remove coverage break pure
  monotonicity — evaluate them as swaps and report the realised gain, not the bound.
- **OR-Tools CP-SAT** solves tiny instances exactly as a differential oracle.

## Properties that must hold (tests/property/)
- **Never worse:** suggested score ≥ current score; respects hours and block counts.
- **Greedy vs exact:** on tiny instances greedy ≥ (1 − 1/e) · CP-SAT optimum.
- **Monotone in access:** adding a stop, trip or satellite never decreases reachability.
- Deterministic: same inputs + seed → same ranked list (break ties by block id).

## Output
Each suggested change carries `{change, gain_visit_hours, gain_people, sources}` so the UI
can show impact with provenance. Gains are **computed**, never hard-coded.
