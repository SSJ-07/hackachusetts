# connection-scan — Requirements (Quick Spec)

> A second, independent router used to differentially verify `raptor-router`.
> Also ships the brute-force oracle used as ground truth on tiny feeds.

- **CS-1 (same interface).** THE CSA router SHALL expose the same public surface as
  `engine.raptor`: `round_trip(tt, origin, clinic, date, start, minutes, limits)` and
  `earliest_arrival(tt, from_stops, date, depart_after, limits)`, returning identical
  `RoundTripResult` / `{stop: (arrival, legs)}` shapes.
- **CS-2 (connection scan).** THE CSA router SHALL expand the feed into elementary
  connections sorted by departure time and compute earliest arrival in a single scan using
  trip reachability.
- **CS-3 (limits).** THE CSA router SHALL honour the same limits as RAPTOR (transfers, leg
  duration, transfer-minimum, walk, earliest-home).
- **CS-4 (differential equality).** FOR every random tiny feed, THE CSA router SHALL produce
  the same reachability AND the same earliest-arrival times as both RAPTOR and the
  brute-force oracle.
- **CS-5 (oracle).** THE brute-force router (`engine/brute_force.py`) SHALL be correct by
  construction (exhaustive label-setting) on tiny feeds and serve as ground truth.

## Traceability
| Requirement | Verified by |
|---|---|
| CS-1, CS-2, CS-3 | `engine/csa.py`, `engine/brute_force.py` |
| CS-4 | `tests/differential/test_routers_agree.py` (240 agreeing queries + earliest-arrival equality) |
| CS-5 | brute force is the oracle in the same differential tests |
