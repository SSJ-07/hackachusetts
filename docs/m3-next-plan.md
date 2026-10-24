# M3 next-tasks plan — multi-feed FRTA, real MCP, data-quality CI, gap closeout

Owner: M3 (Bryan). Branch: cut `feat/multi-feed` off `main` (main already has your merged
PR #3 + M1/M2/M4 work). Commit `.kiro/` constantly. `main` is protected — PR + green CI.

## Ordering & why
Do them in dependency order, not listed order: **3 → 2 → 1 → 4** is safest, but task 1 is
the differentiator, so if time is tight do **1** first and **3** last.
- Task 3 (CI validator) is cheap and protects every later edit — land it early.
- Task 2 (MCP) only reads existing files you already finished — low risk, high demo value.
- Task 1 (multi-feed router) is the hard one and touches M1's `engine/` — coordinate.
- Task 4 (gaps) is paperwork you can do anytime.

Each task = its own spec + branch + PR. Sync with M1 before touching `engine/`.

---

## Task 1 — FRTA into the router (the rural differentiator)
**Scope boundary:** `engine/gtfs.py` is M1's file (steering `router-dev` agent writes
`engine/**`). Pair with M1 or get explicit sign-off before editing. You own the DATA
(`frta_minigtfs/` ✅ already landed) and the clinic/cube wiring.

**Spec `multi-feed` (Requirements-First), EARS acceptance:**
- MF-1 WHEN both feeds load THE Timetable SHALL contain PVTA and FRTA trips in one
  structure, ids prefixed by agency (`pvta:1053`, `frta:<id>`) — no id collisions.
- MF-2 THE loader SHALL resolve each feed's own `calendar.txt` + `calendar_dates.txt`
  independently (FRTA service window 2026-03-01..2027-02-28; see its `calendar.txt`).
- MF-3 THE loader SHALL add walking transfers between stops of DIFFERENT agencies within
  **400 m** (straight-line × 1.3 / 80 m-per-min, consistent with `stops_walk.py`).
- MF-4 Times past midnight stay unwrapped (`24:30:00`→88200), per `tech.md` / raptor RT-6.

**Properties (PBT, approve in IDE):**
- Adding FRTA never makes a PVTA-only trip worse (monotone-in-access; mirrors RT "monotone").
- Every merged trip keeps its agency prefix (no orphan ids).
- `round_trip` results are byte-identical to PVTA-only when FRTA has no service that day.

**Golden test:** one hand-checked Greenfield FRTA trip vs the feed's `stop_times.txt`
(now that we have the real feed, check against the feed, not a PDF). Add to `tests/golden/`.

**Then wire the demo:**
1. Add `CHCFC_GREENFIELD` to `data/manual/clinic_stops.csv` — needs a real FRTA `stop_id`
   near 102 Main St, Greenfield. Pull it from `frta_minigtfs/stops.txt` (JWO Transit Center
   or a High St stop), record `source`, `is_demo_anchor=TRUE`.
2. `python pipeline/build_cube.py` for CHCFC Greenfield → `data/cache/cube.parquet` rows.

**Rubric payoff:** directly answers the judges' "it ignores rural towns" critique (§0);
feeds the equity/rural lens; multi-oracle PBT is Best-Use-of-Kiro evidence.

---

## Task 2 — Make `access-resources-mcp` real
**File:** `mcp/access-resources-mcp/server.py` (currently a stub returning
`not_implemented`). It reads YOUR finished data — zero new data work.

**Implement the 3 tools + 1 resource against real files:**
- `rural_options(town)` → read `data/manual/rural_options.csv` + `rural_coverage.csv`;
  return the town's options + `coverage_tier` + `has_any_option`, each with `source_url`
  and `verified_by`/`date` as vintage.
- `pt1_prefill(patient_id, visit_type)` → map a SYNTHETIC patient to the field `key`s in
  `data/manual/pt1_fields.json` (keys are stable; we verified them). Fill values from the
  synthetic patient only. Never invent a real member id.
- `visit_rules(visit_type)` → read `planner/visit_rules.yaml`; return
  duration/escort/telehealth/prep/recurrence + the entry's `source` block as vintage.
- resource `access://rural-options` → the full rural table with source + date.

**Hard requirements (guardrails):**
- EVERY response carries `source_url` + `vintage` (your files already have these).
- NEVER return clinical or eligibility language — add a guardrail check + a test asserting
  no forbidden phrases (reuse `planner/guardrails.py` if its vocabulary fits).
- Tests in `tests/` (unit): each tool returns sourced data for a known town/visit_type and
  an empty-but-sourced response for an unknown one.

**Rubric payoff:** "real MCP with resources + sourced responses" is explicit Kiro-depth
evidence (§5 cheat-sheet: "use resources, prompts and elicitation, not just tools").

---

## Task 3 — Data-quality CI check (manual-data R9.2)
**File:** `scripts/validate_manual.py`, wired into `.github/workflows/kiro-ci.yml`.

**It FAILS (non-zero exit) if any `data/manual/*` row:**
- lacks a source (`source_url` / `source` empty or `TODO-VERIFY` where a value is present);
- has a malformed time (not `HH:MM`, or hour>23 unless a documented GTFS >24h file);
- has a `clinic_id` not present in `clinic_stops.csv` (referential integrity).

**Design notes:**
- Pure stdlib (csv/json/re) so CI needs no extra deps.
- Treat labelled placeholders (`TODO-VERIFY`, demo FICTIONAL rows) per-file: demo slots in
  `clinic_schedules.csv` are allowed to be templates but MUST keep `source_url`.
- Print a clear per-file, per-row failure list.

**CI wiring:** add a step in `kiro-ci.yml` BEFORE the pytest gate:
`python scripts/validate_manual.py`. Keep it failing-closed (no `|| true`).

**Rubric payoff:** enforces "every number has a source" in CI (ground rule #4 + §8
checklist "every on-screen number is computed and traceable").

---

## Task 4 — Close the gaps (paperwork)
- **ES sign-off:** DONE this session (signoff.json reviewed=true, accent-corrected ES).
  Re-confirm the reviewer name is correct for the record.
- **FIT follow-up stat:** DONE — locked to 50% @ 6mo (PubMed 39843790) in `docs/sources.md`.
- **CHNA transport page:** sourced (2019 verbatim quote + 2025 BFMC CHNA) in `sources.md`.
  OPTIONAL upgrade: open the 2025 BFMC CHNA PDF and add the exact page number.

So task 4 is largely already closed by this session's work — verify + optionally add the
CHNA page cite. Don't redo it.

---

## Cross-cutting rubric reminders (keep these true)
- **Commit `.kiro/` constantly** — specs (`multi-feed`), any steering, hooks. Judges grade it.
- **Log each unit of work** to `docs/kiro-journal/m3-bryan.md` via `scripts/log_kiro.py`
  (the journaling steering now requires it) — this becomes the write-up.
- **Never hard-code a number**; everything carries source + vintage; templates labelled.
- **Synthetic patients only.**
- **CI must stay green** (pytest + the new validator). PR into protected `main`.
- **Cut order (§9)** if behind: FRTA mini-GTFS was a stretch but is DONE; next to cut would
  be the optimizer, not this — task 1 (FRTA routing) is explicitly the rural differentiator,
  so protect it.

## Suggested branch/PR sequence
1. `feat/manual-data-ci` → task 3 → PR.
2. `feat/access-mcp` → task 2 → PR.
3. `feat/multi-feed` → task 1 (with M1) → PR.
4. fold task-4 verifications into whichever PR is open, or a tiny `docs:` PR.
