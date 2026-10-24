"""access-resources-mcp — stdio MCP server (spec: .kiro/specs/access-resources-mcp).

Rural transport options, MassHealth PT-1 pre-fill and the visit-type rulebook, served
from M3's hand-verified data. Thin adapter: all logic lives in planner/access.py.
Logistics only — never clinical or eligibility decisions. Synthetic patients only.
Every response carries source_url + vintage.

Run: .venv/bin/python mcp/access-resources-mcp/server.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Import the MCP SDK BEFORE the repo root is on sys.path: the repo's own mcp/
# folder would otherwise shadow the `mcp` package.
from mcp.server.mcpserver import MCPServer

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from planner import access  # noqa: E402

SERVER = "access-resources-mcp"
server = MCPServer(name=SERVER, version="1.0.0")


def _error(tool: str, exc: Exception) -> dict[str, Any]:
    return {"status": "error", "server": SERVER, "tool": tool, "error": str(exc),
            "source_url": None, "vintage": None}


@server.tool()
def rural_options(town: str) -> dict[str, Any]:
    """Rural ride options for a Franklin/Hampshire town (dial-a-ride, COA drivers, PT-1),
    with coverage tier, source_url and vintage."""
    return access.rural_options(town)


@server.tool()
def pt1_prefill(
    patient_id: str,
    visit_type: str,
    language: str = "en",
    clinic_id: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
) -> dict[str, Any]:
    """Pre-fill MassHealth PT-1 fields for a SYNTHETIC patient (fields from
    data/manual/pt1_fields.json). Fields a person must fill are returned empty."""
    try:
        return access.pt1_prefill(patient_id, visit_type, language, clinic_id, date, start_time)
    except access.NotSyntheticError as exc:
        return _error("pt1_prefill", exc)


@server.tool()
def visit_rules(visit_type: str) -> dict[str, Any]:
    """Logistics rules for a visit type from planner/visit_rules.yaml
    (duration, escort, telehealth, prep, recurrence)."""
    return access.visit_rules(visit_type)


@server.resource("access://rural-options", name="rural-options-table", mime_type="application/json")
def rural_options_table() -> str:
    """Full hand-verified rural options table, each row with source_url and date."""
    return json.dumps(access.rural_table(), ensure_ascii=False)


if __name__ == "__main__":
    server.run()
