"""access-resources-mcp (owner: M4). PLACEHOLDER: no MCP functionality yet.

Planned tools (mcp/README.md, FINAL plan §8.6): rural_options(town),
pt1_prefill(patient, visit), visit_rules(type). Planned resource: the rural options
table with sources. The server will be a thin stdio adapter over planner/ and M3's
data/manual files; the MCP SDK dependency is added when work starts.

Note: do not add mcp/__init__.py. A top-level `mcp` package would shadow the MCP SDK.
"""

SERVER_NAME = "access-resources-mcp"
PLANNED_TOOLS = ("rural_options", "pt1_prefill", "visit_rules")
IMPLEMENTED = False
