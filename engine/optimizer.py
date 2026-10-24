"""Schedule optimizer — "Suggest best schedule".

Pure functions over the reachability cube and the origins table. Reachability
is READ from the cube (via engine.audit.load_cube/load_origins), NEVER re-derived
here — that is the whole point of engine.audit being the one aggregation path, so
/audit, /whatif, reach-mcp and this optimizer can never disagree about a number.

Objective (optimizer-notes.md / schedule-optimizer spec SO-1):

    score(S) = Σ_{block h ∈ S} Σ_bg  w(visit_type) · carless_adults(bg) · ej(bg)
                                      · reachable(bg, clinic, day, h)

Decision (SO-2): shift an existing block by Δ ∈ {−3..−1, +1..+3} hours, evaluated
as a swap, reporting the realised net gain. Greedy with lazy evaluation (CELF),
up to k changes, never worse than baseline, within open hours, deterministic
(ties broken by block id). An exact OR-Tools CP-SAT solver is provided ONLY as a
differential test oracle (solve_exact), never on the production path.

See .kiro/specs/schedule-optimizer/ for the authoritative requirements/design.
"""

from __future__ import annotations

import csv
import heapq
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from engine.audit import (
    AuditDataError,
    CUBE_PATH,
    ORIGINS_PATH,
    load_cube,
    load_origins,
    sources as audit_sources,
)

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_PATH = ROOT / "config" / "visit_weights.yaml"
CLINICS_CSV = ROOT / "data" / "manual" / "clinics.csv"

SHIFT_DELTAS = (-3, -2, -1, 1, 2, 3)  # SO-2
DEFAULT_K = 3  # SO-9

# full weekday name -> cube day abbreviation
_DAY_ABBR = {
    "monday": "mon", "tuesday": "tue", "wednesday": "wed", "thursday": "thu",
    "friday": "fri", "saturday": "sat", "sunday": "sun",
}


# --------------------------------------------------------------------------- #
# weights (SO-3)
# --------------------------------------------------------------------------- #
def load_weights(path: Path = WEIGHTS_PATH) -> dict[str, Any]:
    """Load visit-type priority weights. Returns {default, weights, source, vintage}.

    Illustrative placeholders (guardrail): the config's `source` is surfaced in
    the optimizer's `sources`. A missing file degrades to an all-1.0 weighting
    labelled as such, rather than crashing.
    """
    if not path.exists():
        return {"default": 1.0, "weights": {}, "source": "missing config — all weights 1.0 (illustrative)",
                "vintage": "n/a"}
    data = yaml.safe_load(path.read_text()) or {}
    return {
        "default": float(data.get("default", 1.0)),
        "weights": {str(k): float(v) for k, v in (data.get("weights") or {}).items()},
        "source": str(data.get("source", "unlabelled")),
        "vintage": str(data.get("vintage", "unknown")),
    }


def weight_of(visit_type: str, weights: dict[str, Any]) -> float:
    return float(weights["weights"].get(visit_type, weights["default"]))


def weights_source(weights: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "visit priority weights (illustrative)",
        "vintage": weights.get("vintage", "unknown"),
        "detail": weights.get("source", "unlabelled"),
        "illustrative": True,
        "url": None,
    }


# --------------------------------------------------------------------------- #
# open hours (SO-4)
# --------------------------------------------------------------------------- #
def _parse_hhmm_to_hour_floor(s: str) -> int | None:
    s = (s or "").strip()
    if not s or ":" not in s:
        return None
    try:
        hh, mm = s.split(":", 1)
        return int(hh)
    except ValueError:
        return None


def open_hours(clinic: str, day: str, cube_hours: list[int],
               clinics_csv: Path = CLINICS_CSV) -> tuple[list[int], str]:
    """Allowed start hours for a (clinic, day).

    Prefers rows in data/manual/clinics.csv matching clinic_id; a block starting
    at h occupies [h, h+1), so allowed start hours are open <= h < close, unioned
    across the day's rows (handles lunch splits). Falls back to the cube's observed
    hour range when no row matches, and reports which source was used (SO-4).

    Returns (sorted_hours, source_label).
    """
    day_abbr = day.strip().lower()[:3]
    allowed: set[int] = set()
    matched = False
    if clinics_csv.exists():
        with open(clinics_csv, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("clinic_id") != clinic:
                    continue
                if _DAY_ABBR.get((row.get("day") or "").strip().lower()) != day_abbr:
                    continue
                o = _parse_hhmm_to_hour_floor(row.get("open_time", ""))
                c_raw = (row.get("close_time") or "").strip()
                c = _parse_hhmm_to_hour_floor(c_raw)
                if o is None or c is None:
                    continue
                matched = True
                # a start hour h is allowed if h >= open and h < close (block needs the hour)
                for h in range(o, c):
                    allowed.add(h)
    if matched and allowed:
        return sorted(allowed), "clinics.csv (posted office hours)"
    # fallback: cube's observed range (SO-4)
    if cube_hours:
        lo, hi = min(cube_hours), max(cube_hours)
        return list(range(lo, hi + 1)), f"cube-default ({lo}..{hi})"
    return [], "cube-default (no hours)"


# --------------------------------------------------------------------------- #
# scoring (SO-1, SO-14)
# --------------------------------------------------------------------------- #
class ScoreModel:
    """Pre-indexed scoring over one (clinic, day) cube slice + origins.

    Holds, per cube hour, the two realised totals so a schedule's score is a sum
    over its block hours with no pandas per cell:
        wscore[h] = Σ_bg w(visit_type)·carless·ej·reachable   (visit-hours)
        people[h] = Σ_bg carless·ej·reachable                 (unweighted people)
    """

    def __init__(self, cube: pd.DataFrame, origins: pd.DataFrame, clinic: str, day: str,
                 weights: dict[str, Any] | None = None):
        self.clinic = clinic
        self.day = day
        self.weights = weights if weights is not None else load_weights()
        sub = cube[(cube.clinic_id == clinic) & (cube.day == day)]
        if sub.empty:
            raise AuditDataError(f"no cube rows for clinic={clinic!r} day={day!r}")
        o = origins[["bg_geoid", "carless_adults", "ej_flag"]].copy()
        o["ej_flag"] = o["ej_flag"].astype(bool)
        joined = sub.merge(o, on="bg_geoid", how="inner")
        if joined.empty:
            raise AuditDataError(f"no origins join for clinic={clinic!r} day={day!r}")
        joined = joined[joined.reachable & joined.ej_flag].copy()
        # force plain numpy float arithmetic (robust to pyarrow-backed dtypes)
        w = joined["visit_type"].map(lambda v: weight_of(v, self.weights)).astype("float64")
        carless = pd.to_numeric(joined["carless_adults"], errors="coerce").astype("float64").fillna(0.0)
        joined["people_term"] = carless.to_numpy()
        joined["w_term"] = (w.to_numpy() * carless.to_numpy())
        self.wscore: dict[int, float] = {}
        self.people: dict[int, float] = {}
        for hour, grp in joined.groupby("hour"):
            self.wscore[int(hour)] = float(grp["w_term"].sum())
            self.people[int(hour)] = float(grp["people_term"].sum())
        self.cube_hours = sorted(int(h) for h in sub.hour.unique())
        self.baseline_blocks = tuple(self.cube_hours)  # one block per cube hour

    def cell(self, hour: int) -> float:
        return self.wscore.get(hour, 0.0)

    def cell_people(self, hour: int) -> int:
        return int(round(self.people.get(hour, 0.0)))

    def score(self, blocks) -> float:
        return sum(self.cell(h) for h in blocks)


# --------------------------------------------------------------------------- #
# candidate moves
# --------------------------------------------------------------------------- #
def _block_id(day: str, hour: int) -> str:
    return f"{day}-{hour:02d}"


# --------------------------------------------------------------------------- #
# greedy with lazy evaluation — CELF (SO-8..SO-11)
# --------------------------------------------------------------------------- #
def _greedy(model: ScoreModel, day: str, allowed: set[int], k: int):
    """Return (final_blocks, changes). changes: list of dicts with from/to/gains.

    Each block is shifted AT MOST ONCE: once moved, its new hour is frozen so a
    block cannot migrate further than ±1..3 of its baseline hour across rounds.
    This keeps the k returned changes as k distinct block relocations (SO-2/SO-9)
    and keeps greedy within the per-block exact swap optimum.
    """
    blocks = list(model.baseline_blocks)
    frozen: set[int] = set()  # current hours of blocks that have already moved
    changes: list[dict[str, Any]] = []

    def marginal(from_h: int, to_h: int, cur: set[int]) -> float:
        # swap from_h -> to_h on the current schedule (SO-2): realised net gain.
        if from_h not in cur or to_h in cur or from_h in frozen:
            return float("-inf")  # stale: source gone/frozen or target now filled
        return model.cell(to_h) - model.cell(from_h)

    for _ in range(k):
        cur = set(blocks)
        # Build/refresh heap of candidate moves against the current schedule.
        # Lazy evaluation: compute gains once, then only recompute the popped top.
        heap: list[tuple[float, int, int, int]] = []
        for h in sorted(blocks):
            if h in frozen:
                continue
            for d in SHIFT_DELTAS:
                to = h + d
                if to in allowed and to not in cur:
                    g = model.cell(to) - model.cell(h)
                    # max-heap via negation; tie-break by block id (from_hour) then to
                    heapq.heappush(heap, (-g, h, to, d))

        best: tuple[float, int, int] | None = None
        # CELF: pop, recompute top against current schedule, re-push if it dropped.
        seen_recompute: set[tuple[int, int]] = set()
        while heap:
            neg_g, from_h, to_h, _d = heapq.heappop(heap)
            key = (from_h, to_h)
            cur_gain = marginal(from_h, to_h, cur)
            stored = -neg_g
            if key not in seen_recompute and cur_gain < stored - 1e-12:
                # stale upper bound: re-insert with recomputed gain and continue
                seen_recompute.add(key)
                heapq.heappush(heap, (-cur_gain, from_h, to_h, _d))
                continue
            # top of heap is accurate for current schedule
            if cur_gain > 1e-12:  # SO-8: only commit strictly positive moves
                best = (cur_gain, from_h, to_h)
            break

        if best is None:
            break  # no improving move; stop early (SO-8/SO-9)

        gain, from_h, to_h = best
        people_before = model.cell_people(from_h)
        people_after = model.cell_people(to_h)
        changes.append({
            "change": {"kind": "shift", "day": day,
                       "block": _block_id(day, from_h), "to": int(to_h)},
            "gain_visit_hours": float(gain),
            "gain_people": int(people_after - people_before),
        })
        blocks.remove(from_h)
        blocks.append(to_h)
        blocks.sort()
        frozen.add(to_h)  # this block has moved; it may not move again

    return tuple(blocks), changes


# --------------------------------------------------------------------------- #
# public API (SO-15, SO-16)
# --------------------------------------------------------------------------- #
def suggest_schedule(cube: pd.DataFrame, origins: pd.DataFrame, clinic: str, day: str,
                     k: int = DEFAULT_K, weights: dict[str, Any] | None = None,
                     baseline_blocks: "tuple[int, ...] | list[int] | None" = None) -> dict[str, Any]:
    """Up to k ranked block shifts maximizing reachable EJ car-less visit-hours.

    Deterministic, never worse than baseline, within open hours. See SO-1..SO-16.
    Raises AuditDataError when the clinic/day has no cube rows (SO-16).

    `baseline_blocks`: the clinic's current block START hours for this day. Defaults
    to one block per cube hour (the engine.audit convention). A real clinic runs
    fewer blocks than the cube has hours, so callers pass the actual schedule to get
    meaningful shift suggestions; with every cube hour occupied no shift is legal
    (every target hour is already filled) and zero changes is the correct answer.
    """
    model = ScoreModel(cube, origins, clinic, day, weights=weights)
    if baseline_blocks is not None:
        model.baseline_blocks = tuple(sorted(int(h) for h in baseline_blocks))
    allowed_list, hours_source = open_hours(clinic, day, model.cube_hours)
    allowed = set(allowed_list)
    # baseline blocks must be within allowed hours for a fair never-worse comparison;
    # cube hours are always within the cube-default range, and for clinics.csv the
    # baseline is still the cube's existing blocks (we only constrain MOVE targets).
    baseline_score = model.score(model.baseline_blocks)

    final_blocks, changes = _greedy(model, day, allowed, max(0, int(k)))
    suggested_score = model.score(final_blocks)
    # never-worse guard (SO-8): if numerics ever produced a regression, fall back.
    if suggested_score < baseline_score - 1e-9:
        final_blocks, changes, suggested_score = model.baseline_blocks, [], baseline_score

    src = audit_sources() + [weights_source(model.weights)]
    for ch in changes:
        ch["sources"] = src
    return {
        "clinic": clinic,
        "day": day,
        "k": int(k),
        "baseline_score": float(baseline_score),
        "suggested_score": float(suggested_score),
        "baseline_blocks": [int(h) for h in model.baseline_blocks],
        "suggested_blocks": [int(h) for h in final_blocks],
        "open_hours": allowed_list,
        "open_hours_source": hours_source,
        "changes": changes,
        "sources": src,
    }


def suggest_schedule_for(clinic: str, day: str = "mon", k: int = DEFAULT_K,
                         baseline_blocks: "tuple[int, ...] | list[int] | None" = None,
                         cube_path: Path = CUBE_PATH, origins_path: Path = ORIGINS_PATH) -> dict[str, Any]:
    """Convenience real-data entry point: loads the cached cube + origins and runs
    suggest_schedule. Raises AuditDataError (via load_*) if the cache is missing."""
    cube = load_cube(cube_path)
    origins = load_origins(origins_path)
    return suggest_schedule(cube, origins, clinic, day, k=k, baseline_blocks=baseline_blocks)


# --------------------------------------------------------------------------- #
# exact oracle — OR-Tools CP-SAT (SO-12). TEST ORACLE ONLY.
# --------------------------------------------------------------------------- #
def solve_exact(model: ScoreModel, allowed: set[int], k: int | None = None) -> dict[str, Any]:
    """Exact best schedule under the SAME move structure as greedy. TINY only.

    Each baseline block either STAYS at its hour or moves to one target in its own
    ±1..3 window that is within open hours (SO-4); targets are distinct (SO-6); the
    block count is preserved (SO-5). WHERE `k` is given, at most `k` blocks may move
    (match the greedy move budget), so greedy ≥ (1−1/e)·optimum is a fair comparison
    (SO-13). Used only as a differential test oracle, never on the production path
    (SO-12).
    """
    from ortools.sat.python import cp_model

    baseline = list(model.baseline_blocks)
    n_blocks = len(baseline)

    m = cp_model.CpModel()
    SCALE = 1_000_000
    # per-block option vars: for block i, one bool per (stay | legal shift target).
    # option "stay" = its own hour; shift targets = hour+Δ in open hours.
    options: dict[int, dict[int, Any]] = {}       # block_hour -> {target_hour: boolvar}
    moved: dict[int, Any] = {}                     # block_hour -> bool(moved?)
    for i, h in enumerate(baseline):
        targets = {h}  # stay
        for d in SHIFT_DELTAS:
            t = h + d
            if t in allowed:
                targets.add(t)
        vs = {t: m.NewBoolVar(f"b{i}_h{h}_to{t}") for t in sorted(targets)}
        options[h] = vs
        m.Add(sum(vs.values()) == 1)              # each block lands exactly once
        moved[h] = m.NewBoolVar(f"b{i}_moved")
        # moved == not(stay)
        m.Add(moved[h] == 1 - vs[h])
    # SO-6: no two blocks occupy the same target hour.
    all_targets = sorted({t for vs in options.values() for t in vs})
    for t in all_targets:
        occ = [vs[t] for vs in options.values() if t in vs]
        if len(occ) > 1:
            m.Add(sum(occ) <= 1)
    if k is not None:
        m.Add(sum(moved.values()) <= int(k))      # at most k moves (greedy budget)

    m.Maximize(sum(int(round(model.cell(t) * SCALE)) * v
                   for vs in options.values() for t, v in vs.items()))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"CP-SAT found no solution (status={status})")
    chosen = tuple(sorted(t for vs in options.values() for t, v in vs.items()
                          if solver.Value(v) == 1))
    return {"blocks": chosen, "score": model.score(chosen), "status": int(status)}


# --------------------------------------------------------------------------- #
# Coverage-selection formulation (SO-13 bound). ANALYSIS / TEST ORACLE ONLY.
#
# The product path uses block SHIFTS (swaps), which can remove coverage and so
# break the monotone-submodular guarantee (optimizer-notes.md). The (1−1/e)
# greedy bound is a theorem only for the ADDITIVE coverage problem: "choose k
# hours to OPEN to maximize Σ cell(h)", which is monotone + submodular. These two
# functions expose that formulation so SO-13 can be asserted where it provably
# holds. They are not used by suggest_schedule.
# --------------------------------------------------------------------------- #
def greedy_select_hours(model: ScoreModel, allowed: set[int], k: int) -> dict[str, Any]:
    """Greedy: open up to k hours, each round adding the highest-cell hour.

    Deterministic (ties by hour). Monotone submodular coverage → within (1−1/e)
    of the exact optimum (classic result)."""
    chosen: list[int] = []
    remaining = sorted(allowed)
    for _ in range(max(0, int(k))):
        best_h, best_gain = None, 0.0
        for h in remaining:
            if h in chosen:
                continue
            g = model.cell(h)  # additive: marginal of adding h is just cell(h)
            if g > best_gain + 1e-12 or (best_h is None and g > 1e-12):
                best_h, best_gain = h, g
        if best_h is None:
            break
        chosen.append(best_h)
    chosen.sort()
    return {"hours": tuple(chosen), "score": sum(model.cell(h) for h in chosen)}


def exact_select_hours(model: ScoreModel, allowed: set[int], k: int) -> dict[str, Any]:
    """Exact: the k hours with the largest cell scores (additive optimum)."""
    scored = sorted(((model.cell(h), h) for h in allowed), key=lambda t: (-t[0], t[1]))
    top = [h for c, h in scored[:max(0, int(k))] if c > 1e-12]
    return {"hours": tuple(sorted(top)), "score": sum(model.cell(h) for h in top)}
