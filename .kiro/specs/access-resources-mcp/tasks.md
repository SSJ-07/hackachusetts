# Tasks — access-resources-mcp

- [x] 1. Fix `data/manual/pt1_fields.json` to the `planner/pt1.py` shape (`id`, `source`). (AR-2)
- [x] 2. `planner/access.py`: `rural_options`, `pt1_prefill`, `visit_rules`, `rural_table`. (AR-1..4)
- [x] 3. Provenance (`source_url`, `vintage`) + guardrail on every response. (AR-5)
- [x] 4. `server.py`: thin MCP adapter, 3 tools + `access://rural-options` resource. (AR-5)
- [x] 5. `tests/unit/test_access_resources.py`: known/unknown town, case-insensitive match,
      PT-1 mapping + human fields + synthetic-ID rejection, rule nulls, resource shape,
      provenance on every response, guardrail over every response.
- [x] 6. MCP smoke test: server lists 3 tools + 1 resource and answers a tool call.
