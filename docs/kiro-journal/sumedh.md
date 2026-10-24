# Kiro Journal — Sumedh (M1)

Per-person Kiro-usage log for Slot-to-Stop. Append only, newest at the bottom.
Write entries with: `python scripts/log_kiro.py --member sumedh --tool <IDE|CLI|Web|Crew> --topic <t> --what "..." [--kiro "..."] [--outcome "..."]`
Assemble the whole team's log with: `python scripts/log_kiro.py --assemble`

<!-- LOG ENTRIES BELOW — newest at the bottom -->

## 2026-10-24 15:33 · sumedh · Crew · topic: hooks
what: built the Kiro journal: 2 IDE hooks + scripts/log_kiro.py, logging to docs/kiro-journal.md
kiro: Crew authored the hook docs against the on-disk hook schema and a stdlib helper so Web/Crew work is logged too
outcome: helper verified; hooks travel via .kiro/ for teammates in the IDE

## 2026-10-24 15:33 · sumedh · Crew · topic: mcp
what: wired gtfs-mcp round_trip/plan_trip/validate_feed to the engine
kiro: one shared deterministic router every agent calls, on cached GTFS not a live API
outcome: imports clean, routes correctly

## 2026-10-24 15:33 · sumedh · Crew · topic: pbt
what: differential PBT: RAPTOR == CSA == brute-force oracle over 400 random feeds
kiro: the oracle caught two real router bugs (origin foot-transfers, CSA transfer-unlock) during bring-up
outcome: 3,200 agreeing queries; 250 tests green in 0.6s

## 2026-10-24 15:39 · sumedh · Crew · topic: other
what: added engine.latest_departure: reverse one-to-many profile search (backward RAPTOR) for M2's reachability cube
kiro: Crew built the symmetric backward search and a Hypothesis property proving it agrees with the forward earliest_arrival
outcome: 252 tests green; 626 reverse results verified vs forward oracle, 0 violations

## 2026-10-24 15:43 · sumedh · Crew · topic: hooks
what: made journaling work in Crew: always-on steering/journaling.md tells every agent to self-log via scripts/log_kiro.py
kiro: Crew has no file-save hook, so the steering rule (injected every session) makes the agent log its own work into per-person files
outcome: helper runs from any CWD; steering + per-person journal verified

## 2026-10-24 16:15 · sumedh · Crew · topic: pbt
what: golden PVTA trip on real feed exposed + fixed a transfer-limit bug (RAPTOR boarded from same-round stops, allowing >2 transfers)
kiro: ran round_trip on the live PVTA GTFS; the real network produced 4-6 bus journeys the synthetic feeds never did, revealing the bound was not per-round; fixed to read a frozen previous-round snapshot
outcome: 318 tests green; RAPTOR==CSA 0 disagreements on 120 real-feed queries; golden tests guard the regression

## 2026-10-24 16:27 · sumedh · Crew · topic: other
what: built M2's reachability cube (pipeline/build_cube.py) on real PVTA+ACS data; ran M2's build_origins/stops_walk to produce the caches
kiro: cube calls the engine's verified round_trip per cell (matches the oracle, 20/20); caught and discarded a profile-search shortcut that under-reported reachability 1.2% vs the true 31%
outcome: origins 506 bgs / 55,901 carless adults; 193 transit-desert bgs; cube 42,504 cells/clinic, 31% reachable to Baystate; cube==round_trip 20/20

## 2026-10-24 16:34 · sumedh · Crew · topic: other
what: Fixed reachability cube under-reporting (1.2% flat -> 31% varying by hour)
kiro: rebuilt pipeline/build_cube.py to call engine.round_trip per cell using block-group lat/lon instead of stop-membership join
outcome: Baystate GI cube: 7am 19% to noon 45% to 6pm 14%; cube==round_trip 60/60; 318 tests green
