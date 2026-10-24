# mcp/

Three custom MCP servers (stdio).

| Server | Tools | Resources / prompts / elicitation |
|---|---|---|
| `gtfs-mcp` | `plan_trip`, `round_trip`, `service_changes`, `validate_feed` | resources: feed metadata, stop list · prompt: `explain_trip` |
| `reach-mcp` | `reachability`, `what_if`, `suggest_schedule` | resources: cached cubes · elicitation: visit duration if missing |
| `access-resources-mcp` | `rural_options`, `pt1_prefill`, `visit_rules` | resources: rural options table with sources |

Registered in `.kiro/settings/mcp.json` (alongside GitHub, Playwright and AWS Docs).
All three are **placeholders**: tools return `{"status": "not_implemented", ...}` with the
contract shape. Setup (run from repo root):

```bash
python3 -m venv .venv && .venv/bin/pip install -r mcp/requirements.txt
``` Owner: M1 (gtfs-mcp), M2 (reach-mcp), M4 (access-resources-mcp).
