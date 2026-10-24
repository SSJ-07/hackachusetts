# ADR 004 — Experiment ② (protocol only): spec-driven vs "vibe" coding

- **Status:** pending — needs a human run (protocol fixed here; no result yet)
- **Date:** 2026-10-24
- **Question:** For a small, self-contained UI unit, does writing a Kiro **spec first**
  (requirements + design + tasks) beat **vibe coding** (one free-text prompt, no spec)
  on quality the first time, and on how much rework the change causes?

## The two units under test

Same feature, built twice, by the same author, in two throwaway branches:

- **Spec arm — the Audit week-grid legend.** There is already a spec for the grid
  itself (`.kiro/specs/ui-week-grid/`). For this experiment, write a *fresh* minimal
  spec (`requirements.md` with `LG-n` ids + `design.md` + `tasks.md`) for a **colour +
  text legend** that explains the grid's reachability shading, obeying
  `.kiro/steering/accessibility.md` (the "no colour-only information" rule) and
  `ui-style.md`. Then implement to the spec.
- **Vibe arm — the same legend.** One prompt, no spec:
  `"Add a legend to the Audit week grid explaining the reachability colours."`
  Nothing else; let Kiro decide the shape.

Both arms target `web/src/routes/Audit.tsx` (+ a `Legend` component) in **separate
scratch copies of `web/`**, never the live tree.

## Fixed prompt (vibe arm)

> `Add a legend to the Audit week grid explaining the reachability colours.`

(Spec arm uses whatever the spec's tasks dictate; the point is the spec exists.)

## Metrics to log (identical for both arms)

Record each number with its source command, into a result section appended to THIS file.

1. **Accessibility compliance (the steering bar):** does every legend entry carry
   **text, not colour alone**? Measure with the existing discipline —
   `cd web && npx vitest run` and specifically whether a test like
   `Audit.test.tsx`'s "no colour-only cells" passes for the legend. Log: pass/fail +
   count of legend entries that are colour-only (must be 0).
2. **Build health first try:** `cd web && npx tsc -b` → exit code; `npx vitest run` →
   `N passed / M failed`. Log both, for the first build after generation (no fixups).
3. **Rework:** number of follow-up prompts needed to reach green (tsc clean + vitest
   green + 0 colour-only entries). Log the count and a one-line note per follow-up.
4. **Diff size:** `git diff --stat` lines added/removed in each arm.
5. **Steering adherence without being asked:** did the arm honour
   `accessibility.md` (focus ring, text labels, aria) and `ui-style.md` **unprompted**?
   Log yes/no per rule.
6. **Time to first green:** wall-clock from prompt to all checks green.

## Hypothesis (to confirm or refute, not assume)

Spec arm reaches green in fewer follow-ups and honours `accessibility.md` on the first
try (because the spec's requirements restate the rule); vibe arm is faster to a *first*
render but needs ≥1 follow-up to add text labels / aria. **This is a guess; the run
decides.**

## Honesty label (applies to the eventual result)

Single sample per arm, same author, one small feature. Report as an anecdote, not a
measurement. Keep both scratch branches so the diffs are inspectable.
