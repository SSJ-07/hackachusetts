# rural_coverage.csv — the "no option at all" / coverage-tier layer

Derived from `rural_options.csv` by `pipeline/build_rural_coverage.py` (re-run after any
edit to the rural table). One row per Franklin/Hampshire town.

## Columns
- `coverage_tier` — best available option: `fixed_route` > `demand_response` >
  `assisted_only` (COA/PT-1 only) > `none`
- `has_any_option` — FALSE only when a town has NO transit, NO dial-a-ride, NO COA
  driver, and NO PT-1. TRUE otherwise.
- remaining columns carry provenance through from `rural_options.csv`.

## What this layer DOES say
Whether a town has ANY transport option at all. This is the one thing the engine's
reachability cube CANNOT express: the cube measures whether a reachable bus trip exists
to a given clinic, but a town with zero transit service produces no cube rows at all, so
"no service" would otherwise be invisible. This file makes that explicit for the rural lens.

## What this layer does NOT say
- It is NOT reachability. "Has demand-response" does not mean a patient can reach a
  specific clinic and get home — that is the cube's job (join on `town`/block group).
- The `fixed_route` vs `demand_response` split is only as good as `rural_options.csv`.
  Authoritative fixed-route coverage (which PVTA/FRTA route serves which town) comes from
  the **PVTA/FRTA GTFS feeds**, not hand classification. Current data classifies the
  Hampshire towns by their Senior Dial-A-Ride entry; towns with scheduled fixed-route bus
  (e.g. Amherst, Northampton) will upgrade to `fixed_route` once cross-referenced against
  the GTFS stops — a follow-up for M2's pipeline.

## Current result
All 47 towns = `demand_response` (every town has at least FRTA or PVTA demand-response).
No true transit-desert town in the current table. The meaningful UI signal is therefore
"thin coverage" (demand-response-only, no fixed route), which resolves once GTFS
fixed-route coverage is joined in.
