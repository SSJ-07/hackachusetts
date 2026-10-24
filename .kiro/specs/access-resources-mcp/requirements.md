# Requirements — access-resources-mcp

Make `mcp/access-resources-mcp/server.py` real. It serves M3's hand-verified data
(rural options, PT-1 fields, visit rulebook) to agents and the Visit Planner.
Logistics only. Synthetic patients only. Every response carries provenance.

## AR-1 rural_options(town)
- WHEN called with a town in `data/manual/rural_options.csv`, THE SERVER SHALL return
  that town's `dial_a_ride`, `coa_driver`, `pt1`, `hours`, joined with
  `coverage_tier` and `has_any_option` from `data/manual/rural_coverage.csv`.
- Town matching SHALL ignore case and surrounding whitespace.
- WHEN the town is unknown, THE SERVER SHALL return `found: false`, no options, and up
  to 3 close town-name suggestions. It SHALL NOT guess options.

## AR-2 pt1_prefill(patient_id, visit_type, ...)
- THE SERVER SHALL map a SYNTHETIC patient + visit to the fields in
  `data/manual/pt1_fields.json`, using each field's `source` key (`planner/pt1.py`).
- Fields with `source: null` SHALL be returned as `null` and listed in
  `human_fields` (a person fills them). The MassHealth determination field is always
  null: MassHealth decides, never this tool.
- THE SERVER SHALL reject a `patient_id` that does not look synthetic (must be a short
  slug containing a letter, e.g. `maria`, `syn-001`), so a real member ID cannot pass.
- WHEN `visit_type` is unknown, THE SERVER SHALL return `found: false`.

## AR-3 visit_rules(visit_type)
- THE SERVER SHALL return the parsed rule from `planner/visit_rules.yaml` via
  `planner/rules.py` (duration, escort_required, telehealth_ok, prep, recurrence,
  EN/ES label). `null` stays `null`, never `0`/`false`.
- WHEN `visit_type` is unknown, THE SERVER SHALL return `found: false` and the known types.

## AR-4 resource `access://rural-options`
- THE SERVER SHALL expose the full joined rural table as JSON, each row with
  `source_url` and `date`, plus a top-level `vintage`.

## AR-5 provenance + guardrails (all tools)
- Every response SHALL include top-level `source_url` and `vintage`.
- Every response SHALL pass `planner.guardrails.assert_logistics_only`, except
  provenance fields (`source_url`, `source_name`, `sources`), which are citations, not wording.
- The server SHALL be a thin adapter: logic lives in `planner/access.py` and is
  testable without the MCP SDK.
