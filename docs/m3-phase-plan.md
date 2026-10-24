# M3 (Bryan) — Phase A/B plan: FRTA, validation, equity, report

Grounded in the repo at `ddb7029` + `origin/main` (`f7fc0c2`, includes PR #13).
Guardrails for every step: logistics only, synthetic patients only, every number
has a source + vintage, patient-facing text only from human-reviewed templates,
`.kiro/` committed, journal entry per unit of work (`scripts/log_kiro.py`).

## Step 0 — sync (5 min)
- `git merge origin/main` into `M3-Bryan`. Main now has `pipeline/merge_cubes.py`
  and `build_cube.py --out` (per-clinic files under `data/cache/cubes/`).

## Phase A

### A1. Greenfield FRTA cube  → multi-feed task 7b
State: loader done, `CHCFC_GREENFIELD → frta:2505676` already in `clinic_stops.csv`,
cube already built once locally (42,504 cells, 11.3% reachable).
1. Put the FRTA feed in the cache: `data/cache/frta/` (copied from
   `data/manual/frta_minigtfs/`, which stays the committed source of truth).
   Add the copy step to `scripts/get_data.py` (idempotent, manifest + sha256) so
   Sumedh's `make data` picks it up. **Coordinate with Sumedh** (his file).
2. `build_cube.py` / `stops_walk.py`: read FRTA from `data/cache/frta`, fall back
   to `data/manual/frta_minigtfs`.
3. `python pipeline/build_cube.py --clinic CHCFC_GREENFIELD --out data/cache/cubes/CHCFC_GREENFIELD.parquet`
   then `python pipeline/merge_cubes.py`.
4. Check: merged cube has every clinic; BAY_GI still ~31.1% (PVTA unchanged).
5. Tick 7b in `.kiro/specs/multi-feed/tasks.md` with the real numbers.
Done when: merged cube contains Greenfield; tests green.

### A2. GTFS validator reports  → `docs/validation/`
Tool: MobilityData `gtfs-validator` CLI jar (Java 21 is installed). Pin the jar
version; keep the jar in `data/raw/` (git-ignored), not committed.
1. Run on `data/raw/pvta_gtfs.zip` and a zip of the FRTA feed.
2. Commit `docs/validation/{pvta,frta}/report.json` + `docs/validation/README.md`
   (validator version, feed sha256, date, counts of errors/warnings).
3. Triage each ERROR: if it changes routing, fix it in the loader (never edit the
   published feed) and add a test; else document why it is harmless.
Done when: both reports committed, every error fixed or explained.

## Phase B

### B3. Equity confidence intervals  → `engine/equity.py`
Blocker: `data/raw/acs_bg.csv` has estimates only (`_E`), no margins (`_M`).
1. `get_data.py`: also pull the `_M` columns for B25044, B01003, B01001, C16002
   (**Sumedh's file — coordinate**). `build_origins.py` carries `*_moe` columns.
2. `engine/equity.py` (pure, typed), Census ACS method:
   - MOE of a sum: `sqrt(Σ MOE_i²)`.
   - Share `p = X/Y`: `MOE_p = sqrt(MOE_X² − p²·MOE_Y²) / Y`; if the radicand is
     negative, use `+` (Census rule).
   - 90% CI = `p ± MOE_p`, clipped to [0, 1]. Source: Census "Understanding and
     Using ACS Data" handbook (cite in `docs/methods.md`, with vintage).
   - Splits: EJ, limited-English, 65+, zero-vehicle.
3. `/audit` adds `equity_ci: {group: {share, lo, hi, moe, n}}`. Update
   `docs/contracts.md` + contract tests **in the same PR**, and tell the team.
4. Properties (Hypothesis): `lo ≤ share ≤ hi`; `0 ≤ lo`, `hi ≤ 1`; MOE 0 ⇒ lo = hi.
Done when: `/audit` returns `equity_ci`; properties + contract tests green.

### B4. `/report` CHNA PDF  → spec `audit-report-pdf`
1. Spec `.kiro/specs/audit-report-pdf/` (requirements / design / tasks).
2. `api/routers/report.py`: `GET /report?clinic=...` → `application/pdf`, one page
   per clinic. Numbers come from the same function as `/audit` (no copies), plus
   `equity_ci` (B3), sources + vintage, and a short method box.
3. WeasyPrint (pinned). **Risk:** it needs GTK/Pango — on Windows install the
   GTK runtime; in CI add the apt packages. Tests skip cleanly if the libs are absent.
4. Tests: bytes start `%PDF`; page count = clinics; every number in the PDF equals
   `/audit`; no banned wording.
5. Run the `content-reviewer` agent (`kiro-cli chat --agent content-reviewer`)
   on the report text; fix what it flags.
Done when: PDF renders for the demo clinics; reviewer pass logged.

### B5. Visit-planner tasks 17 + 18 (VP-23 plan B, VP-24 driver windows)
Note: the spec IDs are VP-23/VP-24; "17/18" are the task numbers.
1. `plan_b` templates: `planner/templates/{en,es}/plan_b.md`, grade 6, logistics
   only. Added to `signoff.json` as `reviewed: false` until a human signs.
2. Driver-window data: `data/manual/volunteer_driver_windows.csv`
   (`town, provider, days, start, end, notice_days, source_url, verified_by, date`),
   from web-published COA/FRTA pages only. Unknown → labelled gap, never guessed.
3. Wire into `planner/` only: ride options only inside a driver window (incl.
   travel); `plan_b` text only from a signed template.
4. Properties: ride ⇒ inside a window; `plan_b` ∈ signed templates; escort ⇒ never
   transit-only still holds; no clinical/eligibility words.
5. Extend `scripts/validate_manual.py` to cover the new CSV.
Done when: tasks 17 + 18 ticked; properties green.

### B6. Citations and sign-offs (manual-data 4.3, 6.3, 7.2, 7.3, 7.6)
| Task | State | Action |
|---|---|---|
| 7.2 FIT stat | 50% locked in `docs/sources.md` | tick it |
| 7.3 CHNA transport page | cited via a Baystate RFI, not the CHNA PDF page | find the CHNA PDF page, cite page number |
| 4.3 / 6.3 ES sign-off | `signoff.json` says reviewer "Bryan" | valid only if the reviewer is fluent in Spanish; else get one |
| 7.6 escort policy | per-clinic not confirmed | use web-published prep/discharge pages (no calls) |

## Order and dependencies
```
0 sync ─> A1 ─> A2
          B5, B6        (independent; start any time)
B3 (needs ACS MOE from Sumedh) ─> B4 (report shows CIs)
```
Rough cost: A1 ~30 min (5 min cube), A2 ~1 h, B3 ~3 h, B4 ~3 h, B5 ~2 h, B6 ~1 h.

## Needs from others / from you
- Sumedh: OK to edit `get_data.py` (FRTA copy + ACS `_M` columns).
- Team: heads-up on the `contracts.md` change (`equity_ci`).
- You: a fluent-Spanish reviewer for the ES templates, if that is not you.
- You: install the GTK runtime for WeasyPrint on Windows (or build the PDF in CI only).
