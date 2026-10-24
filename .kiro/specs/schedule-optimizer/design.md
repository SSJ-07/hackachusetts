# schedule-optimizer — Design

> How `engine/optimizer.py` satisfies `requirements.md` (SO-1..SO-16). Pure
> functions over the cube + origins DataFrames; reachability is read, never
> re-derived (SO-1).

## Data model

- **Schedule.** For one clinic × day, the schedule is the set of hours at which a
  block is offered. The baseline is the set of cube hours present for that
  `(clinic, day)` (per `engine.audit`: one appointment block per cube hour). A
  block is identified by `"<day>-<HH>"` (e.g. `"mon-08"`), matching `/whatif`.
- **Cell score.** For a block at hour `h`:
  `cell(h) = Σ_bg w(visit_type) · carless_adults(bg) · ej(bg) · reachable(bg, clinic, day, h)`.
  `ej(bg)` is `1` if `ej_flag` else `0`. `w` is per the block's visit_type; when a
  `(clinic, day)` cube has several visit_types, each contributes its own weighted term.
- **Reachability lookup.** Built once as a dict `(visit_type, hour, bg) -> bool` from
  the cube slice, so scoring a schedule is O(blocks × bgs) with no pandas per cell.

## Objective as a function of the schedule (SO-1, SO-8, SO-14)

`score(S) = Σ_{h ∈ S} cell(h)`. Each `cell(h) ≥ 0` because weights, counts and the
`ej`/`reachable` indicators are all ≥ 0. Adding a block never decreases the score →
the *add-a-block* objective is monotone non-decreasing and submodular (coverage).
A **shift** is `remove(h) then add(h+Δ)`, a swap; its net gain `cell(h+Δ) − cell(h)`
may be negative, which is why SO-2 evaluates moves as swaps and reports realised gain
rather than a bound. Monotonicity in access (SO-14) is immediate: flipping any
`reachable` from false→true only adds non-negative terms.

## Open hours (SO-4)

`open_hours(clinic, day)` reads `data/manual/clinics.csv`:
- rows are keyed by `clinic_id` and full weekday name; `open_time`/`close_time` are
  `HH:MM`. Hours offered = integer start hours `h` with `open ≤ h` and `h < close`
  (a block starting at `h` occupies `[h, h+1)`), unioned across a day's rows (a clinic
  with a lunch split has two rows → union of both intervals).
- When no row matches the `clinic_id` (the real cube clinic `BAY_GI_SPRINGFIELD` is
  NOT in clinics.csv today), fall back to the cube's observed hour range for that
  `(clinic, day)` and set `result["open_hours_source"] = "cube-default (7..18)"` so
  the caller can surface it (SO-4).

## Greedy with lazy evaluation — CELF (SO-9, SO-10, SO-11)

Candidate moves: for each occupied hour `h` and each `Δ ∈ {±1,±2,±3}`, the move
`shift h → h+Δ` is a candidate iff `h+Δ` is within open hours (SO-4) and not already
occupied (SO-6). Keyed/sorted by `(block_id, Δ)` for determinism (SO-11).

CELF loop, up to `k` rounds (SO-9):
1. Compute each candidate's marginal gain against the baseline once; push
   `(-gain, block_id, Δ)` onto a heap (negated for a max-heap; `block_id` then `Δ`
   break ties deterministically, SO-11).
2. Pop the top. If its stored gain is stale (its source hour was already moved, or it
   was computed against an older schedule), recompute its marginal gain against the
   CURRENT schedule and, if it dropped, re-push and continue (lazy evaluation — we
   avoid recomputing every candidate each round).
3. A move is committed only if its realised gain `> 0` (SO-8: never worse — a
   non-positive move is never taken; if the heap empties of positive moves we stop
   early with fewer than `k` changes).
4. Apply the move to the current schedule, record the change, and mark candidates
   touching the vacated/filled hours stale.

Because each `cell(h)` is non-negative and committed moves have strictly positive
realised gain, `score` is non-decreasing across rounds and the returned schedule's
score ≥ baseline (SO-8).

## Exact oracle — CP-SAT (SO-12, SO-13)

`solve_exact(model, allowed, k)` builds a CP-SAT model ONLY for tiny instances
(test oracle), matching the SWAP move structure of the product path: each baseline
block stays or moves to one hour in its own ±1..3 window within open hours, targets
distinct (SO-6), block count preserved (SO-5), at most `k` blocks move. It is used
to check the swap optimizer never exceeds its own optimum and to inspect realised
gains — NOT to assert the `(1−1/e)` bound, which swaps do not satisfy.

The `(1−1/e)` bound (SO-13) is a theorem only for the ADDITIVE coverage problem
"open `k` hours to maximize `Σ cell(h)`", which is monotone and submodular. The
engine exposes that formulation separately as `greedy_select_hours` (greedy, each
round adds the highest-`cell` hour) and `exact_select_hours` (the `k` top-`cell`
hours); the property test asserts `greedy_select ≥ (1−1/e)·exact_select` there,
where it provably holds. Block MOVES can remove coverage and break monotonicity
(optimizer-notes.md), so for the product swap path only never-worse (SO-8) holds.

## Output (SO-15) and errors (SO-16)

`suggest_schedule(cube, origins, clinic, day, k=3)` returns:
```python
{
  "clinic", "day", "k",
  "baseline_score", "suggested_score",
  "open_hours", "open_hours_source",
  "changes": [ {"change": {...}, "gain_visit_hours": float,
                "gain_people": int, "sources": [...]} ],
  "sources": [...],          # engine.audit.sources() + weights config
}
```
Missing cube / empty slice → `engine.audit.load_cube` or the slice guard raises
`AuditDataError`; `reach-mcp` catches it and returns a clear error payload rather
than crashing (SO-16).

## Why this never re-derives reachability

Every `reachable(bg, block)` comes from the cube slice `engine.audit.load_cube`
provides. The optimizer only *re-indexes* those booleans; it never calls the router.
This keeps `/audit`, `/whatif`, `reach-mcp` and the optimizer consistent by
construction (the whole point of `engine.audit` being the one aggregation path).
