# data/manual/frta_minigtfs/

STRETCH (task 16). A hand-encoded mini-GTFS for 1-2 FRTA fixed routes, built from
FRTA's published PDF timetables. This is a SCAFFOLD only — the stop_times are NOT
encoded yet because FRTA timetables are PDFs that could not be fetched automatically
(the fetch returned "unsupported content type: application/pdf").

## GTFS files to produce (minimal viable set)
- `agency.txt`        — FRTA agency row (done below as a starter)
- `stops.txt`         — stop_id, stop_name, stop_lat, stop_lon  (HAND-ENCODE from timetable + map)
- `routes.txt`        — route_id, route_short_name, route_long_name, route_type=3
- `calendar.txt`      — service_id, weekday flags, start/end date
- `trips.txt`         — route_id, service_id, trip_id
- `stop_times.txt`    — trip_id, arrival_time, departure_time, stop_id, stop_sequence

## CRITICAL ENCODING RULE (from steering/tech.md)
GTFS times are "HH:MM:SS" and MAY EXCEED 24:00:00 for trips past midnight.
Downstream the engine converts to seconds since local midnight and MUST NOT wrap
past 86400. Encode e.g. 24:30:00, never 00:30:00, for a 12:30am arrival on a late trip.

## MISSING / MANUAL-CHECK — why this must be done by hand
1. FRTA route timetables are PDF scans at frta.org. Automated fetch is blocked
   (application/pdf unsupported), so a human must open the PDF for the chosen route(s)
   and transcribe every timepoint. WHY MANUAL: the source is an un-fetchable PDF.
2. Stop coordinates (stop_lat/stop_lon) are not in the timetable. A human must geocode
   each named stop from a map. WHY MANUAL: requires reading a map / geocoder per stop.
3. Service calendar: confirm which days each trip runs and the service period dates
   from the timetable header. WHY MANUAL: on the PDF only.
4. Pick which 1-2 routes to encode (likely the Greenfield-anchored routes serving the
   audit clinics). WHY MANUAL: a scoping decision for the demo.

Candidate source index: https://www.frta.org/  (Routes & Schedules -> individual PDFs)
