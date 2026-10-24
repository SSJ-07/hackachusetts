---
inclusion: fileMatch
fileMatchPattern: 'engine/**'
---

# GTFS domain rules (engine only)

These apply when working under `engine/**`. GTFS has traps that cause wrong routing
answers; a wrong answer strands a patient.

## Time handling
- GTFS `stop_times` may have times **≥ 24:00:00** (e.g. `24:30:00`, `25:10:00`) to encode
  trips running past midnight on the same service day. **Parse these as seconds past local
  midnight and keep them > 86400 — never wrap to 00:30.** This is the classic midnight bug.
- All internal times are **integer seconds since local midnight of the service date**.

## Service calendar
- Use `calendar.txt` **and** `calendar_dates.txt`. `calendar_dates` adds/removes service on
  specific dates (exception_type 1 = added, 2 = removed) and overrides `calendar`.
- Resolve the active service_ids for the query date before building the timetable.

## Transfers and frequencies
- Respect `transfers.txt` minimum transfer time. Default a small min transfer if absent.
- If `frequencies.txt` is present, expand headway-based trips into concrete departures.

## Accessibility fields
- Carry `wheelchair_boarding` on stops and `wheelchair_accessible` on trips through to the
  itinerary so the UI can flag wheelchair-boarding.

## Limits (configurable; defaults)
- ≤ 2 transfers · ≤ 2h each way · walk legs ≤ 800 m · earliest home departure ≥ 05:30 ·
  10-minute (600 s) check-in buffer before appointment start.

## Testing expectations
- Every router change runs the fast Hypothesis suite + golden trips (File Save hook).
- Properties to preserve: causality, FIFO, transfer-minimum, Pareto, round-trip soundness,
  **midnight/service-day safety**. Differential: RAPTOR == CSA == brute force.
