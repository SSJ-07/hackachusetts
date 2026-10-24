# raptor-router — Tasks

- [x] 1. Engine value types matching contracts.md §2 (`engine/types.py`: Leg, RoundTripResult, Limits).
- [x] 2. In-memory GTFS timetable with midnight-safe time parsing and calendar/calendar_dates resolution (`engine/gtfs.py`).
- [x] 3. Synthetic feed builders + access-link resolution for tests (`engine/synth.py`).
- [x] 4. RAPTOR core + round-trip assembly (`engine/raptor.py`): rounds, transfers, limits, last-bus-home.
- [x] 5. Brute-force oracle (`engine/brute_force.py`) — ground truth on tiny feeds.
- [x] 6. CSA second implementation (`engine/csa.py`).
- [x] 7. Differential tests RAPTOR == CSA == brute force (`tests/differential/`). 240 agreeing queries.
- [x] 8. Property tests: soundness, check-in buffer, midnight safety, causality, determinism, monotone-in-access (`tests/property/`).
- [x] 9. Golden grid round trip + GTFS unit tests (`tests/unit/`).
- [ ] 10. Golden PVTA trip hand-checked against the real timetable (waits on `data/raw/pvta_gtfs.zip` from M2).
- [ ] 11. Wire the real feed through `gtfs-mcp` `round_trip` / `plan_trip` (in progress — see `mcp/gtfs-mcp/server.py`).

Status: **core complete and cross-validated** (250 tests, 0.54s). Remaining items wait on
the real PVTA feed landing (M2) and are plumbing, not router logic.
