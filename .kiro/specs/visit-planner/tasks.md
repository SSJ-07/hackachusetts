# visit-planner — Tasks

- [x] 1. Planner value types; reuse engine `Leg` / `RoundTripResult` (`planner/models.py`). _VP-1, VP-11_
- [x] 2. Rulebook loader for schema v1 with `null` = unknown (`planner/rules.py`). _VP-2, VP-3_
- [x] 3. Transit interface, travel window, fixture stub for `engine.round_trip` (`planner/transit.py`). _VP-6, VP-7_
- [x] 4. Solver: escort, shift, telehealth, prep, none, ranking, itinerary (`planner/solver.py`). _VP-3..VP-14_
- [x] 5. PT-1 pre-fill from a data-driven field list (`planner/pt1.py`). _VP-15_
- [x] 6. Logistics-only guardrail (`planner/guardrails.py`). _VP-16_
- [x] 7. `POST /plan` router + data-mode dependencies, 503 in real mode (`api/routers/plan.py`, `api/deps.py`). _VP-4, VP-11, VP-18_
- [x] 8. Labelled mocks + synthetic Maria (`api/mocks/`). _VP-17_
- [x] 9. Unit tests (`tests/unit/test_planner_*.py`) and contract tests (`tests/contract/`). _VP-3..VP-19_
- [x] 10. Property tests P15–P18, P-rank, P-none (`tests/property/test_planner_properties.py`). _VP-5, VP-6, VP-8, VP-10, VP-13, VP-16_
- [ ] 11. Wire `engine.round_trip` in real mode. **Blocked:** `engine.round_trip(tt, ...)` exists, but needs a loaded PVTA `Timetable` + `data/cache/stops_walk.parquet` for origin_bg/clinic_id→stop resolution (M1/M2). Real mode 503s here until then. _VP-6_
- [x] 12. Load candidate slots from `data/manual/clinic_schedules.csv`; service→visit-type map; illustrative labelled (`planner/slots.py`). _VP-1_
- [x] 13. Real mode reads M3's `pt1_fields.json` (inventory adapter) + real `visit_rules.yaml`; file shapes confirmed (`planner/pt1.py::load_fields_inventory`, `api/deps.py`). _VP-2, VP-15_
- [ ] 14. Childcare window: agree a contract change with Sumedh, then add the check + property. _VP-20_
- [x] 15. Use `cost_worry` / `has_transport` as navigator-facing option flags (fixed kind order unchanged). _VP-21_
- [x] 16. Recurrence annotation on the top option from `recurrence_per_week` (e.g. dialysis per week). _VP-22_
- [ ] 17. `plan_b` from reviewed templates (M3). _VP-23_
- [ ] 18. Volunteer-driver windows for rides (M3 data). _VP-24_
- [x] 19.* Property: itinerary integrity — `last_bus_home` is truly last (plan B vs A waits on M3 templates, VP-23). _VP-14_

Status: **H6 target met with mocks**. Maria (synthetic) gets an escort-aware ride at 15:30,
a Spanish prep option and a PT-1 pre-fill using the stubbed router. Open items wait on
real data (M1/M2/M3) or a contract change.
