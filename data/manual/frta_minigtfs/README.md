# data/manual/frta_minigtfs/

The **full published FRTA GTFS feed** — not a hand-encoded mini-feed. The original
task (R8) was a stretch goal to hand-encode 1-2 routes from PDF timetables; that is
now unnecessary because FRTA publishes a complete, official GTFS feed. We use it
directly.

## Source / provenance
- **Agency:** Franklin Regional Transit Authority (GTFS `agency_id` 961)
- **Publisher:** Trillium Solutions, Inc. (FRTA's official GTFS vendor)
- **Obtained via:** Mobility Database feed `mdb-429` (snapshot `202608140033`)
- **Feed version:** UTC 13-Aug-2026; `feed_id` frta-ma-us
- **Service window:** 2026-03-01 → 2027-02-28 (see `calendar.txt`)
- **Routes (7):** 20 GreenLink, 21 Greenfield, 23 Sunderland, 24 Crosstown Connector,
  31 Northampton, 32 Orange, 41 Charlemont

## Layout
Standard GTFS text files at the top level of this folder (`stops.txt`, `stop_times.txt`,
`trips.txt`, `routes.txt`, `calendar.txt`, `calendar_dates.txt`, `shapes.txt`, plus
Trillium extension files). The folder name keeps the historical `frta_minigtfs` for the
R8 task reference, but the contents are the FULL feed.

## Engine notes (steering/tech.md)
- GTFS times may exceed 24:00:00 for past-midnight trips; the engine converts to seconds
  since local midnight and MUST NOT wrap past 86400. The published feed already encodes
  these correctly — do not "fix" them.
- `calendar.txt` + `calendar_dates.txt` define active service days; resolve service for a
  date from both (RT-7 in the raptor-router spec).

## MANUAL-CHECK — resolved
- Hand-encoding is NO LONGER NEEDED (R8 stretch goal satisfied by the official feed).
- Refresh: re-download the latest `mdb-429` snapshot from the Mobility Database when the
  service window rolls over (after 2027-02-28).
