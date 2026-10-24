# Design — multi-feed

## Approach
Additive. Keep `Timetable.from_gtfs_dir(path, date)` exactly as-is (M1's single-feed
loader; all existing tests depend on it). Add `Timetable.from_gtfs_dirs(feeds, date, ...)`
that:
1. Loads each feed with the existing single-feed loader (so per-feed calendar/calendar_dates
   and midnight-safe parsing are reused verbatim — no duplicated logic).
2. Prefixes every id with `"<agency>:"` on the way into the merged Timetable
   (stop/trip/route/service + transfer endpoints).
3. Adds cross-agency walking `Transfer`s between stops of different agencies within
   `max_interagency_walk_m` (default 400 m), weight `ceil(d·1.3/80·60)` seconds.
4. Calls `index()` once at the end.

Routers are untouched: they already consume `Timetable` + `Transfer`, so a merged
Timetable "just works" through RAPTOR/CSA/brute force.

## Why prefix instead of namespacing by field
PVTA and FRTA both use small integer-ish stop_ids that WILL collide (`1053`). A string
prefix is the simplest collision-free key and keeps `reason` strings legible
(`frta:JWO`). The prefix is the agency marker MF-P2 checks.

## Cross-agency transfers only
Intra-agency transfers already come from each feed's `transfers.txt`. We add ONLY
different-agency pairs, so we never double-count or shadow a feed's own transfer rules.
O(n·m) over the two agencies' stops — fine at these sizes (FRTA ~206, PVTA ~1-2k).

## Risk / boundary
`engine/gtfs.py` is M1's file (`router-dev` owns `engine/**`). This change is purely
additive and leaves the single-feed path byte-identical; M1 should review before merge.

## Out of scope
Fare merging, shapes, and realtime. The router needs stops/trips/stop_times/transfers +
calendar; the extra Trillium files in the feed are ignored by the loader.
