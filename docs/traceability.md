# Traceability — every on-screen number: source → requirement → property → status

> Owner: M4 (with M1). This is the human-readable view. The machine-readable records
> the `GET /provenance?id=…` endpoint serves in real mode live in
> [`docs/provenance.jsonl`](provenance.jsonl) (one JSON record per id). Keep the two in
> sync: a row here = a line there, same `id`.
>
> **Status** is one of `pass` / `fail` / `pending`, matching the test outcome for that
> property. A number is only presentable when its properties are `pass`. Numbers from
> templates or demo assumptions are labelled "illustrative" and never stated as findings
> (AGENTS.md guardrail 3).

## Visit Planner (M4)

| id | Source (+ vintage) | Requirement | Property | Status |
|---|---|---|---|---|
| `planner-escort-colonoscopy` | ASGE escort-home standard; `planner/visit_rules.yaml` colonoscopy.source — ASGE 2023 | VP-5 | escort ⇒ never transit-only | pass |
| `planner-shift-no-overlap` | Planner shift rule (travel included); `solver.shift_intervals` — spec VP-6 | VP-6 | no recommended slot overlaps the shift, travel included | pass |
| `planner-telehealth-gated` | Rulebook `telehealth_ok`; `planner/visit_rules.yaml` — schema v1 | VP-8 | telehealth only if the visit type allows it | pass |
| `planner-itinerary-integrity` | Planner itinerary build; engine round-trip legs — spec VP-14 | VP-14 | itinerary integrity (`last_bus_home` is truly last) | pass |
| `planner-pt1-prefill` | MassHealth PT-1 field inventory; `data/manual/pt1_fields.json` — TRN-33 2017; APB-339 2022 | VP-15 | PT-1 pre-fill from a data-driven field list | pass |
| `planner-logistics-only` | Logistics-only guardrail; `planner/guardrails.py` — AGENTS.md guardrail 1 | VP-16 | output never contains clinical/eligibility wording | pass |
| `planner-no-silent-mocks` | Data-mode dependency gate; `api/deps.py` — spec VP-18 | VP-18 | real mode never falls back to mock data | pass |
| `planner-slots-illustrative` | Demo clinic schedule (`is_template=TRUE`); `data/manual/clinic_schedules.csv` — 2026 demo assumptions | VP-1 | candidate slots carry illustrative labelling | pass |

## Audit / routing (M1, M2)

_To be filled by M1 (raptor-router spec: round-trip soundness, midnight safety) and M2
(reachability cube, optimizer) as those provenance records land in `provenance.jsonl`._
