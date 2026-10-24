# Design — Manual Data Collection (M3)

Branch: `M3-Bryan`. Owner: M3.

## Overview

M3 produces the hand-collected data layer. These artifacts are consumed by the engine
(`engine/`), the planner (`planner/`), and the API (`api/`), but M3 depends on NONE of
them — it is a pure data producer sitting behind the fixed shapes in
`docs/contracts.md`. Everything here is a flat, diffable, cited file so each row's
provenance survives review.

## Design principles

1. **Diffable over binary.** CSV / YAML / JSON only. No spreadsheets, no Parquet (that
   is M2's cache layer). A reviewer must see every changed cell in a PR diff.
2. **Provenance is a column, not a footnote.** Each row/field carries its own
   `source_url` / `source` / `verified_by`. A value without provenance is invalid.
3. **Placeholders, never guesses.** Unknown real-world values are `TODO-VERIFY` /
   `null` / `verified:false`, never plausible inventions.
4. **Human gates are explicit.** Every file ends with MISSING / MANUAL-CHECK naming the
   human step and why automation cannot close it.
5. **Guardrails enforced in the data shape.** ES text carries a DRAFT flag; templates
   carry `reviewed:false`; demo slots carry a FICTIONAL label.

## Artifact map

| Requirement | File | Format | Consumed by | Contract tie |
|---|---|---|---|---|
| R1 | `data/manual/clinic_schedules.csv` | CSV | engine, /audit | `clinic_id` = cube/audit key |
| R2 | `data/manual/rural_options.csv` | CSV | planner | ride-option lookup |
| R3 | `data/manual/pt1_fields.json` | JSON | /plan | `pt1_prefill` keys |
| R4 | `data/manual/barrier_questions.yaml` | YAML | /plan | `barriers` keys |
| R5 | `planner/visit_rules.yaml` | YAML | planner engine | `visit_type` values |
| R6 | `planner/templates/{en,es}/*.md` + `signoff.json` | MD + JSON | /plan itinerary | template tokens |
| R7 | `docs/sources.md` | MD | /provenance drawer | `(verify)` claims |
| R8 | `data/manual/frta_minigtfs/` | GTFS txt | engine | GTFS time rule |

## Schemas (authoritative column/key order)

### clinic_schedules.csv
`slot_id, clinic_id, clinic_name, address, town, visit_type, appointment_date,
start_time, end_time, visit_minutes, arrive_by, earliest_return_departure, timezone,
office_hours, source_url, is_template, status, notes`

### rural_options.csv
`town, county, dial_a_ride, coa_driver, pt1, hours, source_url, verified_by, date`
- `county` added to the base contract to disambiguate Franklin vs Hampshire towns.

### pt1_fields.json
`{ form_id, form_name, source{authority,basis[],vintage,verified}, fields[{key,label,
type,required,verified,note}], MISSING_MANUAL_CHECK[] }`

### barrier_questions.yaml
`meta{instruments,es_status}` + `questions[{id,maps_to,source,verbatim,en,es}]`

### visit_rules.yaml
`visit_types{<type>{duration,escort_required,telehealth_ok,prep,recurrence}}`
- `duration` in minutes, feeds `round_trip(minutes=...)`.

### signoff.json
`{reading_level_target, templates[{path,lang,reviewer,reviewed,date,
reading_level_target, translation_status?}]}`

## Key design decisions

- **`county` column in rural_options.** The contract listed `town` only; two counties
  share town-like names and the audit scopes by county, so county is first-class.
- **Mode past-midnight in GTFS.** `stop_times` uses `24:30:00` not `00:30:00`; the
  engine converts to seconds-since-midnight and must not wrap (tech.md). This is the one
  place a naive encoder corrupts routing silently.
- **ES is data-flagged, not code-gated.** Draft ES ships in the repo (so reviewers can
  work on it) but every ES artifact carries a DRAFT/`reviewed:false` marker; the planner
  must refuse to emit any ES patient text whose `signoff.json.reviewed` is false.
- **403 / PDF sources are recorded, not faked.** mass.gov (PT-1) and FRTA/CHNA PDFs
  block automated fetch. The design records the pointer + a manual step rather than
  transcribing unverified values.

## Failure modes guarded

| Risk | Guard |
|---|---|
| Invented stat presented as fact | provenance column required; `unsourced` status |
| ES machine-translation reaching a patient | `reviewed:false` + planner refusal |
| Wrapped GTFS midnight time | R8.2 encoding rule + engine property test |
| Demo slot mistaken for real | `is_template` + FICTIONAL label (R1.2) |
| Stale rural data | `verified_by` + `date` required when filled (R2.3) |

## Out of scope

Parquet caches (`data/cache/*`, M2), the routing engine (M1), the API (M2/M4), and the
web UI. M3 stops at the cited flat files.
