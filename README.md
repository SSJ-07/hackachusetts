# Slot-to-Stop: Reachable Care

> We show western Massachusetts health systems **which of their own appointments their
> patients physically can't get to**, and then plan the high-stakes visits so they
> actually happen.

Hackachusetts 2026 · Healthcare & Biotech · Challenge 3 ("A referral is not a finished visit")

## Two modes, one routing engine

- **Clinic Audit** — for every clinic hour in a weekly schedule, compute what share of
  car-less adults in each neighborhood can get there *and back* by bus. Drag a clinic
  block or add a satellite day to see the fix.
- **Visit Planner** — for high-stakes visits (colonoscopy after a positive FIT, prenatal,
  dialysis, chemo), run a barrier check and build a plan that can actually happen.

## Repo layout

```
slot-to-stop/
├── .kiro/          Kiro steering, specs, hooks, agents, skills, MCP config (COMMITTED)
├── AGENTS.md       Always-on agent rules
├── engine/         GTFS ingest, RAPTOR, CSA, brute force, reachability cube, optimizer
├── planner/        Visit rules, barrier check, constraint solver, itinerary
├── api/            FastAPI app
├── web/            React app
├── mcp/            gtfs-mcp, reach-mcp, access-resources-mcp
├── power/          Publishable Kiro power
├── data/           raw/ + cache/ (git-ignored) + fixtures/ (committed)
├── tests/          unit, property, differential, golden trips
├── docs/           kiro-journal, traceability, methods, decisions, contracts
└── .github/        CI workflows
```

## Run steps

```bash
make data    # download + build data caches
make demo    # load the frozen demo snapshot
make dev     # run API + web
```

## Guardrails

- **Logistics only.** No clinical or eligibility decisions.
- **Synthetic patients only.** No real PHI.
- **Every number carries a source and vintage.** Template values are labelled "illustrative".
- **`.kiro/` is committed, never git-ignored.**

## Kiro Scorecard

_Populated as we go: specs, tasks, properties, counterexamples → bugfix specs, hooks,
MCP calls, Web PRs, Crew alerts._
