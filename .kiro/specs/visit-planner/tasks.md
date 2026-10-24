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
- [x] 11. Wire `engine.round_trip` in real mode via `TimetableRoundTrip` (loads PVTA `Timetable` once per date, resolves origin_bg→centroid + clinic_id→stop, calls the one authoritative `engine.round_trip`). Cache-gated: real-mode `/plan` routes when `data/cache/pvta` + `origins.parquet` + `clinic_stops.csv` are present, else 503; real-data tests `skipif(not cache)` so CI stays green. _VP-6_
- [x] 12. Load candidate slots from `data/manual/clinic_schedules.csv`; service→visit-type map; illustrative labelled (`planner/slots.py`). _VP-1_
- [x] 13. Real mode reads M3's `pt1_fields.json` (inventory adapter) + real `visit_rules.yaml`; file shapes confirmed (`planner/pt1.py::load_fields_inventory`, `api/deps.py`). _VP-2, VP-15_
- [x] 14. Childcare window: added optional `childcare_window: [start, end]` to `POST /plan` (contracts.md §3); solver treats it as a second no-go band alongside the work shift; property P20 + unit tests. _VP-20_
- [x] 15. Use `cost_worry` / `has_transport` as navigator-facing option flags (fixed kind order unchanged). _VP-21_
- [x] 16. Recurrence PLAN on the top option (per_week, same-trip-each-session, PT-1-once for rides) from `recurrence_per_week`; property P22. _VP-22_
- [x] 17. `plan_b` from reviewed templates (M3). `planner/plan_b.py` + `planner/templates/{en,es}/plan_b.md`
  (situations `later_bus` / `last_bus`); used only when `signoff.json` marks that language reviewed, no
  language fallback. Ships `reviewed: false`, so `plan_b` stays null until a human signs. _VP-23_
- [x] 18. Volunteer-driver windows for rides (M3 data). `data/manual/volunteer_driver_windows.csv`
  (web-sourced; unpublished hours are labelled gaps, never used) + `planner/driver_windows.py`.
  `plan_visit(..., driver_windows, patient_town)`: a ride is `ride_mode: volunteer_driver` with a `window`
  only when a sourced window for the town covers the whole trip, else `pt1_broker`. Windows never add or
  drop options. Not wired into the API yet (needs a patient-town input): planner/ only. _VP-24_
- [x] 19.* Property: itinerary integrity — `last_bus_home` is truly last (plan B vs A waits on M3 templates, VP-23). _VP-14_

Status: **H6 target met with mocks**. Maria (synthetic) gets an escort-aware ride at 15:30,
a Spanish prep option and a PT-1 pre-fill using the stubbed router. Open items wait on
real data (M1/M2/M3) or a contract change.
