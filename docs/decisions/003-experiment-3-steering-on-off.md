# ADR 003 — Experiment ③: steering ON vs OFF (does `gtfs-domain.md` change the answer?)

- **Status:** accepted (observation; single-sample, one confound — see below)
- **Date:** 2026-10-24
- **Context:** `.kiro/steering/gtfs-domain.md` encodes the "classic midnight bug" rule:
  GTFS `stop_times` ≥ `24:00:00` must be parsed as seconds past local midnight and
  **never wrapped** (`24:30:00` → `88200`, not `1800`). Does having that steering file
  present actually change what Kiro writes? We removed the time-parser, then asked
  Kiro to re-implement it twice — once with the steering present, once with it deleted.

> **This experiment RAN for real.** `kiro-cli chat --no-interactive` works in this
> environment (verified: it answered a probe without a login prompt). It is not a
> pending/human-run writeup. Caps honoured: **2 kiro-cli runs, well under 10 min**.

## Protocol (as executed)

Two scratch copies under `$KIROCREW_SCRATCH/exp3-on` and `exp3-off`, each containing
only: `engine/` (full copy), the GTFS-time oracle tests
`tests/unit/test_engine_basics.py` + `tests/property/test_midnight.py`, `.kiro/steering/`,
and `AGENTS.md`. **ON keeps `gtfs-domain.md`; OFF deletes it** (all other steering
identical in both).

1. In **both** copies, replaced `engine/gtfs.py::parse_gtfs_time`'s body with
   `raise NotImplementedError(...)`. Confirmed the oracle then fails identically in
   both (1 failed, 4 passed on the unit file; the property file errors at collection).
2. Ran, in each copy, the **identical** prompt:
   `kiro-cli chat --no-interactive --trust-tools=fs_read,fs_write`
   `"Implement the missing GTFS time parser in engine/gtfs.py"`
3. Ran the oracle in each copy with the repo venv:
   `.venv/bin/python -m pytest tests/unit/test_engine_basics.py tests/property/test_midnight.py`.

## What actually happened

| | ON (`gtfs-domain.md` present) | OFF (`gtfs-domain.md` deleted) |
|---|---|---|
| kiro-cli read the existing tests first? | yes | yes |
| Wrote the file? | **yes** | **no — every write/edit/shell call denied** |
| Oracle on the **written** result | **12 passed** | n/a (still the stub → collection error) |
| Reasoned about the midnight rule? | yes (cited the no-wrap requirement) | **yes — derived it from `tech.md` + the existing tests**, without `gtfs-domain.md` |

**The OFF run hit a confound unrelated to steering.** Despite being launched with the
same `--trust-tools=fs_read,fs_write`, the OFF session's file-mutating tools (`fs_write`,
the AST rewrite, and `shell`) were all denied with
`tool permission approval is not supported in non-interactive mode` — so it could not
write its answer. The ON run, with the identical flags, *was* allowed to write. This is
an environmental/approval flake in the harness, **not** an effect of the steering file.
So we have exactly **one written sample (ON)**, which passed.

**To salvage the correctness question honestly**, the OFF agent's *proposed* code (from
its transcript — it printed a complete implementation) was applied to an eval-only copy
and run through the same oracle:

| Result | Oracle |
|---|---|
| ON — code kiro-cli **wrote** | **12 passed** |
| OFF — code kiro-cli **proposed** (applied by hand for eval only; not a 3rd run) | **12 passed** |

## Finding

On **this task**, steering made **no observable correctness difference**: both the ON
code and the OFF-proposed code preserved the midnight invariant (`24:30:00` → `88200`,
no modulo). The reason is instructive and honest: the no-wrap rule is **redundantly
encoded** elsewhere in the repo —
- `tests/unit/test_engine_basics.py` asserts `parse_gtfs_time("24:30:00") == 88200`,
- `tests/property/test_midnight.py` is a whole Hypothesis suite named after the bug,
- `engine/gtfs.py`'s own module/function docstrings state "never wraps",
- `.kiro/steering/tech.md` also carries the no-wrap rule.

The OFF agent read the tests and `tech.md` and inferred the invariant without
`gtfs-domain.md`. So this experiment did **not** isolate steering's value — it showed
that when an invariant is *also* pinned by tests, deleting one steering file does not
by itself reintroduce the bug. That is arguably the system working as designed (defence
in depth), but it means a clean steering on/off signal needs a rule that is **only** in
steering and **not** mirrored by a test.

## Verdict

- Keep `gtfs-domain.md` — it is cheap and it is the human-readable home of the rule.
- This single run is **not** evidence that steering is unnecessary; it is evidence that
  our **tests** already defend the midnight invariant, which is the stronger guarantee.
- **Follow-up (pending):** re-run with a rule present ONLY in `gtfs-domain.md` and in no
  test (e.g. the `calendar_dates` exception-type override, or the 800 m walk cap) and a
  harness that grants writes in both arms, to get a clean on/off signal. Record it here
  as a second data point.

## Honesty label

Single sample per arm; one arm could not write due to a harness permission flake; the
chosen task's invariant is mirrored by tests, weakening the on/off contrast. Treat as a
qualitative observation, not a measurement of steering's effect size.
