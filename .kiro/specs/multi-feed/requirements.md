# Requirements — multi-feed (PVTA + FRTA into one Timetable)

Branch: `feat/multi-feed`. Owner: M3 (engine edits coordinated with M1).
The rural differentiator: FRTA service into the same round-trip router as PVTA.

## Introduction
`engine/gtfs.py` loads one GTFS directory into a `Timetable` (`from_gtfs_dir`). This spec
adds loading MULTIPLE feeds (PVTA at `data/cache/pvta`, FRTA at
`data/manual/frta_minigtfs`) into ONE `Timetable`, so a single `round_trip` can combine a
PVTA leg with an FRTA leg. Additive only: the existing single-feed path and all current
tests stay unchanged. Guardrails: times never wrap (RT-6); deterministic; pure function.

## Requirements

### MF-1 — one merged Timetable, agency-prefixed ids
WHEN two or more feeds are loaded for a service date THE loader SHALL return one
`Timetable` whose stop_ids, trip_ids and route_ids are prefixed by a per-feed agency key
(e.g. `pvta:1053`, `frta:JWO`). No raw id from one feed SHALL collide with another's.

### MF-2 — per-feed calendars
THE loader SHALL resolve each feed's `calendar.txt` + `calendar_dates.txt` INDEPENDENTLY
for the service date (a trip is included only if its own feed marks its service active).

### MF-3 — cross-agency walk transfers
THE loader SHALL add walking `Transfer`s between stops of DIFFERENT agencies whose
great-circle distance ≤ `max_interagency_walk_m` (default 400 m), with
`min_transfer_time = ceil(dist_m × 1.3 / 80 × 60)` seconds (consistent with
`pipeline/stops_walk.py`). It SHALL NOT add intra-agency transfers already in the feeds.

### MF-4 — midnight safety preserved
THE merged loader SHALL keep all times as seconds since local midnight, never wrapping
≥ 86400 (RT-6 / steering gtfs-domain.md).

## Non-functional / properties (PBT)
- **MF-P1 (never worse):** for any query, `round_trip` on {PVTA+FRTA} is reachable whenever
  `round_trip` on {PVTA only} is reachable (adding a feed never removes a PVTA journey).
- **MF-P2 (agency kept):** every stop/trip/route id in a merged result carries exactly one
  known agency prefix; no unprefixed or double-prefixed ids.
- **MF-P3 (no-service identity):** on a date where FRTA has NO active service, a merged
  `round_trip` result is byte-identical to the PVTA-only result.

## Golden
- **MF-G1:** one hand-checked Greenfield FRTA trip, verified against
  `data/manual/frta_minigtfs/stop_times.txt`, reproduced by the router.

## Traceability
| Req | Verified by |
|---|---|
| MF-1, MF-2 | `tests/unit/test_multifeed_loader.py` |
| MF-3 | `tests/unit/test_multifeed_loader.py::test_interagency_transfers_within_400m` |
| MF-4 | `tests/property/...::test_merged_midnight_never_wraps` |
| MF-P1..P3 | `tests/property/test_multifeed_properties.py` |
| MF-G1 | `tests/golden/test_frta_greenfield_golden.py` |
