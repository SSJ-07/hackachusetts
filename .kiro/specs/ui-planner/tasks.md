# ui-planner — Tasks

- [x] 1. API client + types: `postPlan`, `getProvenance`; `PlanRequest`/`PlanResponse`/`ProvenanceResponse` mirrors (`web/src/api/`). _UP-3, UP-6_
- [x] 2. `planner.*` i18n namespace (EN + ES), grade-6 reading level; barrier text under `planner.barrier.*` from `barrier_questions.yaml`. _UP-2.2, UP-7.2_
- [x] 3. `BarrierCheck` — 6-step tap flow, back/change, maps to the `barriers` shape incl. `work_shift` + `childcare_window`. _UP-2_
- [x] 4. `PlanView` — ranked options in contract order each with its reason; itinerary; phone-sized preview; PT-1 summary. _UP-3, UP-4, UP-5_
- [x] 5. `ProvenanceDrawer` + chip wiring — source→vintage→requirement→properties→status from `/provenance`; Esc close, focus restore. _UP-6_
- [x] 6. `Planner.tsx` phase state machine (pick → barriers → plan), loading/empty/error states, illustrative labels. _UP-1, UP-7_
- [x] 7. Accessibility pass — keyboard, labels, contrast tokens, not-colour-only, large-type mode. _UP-P4, UP-P5, accessibility.md_
- [x] 8. `web/e2e/planner.spec.ts` — Playwright flow (Maria → escort → itinerary) + axe; ES run. _UP-P1..P5_

Status: Planner screen built against the stubbed `/plan` + `/provenance`. Real `/plan`
routes once the data cache is present (VP-11); real `/provenance` reads `docs/provenance.jsonl`.
The access-resources-mcp rural-options surfacing waits on Bryan's MCP server.
