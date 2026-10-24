# visit-planner — Design

## Overview
A small, explicit constraint solver. Every candidate slot is checked against hard rules
read from the rulebook; survivors become options, ranked by burden. The solver is a pure
function; the API is a thin adapter that supplies data sources as FastAPI dependencies.

```
POST /plan ─► api/routers/plan.py ─► planner.solver.plan_visit(...)
                 │  deps (api/deps.py)          │
                 ├─ rules        ◄─ planner/visit_rules.yaml (M3) | api/mocks/planner/
                 ├─ candidate slots ◄─ clinic_schedules.csv (M3, TODO) | mocks
                 ├─ round_trip   ◄─ engine.round_trip (M1, TODO) | FixtureRoundTrip
                 └─ PT-1 fields  ◄─ data/manual/pt1_fields.json (M3) | mocks
```

## Modules
| Module | Role | Requirements |
|---|---|---|
| `planner/models.py` | `VisitRule`, `Patient`, `Barriers`, `CandidateSlot`, `Option`, `Itinerary`, `Plan`; re-exports engine `Leg`, `RoundTripResult` | VP-1, VP-11 |
| `planner/rules.py` | Parse rulebook schema v1; `null` kept as `None` | VP-2, VP-3 |
| `planner/transit.py` | `RoundTripFn` protocol, `travel_window`, `FixtureRoundTrip` stub | VP-6, VP-7 |
| `planner/solver.py` | `plan_visit`: rules → checks → options → ranking → itinerary → PT-1 | VP-3..VP-15 |
| `planner/pt1.py` | PT-1 field list (data) + `prefill` | VP-15 |
| `planner/guardrails.py` | Banned-pattern check on every emitted string | VP-16 |
| `api/deps.py` | Data mode `mock` / `real`; 503 when a real source is missing | VP-18 |
| `api/routers/plan.py` | Request → solver inputs; Plan → response; 422 / 500 mapping | VP-4, VP-11, VP-16 |

## Algorithm (`plan_visit`)
1. **VP-3:** if the rule is incomplete → `[none(rules_unverified)]`.
2. Shift → second intervals on the service day and the next day (overnight safe).
3. For each unique candidate: `round_trip(origin_bg, clinic, date, start, duration)`;
   `window = (out_legs[0].dep, ret_legs[-1].arr)` if complete; `conflict = overlap(window, shift)`.
4. Sort candidates by `(known window first, door-to-door, date, start, clinic)`.
5. **Escort required:** `ride` for each non-conflicting candidate; a candidate without a
   window is kept only when there is no shift (VP-7). The transit trip is a conservative
   travel-time proxy for the shift check.
   **Otherwise:** `slot` for each candidate with a window and no conflict.
6. `tele` if `telehealth_ok` (VP-8). Sort by kind rank, then candidate key (VP-12).
7. No attendable option → single `none` with a specific reason (VP-10). Else add `prep`
   if `prep` (VP-9).
8. Itinerary from the top `slot` (VP-14); PT-1 from the top `ride` (VP-15).
9. Guardrail over every `why` and `details` string (VP-16).

## Correctness properties (Hypothesis, `tests/property/test_planner_properties.py`)
| Property | Statement | Req |
|---|---|---|
| P15 | For any inputs, WHEN `escort_required` is not false, THE plan has no `slot` and an empty itinerary | VP-5, VP-3 |
| P16 | For any recommended `slot`/`ride`, its door-to-door window contains no minute inside the shift (independent minute-by-minute oracle) | VP-6, VP-7 |
| P17 | For any plan containing `tele`, `telehealth_ok` is true | VP-8 |
| P18 | For any plan, no emitted string matches the banned clinical/eligibility patterns | VP-16 |
| P-rank | For any inputs and any permutation of candidates, the plan is identical | VP-13 |
| P-none | `none` appears only alone, and a plan is never empty | VP-10 |

Generators: rules (complete, plus ~1 in 4 with nulls), shifts incl. overnight and
`start == end`, up to 6 unique candidates over 2 clinics × 2 dates, round trips that are
unreachable or reachable with home arrival possibly `> 86400`.

## Error handling
| Condition | Result |
|---|---|
| Rulebook missing/malformed | 503 |
| Real source not landed (`real` mode) | 503 |
| Unknown `visit_type` | 422 with known types |
| Invalid request (extra field, bad GEOID, bad shift) | 422 |
| Guardrail violation | 500, plan withheld, logged |

## Decisions
- `none` reasons and `why` strings are coordinator-facing, not patient-facing. Patient text
  comes only from reviewed templates (M3), so `plan_b` is `null` until those exist.
- Ride `details`: `slot`, `clinic_id`, `escort_required`, `has_escort`, `pt1_request`. The
  contract example's `window` (volunteer driver) waits on VP-24 data.
