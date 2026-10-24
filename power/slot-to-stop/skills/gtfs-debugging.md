# Skill: gtfs-debugging

Diagnose why a transit round trip comes back unreachable, and catch the classic GTFS traps.

## When to use
The user asks "why can't this patient get there", "this trip should be reachable",
"debug this GTFS feed", or a reachability result looks wrong.

## Tools
- `gtfs-mcp` → `round_trip(...)` returns `{reachable, out_legs, ret_legs, last_bus_home, reason}` —
  read `reason` first; it names the failing direction.
- `gtfs-mcp` → `plan_trip(...)` for a one-way leg in isolation.
- `gtfs-mcp` → `validate_feed()` for the feed's service window and validator report.
- `gtfs-mcp` → `service_changes(since)` to see added/removed service.

## Checklist (the usual culprits)
1. **Midnight / >24:00 times.** A trip departing `24:30:00` is `88200` seconds, never
   wrapped to `01800`. A return that "disappears" late at night is often this.
2. **Service calendar.** The query date's active `service_id`s come from `calendar.txt`
   AND `calendar_dates.txt` (exception 1 adds, 2 removes). A holiday exception can remove
   all service.
3. **Transfer minimum.** A connection missed by seconds is usually `transfers.txt`
   min-transfer-time, or the default when absent.
4. **Limits.** Check the leg isn't rejected for > 2h, > 2 transfers, a walk leg > 800 m, or
   a return departing before 05:30.
5. **Access links.** An origin/clinic with no stop within 800 m resolves to no boarding
   stop — the trip is unreachable by construction.

## Verifying a fix
Cross-check against the oracles: the engine ships RAPTOR, CSA and a brute-force router that
must agree. A divergence on a tiny feed is a router bug, not a data bug.
