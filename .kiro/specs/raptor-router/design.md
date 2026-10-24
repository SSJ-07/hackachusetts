# raptor-router — Design

## Overview
RAPTOR (Round-bAsed Public Transit Optimized Router) computes earliest arrival by
*rounds*: round `k` holds the earliest arrival at each stop using at most `k` vehicle
trips. A round-trip query runs the router twice — once outbound (origin → clinic, bounded
by the check-in deadline) and once for the return (clinic → home, bounded below by the
visit end).

## Data model
- `engine/gtfs.py::Timetable` — an in-memory feed resolved to one service date. Pure
  Python (no pandas) so a tiny feed can be built by hand in tests and the router is
  testable in isolation (RT-15).
- Times are integer seconds since local midnight; parsing preserves `>= 86400` (RT-6).
- `_active_services(path, date)` resolves `calendar` + `calendar_dates` (RT-7).

## RAPTOR core (`_run_raptor`)
1. Seed `best[stop] = (arrival, legs)` from the source stops (origin walk links).
2. Round 0: transitive foot-transfer closure from the sources (so a walk-only path, e.g. a
   `transfers.txt` edge origin→clinic, is found with zero rides).
3. For `k` in `1..max_transfers+1`:
   a. For every trip, board at the earliest already-reached stop whose `dep >= ready`
      (`ready` adds the min transfer time when the previous leg was a bus — RT-8), then
      relax arrival at every downstream stop, rejecting legs over `max_leg_seconds` (RT-10).
   b. Relax foot transfers out of every stop improved this round (transitive closure).
4. Return `best`.

## Round-trip assembly (`round_trip`)
- `must_arrive_by = start - checkin_buffer` (RT-2); `visit_end = start + minutes*60` (RT-3).
- Outbound: `one_way(origin→clinic, arrive_by=must_arrive_by)`.
- Return: `one_way(clinic→home, depart_after=visit_end)`; reject if the first bus departs
  before `earliest_home_dep` (RT-12). `last_bus_home` = that first bus's departure (RT-4).
- `reachable = out_legs and ret_legs`.

## Access resolution (`engine/synth.py::access_links`)
A stop_id resolves to itself (0 walk). A `(lat, lon)` resolves to every stop within
`max_walk_m` (RT-11), walk seconds = `haversine_m / walk_m_per_min * 60`.

## Oracles (see `connection-scan` spec)
- `engine/brute_force.py` — label-setting search over connections; correct by construction
  on tiny feeds; the ground-truth oracle.
- `engine/csa.py` — Connection Scan Algorithm; a structurally different second opinion.
- Differential tests assert RAPTOR == CSA == brute force (RT-14).

## Determinism (RT-13)
RAPTOR relaxes strictly on `arrival < best`, and ties resolve by stable iteration order, so
identical inputs give an identical result.
