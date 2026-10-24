# planner/

Visit Planner: turns a high-stakes visit + barrier answers into a plan that can happen.

- `visit_rules.yaml` — visit-type rulebook (duration, escort?, telehealth-OK?, prep, recurrence)
- Barrier check (6 questions, based on CMS AHC HRSN + PRAPARE)
- Constraint solver → ranked options (slot / ride / tele / prep / none)
- Itinerary + last bus home + PT-1 pre-fill
- `templates/{en,es}/*.md` — human-reviewed patient templates (+ `signoff.json`)

Owner: M4 (solver + API), M3 (rules + templates).
