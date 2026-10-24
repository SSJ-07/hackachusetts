# schedule-optimizer — Requirements (EARS)

> Feature spec, Requirements-First. The authoritative requirements for the
> "Suggest best schedule" optimizer. Working summary lives in steering
> `optimizer-notes.md`; THIS file is authoritative where the two differ.
> Objective, constraints and bounds fixed here; data shapes fixed by
> `docs/contracts.md` §1 (cube) and the `origins` table.
>
> Consumed by `engine/optimizer.py`, exposed via `reach-mcp` `suggest_schedule`.
> Each requirement has a stable id (`SO-n`) referenced by tests.

## Scope

- **In scope (MVP):** shifting an existing clinic block by ±1..3 hours within
  the clinic's posted open hours, for one clinic × day, ranked by marginal gain.
- **Out of scope (explicitly deferred):** satellite-clinic days. The objective
  and method below are designed to admit satellites as additional candidate
  moves later (optimizer-notes.md), but SO this release implements block shifts
  only. No requirement here depends on a satellite candidate list.

## Objective

- **SO-1 (coverage objective).** THE optimizer SHALL score a schedule as
  `score = Σ_blocks Σ_bg  w(visit_type) · carless_adults(bg) · ej(bg) · reachable(bg, block)`,
  where `reachable` is read from the cube (`docs/contracts.md` §1), `carless_adults`
  and `ej_flag` from `origins`, and `w(visit_type)` from `config/visit_weights.yaml`.
  THE optimizer SHALL NOT re-derive reachability; it reads it from the cube only.

- **SO-2 (decision variable).** THE optimizer SHALL consider, for each existing
  block at hour `h`, moving it to hour `h+Δ` for `Δ ∈ {−3,−2,−1,+1,+2,+3}`, and
  SHALL evaluate each move as a SWAP (the block leaves `h` and appears at `h+Δ`),
  reporting the realised net gain rather than a submodular bound.

- **SO-3 (illustrative weights).** WHERE `w(visit_type)` is sourced from
  `config/visit_weights.yaml`, THE optimizer SHALL treat the weights as
  illustrative and SHALL surface the config's `source` field in `sources`.

## Hard constraints

- **SO-4 (open hours).** THE optimizer SHALL only place a block at an hour within
  the clinic's posted open hours. WHERE `data/manual/clinics.csv` has rows whose
  `clinic_id` matches, THE optimizer SHALL take open/close hours from them; OTHERWISE
  THE optimizer SHALL default to the cube's observed hour range (7..18) and SHALL
  state in its result that the default was used.

- **SO-5 (same block count).** THE optimizer SHALL keep the number of blocks per
  day unchanged — a shift removes exactly one block-hour and adds exactly one.

- **SO-6 (no overlap).** THE optimizer SHALL NOT place two blocks at the same hour
  for the same clinic/day (one appointment block per cube hour, per `engine.audit`).
  A move whose destination hour is already occupied is not a candidate.

- **SO-7 (satellite candidate list).** IF satellite days are implemented in a
  later release, THE optimizer SHALL only add a satellite day at a site present in
  the candidate list. (Deferred — see Scope.)

## Behaviour

- **SO-8 (never worse).** WHEN the optimizer returns a suggested schedule, THE
  suggested schedule's score SHALL be ≥ the baseline schedule's score. WHEN no
  move improves the score, THE optimizer SHALL return zero changes and the baseline.

- **SO-9 (bounded changes).** THE optimizer SHALL return at most `k` changes
  (default `k = 3`), ranked by descending realised marginal gain.

- **SO-10 (greedy with lazy evaluation).** THE optimizer SHALL select changes
  greedily using lazy evaluation (CELF): a priority queue keyed by each candidate's
  last-computed marginal gain, re-evaluating the top candidate against the current
  schedule before committing it.

- **SO-11 (determinism).** GIVEN identical inputs, THE optimizer SHALL return an
  identical ranked list. WHERE two candidate moves have equal marginal gain, THE
  optimizer SHALL break the tie by block id (ascending), so ordering never depends
  on dict/iteration order.

- **SO-12 (exact oracle).** THE optimizer SHALL provide an OR-Tools CP-SAT exact
  solver for tiny instances, used ONLY as a differential test oracle, never on the
  production path.

- **SO-13 (greedy vs exact bound).** THE optimizer SHALL expose the coverage
  formulation "open `k` hours to maximize `Σ cell(h)`" (monotone submodular), and on
  tiny instances greedy selection over it SHALL be ≥ `(1 − 1/e)` × the exact optimum
  of the SAME formulation. Block MOVES are swaps and can remove coverage, so the
  `(1−1/e)` guarantee is a theorem only for this additive selection — NOT for the
  swap objective, where only never-worse (SO-8) is guaranteed. The swap optimizer
  is separately checked to never exceed its own CP-SAT swap optimum.

- **SO-14 (monotone in access).** WHEN a cube is modified so that some
  `(bg, block)` flips from unreachable to reachable and nothing flips the other
  way, THE baseline score SHALL NOT decrease.

## Output

- **SO-15 (change shape).** THE optimizer SHALL return, for each suggested change,
  `{change, gain_visit_hours, gain_people, sources}` where:
  - `change` describes the move (e.g. `{kind:"shift", day, block:"mon-08", to:10}`),
  - `gain_visit_hours` is the realised increase in `Σ w·carless·ej·reachable` (visit-hours),
  - `gain_people` is the realised increase in reachable car-less EJ adults (unweighted),
  - `sources` carries provenance (cube, origins, weights config) per the guardrail.
  Gains SHALL be computed, never hard-coded.

- **SO-16 (data errors).** WHERE the cube is missing or the clinic/day has no cube
  rows, THE optimizer SHALL raise `engine.audit.AuditDataError` (not crash), so
  callers can return a clear error payload.
