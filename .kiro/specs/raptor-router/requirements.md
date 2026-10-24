# raptor-router — Requirements (EARS)

> Feature spec, Requirements-First. The authoritative round-trip transit router
> over GTFS. Consumed by the reachability cube, the Visit Planner, and the
> `gtfs-mcp` server. Shapes fixed by `docs/contracts.md` §2.

Each requirement has a stable id (`RT-n`) referenced by `/provenance` and tests.

## Functional requirements

- **RT-1 (round-trip soundness).** WHEN `round_trip(origin, clinic, date, start, minutes)`
  returns `reachable = true`, THE engine SHALL guarantee an outbound journey arriving
  `<= start - checkin_buffer` AND a return journey departing `>= start + minutes*60`,
  both on `date`, within all limits in RT-6..RT-10.

- **RT-2 (check-in buffer).** THE engine SHALL require the outbound arrival at the clinic
  to be no later than `start - 600` seconds (a 10-minute check-in buffer).

- **RT-3 (return after visit).** THE engine SHALL require the return journey to depart the
  clinic no earlier than `start + minutes*60` (the visit end).

- **RT-4 (last bus home).** WHEN a round trip is reachable, THE engine SHALL report
  `last_bus_home`: the departure time of the first bus leg of a valid return, or `null`
  when the return is walk-only.

- **RT-5 (legs and reason).** THE engine SHALL return `out_legs`, `ret_legs` (each a list of
  `Leg{kind,from_stop,to_stop,route_id,dep,arr}`) and a plain-language `reason`.
  WHEN not reachable, THE failing direction's legs SHALL be empty and `reason` SHALL say why.

## GTFS-correctness requirements

- **RT-6 (midnight / service-day safety).** THE engine SHALL treat all times as integer
  seconds since local midnight and SHALL NOT wrap times `>= 86400`. A `24:30:00` departure
  is `88200`, never `01800`.

- **RT-7 (service calendar).** THE engine SHALL resolve active `service_id`s for `date`
  from `calendar.txt` AND `calendar_dates.txt` (exception 1 adds, 2 removes), before
  building the timetable.

- **RT-8 (minimum transfer time).** WHEN a journey transfers between vehicles, THE engine
  SHALL enforce `transfers.txt` minimum transfer time, defaulting to a small transfer when
  absent.

## Limit requirements (configurable; defaults from `Limits`)

- **RT-9 (transfers).** THE engine SHALL use at most `max_transfers` (default 2) vehicle
  transfers per direction.
- **RT-10 (leg duration).** THE engine SHALL reject any single direction exceeding
  `max_leg_seconds` (default 2h).
- **RT-11 (walk distance).** THE engine SHALL only use walk links `<= max_walk_m`
  (default 800 m) to resolve origin/clinic to boarding stops.
- **RT-12 (earliest home departure).** THE engine SHALL reject a return whose first bus
  departs before `earliest_home_dep` (default 05:30).

## Non-functional requirements

- **RT-13 (determinism).** GIVEN identical inputs and feed, THE engine SHALL return an
  identical `RoundTripResult` (ties broken deterministically).
- **RT-14 (differential correctness).** THE engine SHALL agree with the brute-force oracle
  on every random tiny feed, and with the CSA implementation (see `connection-scan` spec).
- **RT-15 (purity).** THE router SHALL be a pure function of `(Timetable, query, limits)`,
  making no network calls (deterministic, cached data only — steering/tech.md).

## Traceability

| Requirement | Verified by |
|---|---|
| RT-1, RT-2, RT-3 | `tests/property/test_router_properties.py::test_reachable_result_is_sound`, `test_checkin_buffer_respected` |
| RT-6 | `tests/property/...::test_midnight_times_never_wrap`, `tests/unit/...::test_parse_gtfs_time_past_midnight` |
| RT-7 | `engine/gtfs.py::_active_services` (calendar + calendar_dates) |
| RT-8, RT-9, RT-10, RT-11, RT-12 | `engine/types.py::Limits`, enforced in `engine/raptor.py` |
| RT-13 | `tests/property/...::test_determinism` |
| RT-14 | `tests/differential/test_routers_agree.py` |
