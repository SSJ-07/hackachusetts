# ADR 005 — Experiment ⑤ (protocol only): Kiro IDE vs Kiro Web Autonomous

- **Status:** pending — needs a human run (protocol fixed here; no result yet)
- **Question:** For one well-scoped, self-contained task, how does driving Kiro in the
  **IDE** (interactive, human-in-the-loop per step) compare to **Kiro Web Autonomous**
  (fire a task, it runs unattended and opens a PR) — on correctness, how much the human
  had to intervene, and wall-clock?

## The task (same for both surfaces)

Pick ONE bounded task that touches code + tests and has an objective pass bar, so both
surfaces are judged against the same oracle. Recommended candidate:

> **"Add `service_changes` real logic to `mcp/gtfs-mcp` (currently it leans on the
> engine) — return the set of service_ids added/removed for a date vs the prior week,
> with a unit test, obeying `.kiro/steering/gtfs-domain.md` (calendar + calendar_dates)
> and the provenance rule (every number carries a source)."**

Any task works as long as it is identical across both arms, has a committed spec or
clear acceptance, and its pass bar is a test that already exists or is part of the task.

## Fixed prompt (both arms)

> Use the task's own spec/acceptance verbatim as the prompt, so IDE and Web get the
> same instruction. Do not hand the Web arm extra context the IDE arm did not get.

## Metrics to log (identical for both; append results to THIS file)

1. **Correctness:** `.venv/bin/python -m pytest -q` → `N passed / M failed`, plus the
   specific new test's result. Log for each arm's final state.
2. **Human interventions:** count of times the human had to step in.
   - **IDE:** number of tool-approval clicks + number of corrective follow-up prompts.
   - **Web Autonomous:** number of times the run stalled/asked, + whether the opened PR
     needed human commits on top before it was green (count those commits).
3. **First-try PR quality (Web) / first-try diff quality (IDE):** did CI
   (`.github/workflows/kiro-ci.yml`) pass on the first push? Log green/red + the first
   failing job if red.
4. **Diff size + scope creep:** `git diff --stat`; did the arm touch files outside the
   task's owned set? Log any out-of-scope file.
5. **Steering adherence unprompted:** did it honour `gtfs-domain.md`
   (calendar_dates override) and the provenance rule without being told? yes/no each.
6. **Wall-clock:** prompt → CI-green PR (Web) / prompt → local-green diff (IDE).
7. **Autonomy failure modes (Web only):** did it fake a result, claim success without
   running tests, or leave a half-build? (cross-check against the repo's "never claim a
   thing ran unless you ran it" rule). Log verbatim any unverified success claim.

## Hypothesis (to confirm or refute)

IDE needs more human clicks but fewer wrong turns (human catches drift early); Web
Autonomous needs zero babysitting but is more likely to over-reach or claim success it
did not verify, so its PR needs ≥1 corrective commit. **Guess only — the run decides.**

## Honesty label (applies to the eventual result)

Single task, single run per surface, same author. Anecdote, not a benchmark. Keep the
IDE diff and the Web PR link so both are inspectable.
