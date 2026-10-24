# ADR 002 — Experiment ④: Requirements-First vs Design-First spec authoring

- **Status:** accepted (observation; single-sample)
- **Date:** 2026-10-24
- **Context:** Kiro supports two spec workflows. We wrote one feature each way and
  compared them on measurable facts, to decide which workflow to default to.
  - **Requirements-First:** `.kiro/specs/schedule-optimizer/` — requirements authored
    first (EARS, stable `SO-n` ids), design derived from them, tasks cite the ids.
  - **Design-First:** `.kiro/specs/reachability-cube/` — design doc written first
    (documenting code "as it exists today"), requirements (`RC-n`) and tasks derived
    *from* the design.

> **Honesty label.** This is a **single sample per arm, same author, same week, two
> different features** (an optimizer vs a data-cube+API). It is an observation about
> these two specs, **not** a controlled result — the features differ in size and kind,
> so numbers below compare the two documents as written, not the two methodologies in
> isolation. Treat the verdict as a working default, not a proven law.

## Measured facts

All counts produced by `grep`/`wc` over the two spec trees on 2026-10-24.
Test references counted with `grep -rhoE '<ID>-[0-9]+' tests/ | sort -u`.

| Metric | Requirements-First (`schedule-optimizer`) | Design-First (`reachability-cube`) |
|---|---:|---:|
| Requirements (stable ids) | 16 (`SO-1`..`SO-16`) | 24 (`RC-1`..`RC-24`) |
| EARS `SHALL` clauses in requirements | 25 | 28 |
| Tasks total | 9 | 12 |
| Tasks ticked `[x]` | 9 (100%) | 9 (75%) |
| Tasks open `[ ]` (explicit gaps) | 0 | 3 |
| requirements.md lines | 104 | 73 |
| design.md lines | 105 | 147 |
| tasks.md lines | 41 | 40 |
| **Total spec lines** | **250** | **260** |
| Distinct requirement ids **referenced by tests** (`grep tests/`) | 9 of 16 | 0 of 24 |

### Traceability gaps (requirements with no test referencing their id)

- **Requirements-First — 7 of 16 `SO-` ids are not cited by id in `tests/`:**
  `SO-1, SO-2, SO-3, SO-7, SO-10, SO-12, SO-16`. Several are nonetheless exercised
  indirectly (e.g. `SO-1` scoring underlies every optimizer test; `SO-7` is an
  explicitly deferred satellite requirement). The property suite
  `tests/property/test_optimizer_properties.py` cites 8 ids inline
  (`SO-4,5,6,8,9,11,13,14`) and the unit suite adds `SO-13`.
- **Design-First — 0 of 24 `RC-` ids appear anywhere in `tests/`.** The cube's tests
  (`tests/unit/test_audit_api.py`, `tests/contract/test_audit_real.py`) are real and
  passing, but they trace to requirements only through the *tasks* file's
  parenthetical `(RC-…)` citations — **never in the test code itself**. So the
  requirement→test link is one hop weaker than in the Requirements-First spec: you can
  read a test and not know which `RC-` it defends.

### Design decisions with no requirement

- **Requirements-First:** none found — every design section maps back to an `SO-n`,
  because the requirements existed first and the design was written to satisfy them.
- **Design-First:** the design doc's `§2.3 discarded profile-search shortcut` is a
  decision/narrative that became requirement `RC-8` *after the fact*; the design's
  cost note `§2.4 (~9 min/clinic)` has no requirement at all (it is a property of the
  implementation, not a SHALL). This is the expected shape of design-first: the design
  carries material the requirements never capture.

## Verdict

For **this repo's safety bar** (a wrong routing answer strands a patient), the
**Requirements-First** spec is the stronger artifact on the metric that matters most
here — **requirement→test traceability**: 9/16 of its ids are cited directly in test
code, versus 0/24 for the design-first spec, whose tests trace only through the tasks
file. It also closed with **100% of tasks ticked and zero open gaps**, where
design-first honestly carries **3 explicit `[ ]` gaps** (multi-clinic cubes, build
speedup, FRTA).

That said, **design-first was the right choice for the cube**: the cube already
existed as code, and documenting it "as it exists today" then deriving requirements
captured real constraints (the 9-min cost, the discarded 1.2%-vs-31% shortcut) that a
requirements-first pass would have had to invent. Design-first also produced **more
requirements (24 vs 16)** by reverse-engineering the implementation's edge cases.

**Working default:** author *new* features **Requirements-First** (it forces the
test↔requirement link up front, which is what our differential/property discipline
depends on); use **Design-First** to *retrofit* a spec onto code that already exists
(the cube, and the `bug-transfer-limit` bugfix spec). Independently of the method, add
inline requirement-id references (`RC-…`) to the cube's tests to close the one-hop
traceability gap this experiment surfaced.

## Alternatives considered

- **Pick one method for everything.** Rejected — the two specs show each method fits a
  different situation (greenfield feature vs retrofit onto existing code).
- **Treat the numbers as a methodology benchmark.** Rejected — single sample, same
  author, two unlike features; see the honesty label.
