# Design — access-resources-mcp

```
MCP client ──stdio──> mcp/access-resources-mcp/server.py   (thin: 3 tools + 1 resource)
                              │
                              ▼
                       planner/access.py                     (pure functions, unit-tested)
                        │        │         │
   rural_options.csv ───┘        │         └── planner/rules.py ── visit_rules.yaml
   rural_coverage.csv            └── planner/pt1.py ── pt1_fields.json
                              │
                              ▼
                 planner/guardrails.assert_logistics_only  (on every response)
```

## Decisions
- **Logic in `planner/`, not `mcp/`.** The repo's `mcp/` folder shadows the `mcp` SDK
  package when the repo root is on `sys.path`, so tests import `planner.access`
  directly. `server.py` imports the SDK first, then appends the repo root.
- **Provenance is exempt from the word guardrail.** A citation URL like
  `cancer.org/...` is not patient wording. Only `source_url`, `source_name` and
  `sources` are exempt; everything else is checked.
- **`vintage`** = the row's verification `date` (rural), the PT-1 `source.vintage`,
  or the rule's `source.vintage`.
- **Synthetic-ID check** is a floor, not proof: `^[a-z][a-z0-9_-]{0,39}$` after
  lower-casing must hold and the id must not be all digits.
- **PT-1 field-file fix.** `pt1_fields.json` used `key`; `planner/pt1.py` reads
  `id` + `source`. Each field now carries both. The eligibility box was given the
  neutral id `masshealth_determination` (source null) so no eligibility wording is emitted.
