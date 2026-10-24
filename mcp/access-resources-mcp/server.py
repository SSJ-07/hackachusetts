"""access-resources-mcp — PLACEHOLDER stdio MCP server. Owner: M4.

Rural transport options, MassHealth PT-1 pre-fill, and the visit-type rulebook
(planner/visit_rules.yaml). Logistics only — never clinical or eligibility decisions.
Synthetic patients only.

Run: .venv/bin/python mcp/access-resources-mcp/server.py
"""

from typing import Any

from mcp.server.mcpserver import MCPServer

SERVER = "access-resources-mcp"
server = MCPServer(name=SERVER, version="0.0.0-placeholder")


def _stub(tool: str, **echo: Any) -> dict[str, Any]:
    """Uniform placeholder payload. Carries no numbers, so nothing needs a source yet."""
    return {"status": "not_implemented", "server": SERVER, "tool": tool, "request": echo, "sources": []}


@server.tool()
def rural_options(town: str) -> dict[str, Any]:
    """Transport options for a town (volunteer drivers, COA vans, demand-response), with sources."""
    stub = _stub("rural_options", town=town)
    stub.update(options=[])
    return stub


@server.tool()
def pt1_prefill(patient_id: str, visit_type: str) -> dict[str, Any]:
    """Pre-fill MassHealth PT-1 fields for a SYNTHETIC patient (fields: data/manual/pt1_fields.json)."""
    stub = _stub("pt1_prefill", patient_id=patient_id, visit_type=visit_type)
    stub.update(pt1_prefill={})
    return stub


@server.tool()
def visit_rules(visit_type: str) -> dict[str, Any]:
    """Logistics rules for a visit type from planner/visit_rules.yaml."""
    return _stub("visit_rules", visit_type=visit_type)


@server.resource("access://rural-options", name="rural-options-table", mime_type="application/json")
def rural_options_table() -> str:
    """Hand-verified rural options table with sources (placeholder)."""
    return '{"status": "not_implemented", "rows": [], "sources": []}'


if __name__ == "__main__":
    server.run()
