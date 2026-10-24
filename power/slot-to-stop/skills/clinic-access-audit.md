# Skill: clinic-access-audit

Audit which hours of a clinic's weekly schedule car-less adults in each neighborhood
can actually reach **and return from** by transit.

## When to use
The user asks "who can reach this clinic by bus", "audit our schedule for access",
"which appointment hours strand car-less patients", or wants a CHNA-ready access report.

## Tools
- `gtfs-mcp` → `round_trip(origin, clinic, date, start, minutes)` — the authoritative
  round-trip reachability check (arrive by start − 10 min AND return after the visit ends).
- `reach-mcp` → `reachability(clinic, visit_type, day, hour)` and `what_if(...)` — the
  precomputed cube and schedule shifts.

## Procedure
1. Identify the clinic (`clinic_id` or lat/lon) and the weekly schedule blocks.
2. For each (day, hour, visit_type) block and each block-group origin, call the cube via
   `reach-mcp reachability`, which calls the engine's `round_trip`. Never re-derive
   reachability by hand.
3. Report the reachable share of **car-less adults** per hour, plus the equity breakdown
   (EJ, limited-English, 65+, zero-vehicle). Every number carries its source and vintage.
4. To test a fix, call `what_if` with a block shift (±1–3h) or a satellite day and compare
   the reachable share — report the realised gain, not a hard-coded number.

## Guardrails
Logistics only — never a clinical or eligibility statement. Reachability is not attendance.
Template numbers are labelled "illustrative". Synthetic patients only.
