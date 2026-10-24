"""reach-mcp — PLACEHOLDER stdio MCP server. Owner: M2.

Wraps the reachability cube and the schedule optimizer. Tool shapes follow
docs/contracts.md §3 (/audit, /whatif). Elicitation (ask for visit duration when
missing) lands with the real implementation.

Run: .venv/bin/python mcp/reach-mcp/server.py
"""

from typing import Any

from mcp.server.mcpserver import MCPServer

SERVER = "reach-mcp"
server = MCPServer(name=SERVER, version="0.0.0-placeholder")


def _stub(tool: str, **echo: Any) -> dict[str, Any]:
    """Uniform placeholder payload. Carries no numbers, so nothing needs a source yet."""
    return {"status": "not_implemented", "server": SERVER, "tool": tool, "request": echo, "sources": []}


@server.tool()
def reachability(clinic: str, community: str, day: str) -> dict[str, Any]:
    """Reachability for one clinic x community x day. Same shape as GET /audit when implemented."""
    stub = _stub("reachability", clinic=clinic, community=community, day=day)
    stub.update(cells=[], equity={})
    return stub


@server.tool()
def what_if(clinic: str, block: str, to: int) -> dict[str, Any]:
    """Recompute after moving a clinic block (e.g. block='mon-08', to=10). Same shape as /audit."""
    stub = _stub("what_if", clinic=clinic, block=block, to=to)
    stub.update(cells=[], equity={})
    return stub


@server.tool()
def suggest_schedule(clinic: str, k: int = 3) -> dict[str, Any]:
    """Up to k ranked schedule changes maximizing EJ reachable visit-hours (see optimizer-notes)."""
    stub = _stub("suggest_schedule", clinic=clinic, k=k)
    stub.update(changes=[])
    return stub


@server.resource("reach://cubes", name="cached-cubes", mime_type="application/json")
def cached_cubes() -> str:
    """Index of cached reachability cubes (placeholder)."""
    return '{"status": "not_implemented", "cubes": []}'


if __name__ == "__main__":
    server.run()
