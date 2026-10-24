"""reach-mcp — stdio MCP server wrapping the reachability cube + schedule optimizer.

Owner: M2. Exposes the ONE aggregation path (engine.audit) and the schedule
optimizer (engine.optimizer) so agents read reachability from the cached cube
instead of recomputing it. Tool shapes follow docs/contracts.md §3 (/audit,
/whatif) and the schedule-optimizer spec (SO-15).

Same MCPServer style and import pattern as mcp/gtfs-mcp/server.py (repo-root
sys.path shim). Every response carries `sources` (guardrail: every number has a
source). If the cube cache is missing, tools return a clear error payload rather
than crashing.

Run: .venv/bin/python mcp/reach-mcp/server.py
"""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from typing import Any

# Make the repo root importable so `import engine` works when run as a script.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from mcp.server.mcpserver import MCPServer  # noqa: E402

from engine import audit as audit_mod  # noqa: E402
from engine import optimizer as opt_mod  # noqa: E402
from engine.audit import AuditDataError  # noqa: E402

SERVER = "reach-mcp"
server = MCPServer(name=SERVER, version="0.1.0")


# --------------------------------------------------------------------------
# Cached cube + origins (loaded once per process).
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _data():
    """Return (cube, origins) or raise. Cached so repeated calls are cheap."""
    cube = audit_mod.load_cube()
    origins = audit_mod.load_origins()
    return cube, origins


def _error(tool: str, msg: str, **echo: Any) -> dict[str, Any]:
    """Uniform error payload — never a crash (contracts: clear error, not an exception)."""
    return {"server": SERVER, "tool": tool, "error": msg, "request": echo, "sources": []}


def _safe_data(tool: str, **echo: Any):
    """Load data or return (None, error_payload)."""
    try:
        return _data(), None
    except FileNotFoundError:
        return None, _error(tool, "reachability cube cache not found "
                                  "(data/cache/cube.parquet); build it with pipeline/build_cube.py",
                            **echo)
    except Exception as e:  # pragma: no cover - defensive
        return None, _error(tool, f"failed to load cube/origins: {e}", **echo)


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------
@server.tool()
def reachability(clinic: str, community: str, day: str) -> dict[str, Any]:
    """Reachability for one clinic x community x day. Same shape as GET /audit
    (contracts.md §3): {cells, equity, sources}."""
    data, err = _safe_data("reachability", clinic=clinic, community=community, day=day)
    if err:
        return err
    cube, origins = data
    try:
        payload = audit_mod.audit(cube, origins, clinic, community, day)
    except AuditDataError as e:
        return _error("reachability", str(e), clinic=clinic, community=community, day=day)
    payload["server"] = SERVER
    return payload


@server.tool()
def what_if(clinic: str, block: str, to: int, community: str = "all") -> dict[str, Any]:
    """Recompute after moving a clinic block (e.g. block='mon-08', to=10). Same
    shape as /audit (contracts.md §3)."""
    data, err = _safe_data("what_if", clinic=clinic, block=block, to=to, community=community)
    if err:
        return err
    cube, origins = data
    try:
        payload = audit_mod.whatif(cube, origins, clinic, block, int(to), community)
    except AuditDataError as e:
        return _error("what_if", str(e), clinic=clinic, block=block, to=to, community=community)
    payload["server"] = SERVER
    return payload


@server.tool()
def suggest_schedule(clinic: str, k: int = 3, day: str = "mon") -> dict[str, Any]:
    """Up to k ranked schedule changes maximizing reachable EJ car-less visit-hours
    (schedule-optimizer spec SO-1..SO-16). Each change carries
    {change, gain_visit_hours, gain_people, sources}."""
    data, err = _safe_data("suggest_schedule", clinic=clinic, k=k, day=day)
    if err:
        return err
    cube, origins = data
    try:
        payload = opt_mod.suggest_schedule(cube, origins, clinic, day, k=int(k))
    except AuditDataError as e:
        return _error("suggest_schedule", str(e), clinic=clinic, k=k, day=day)
    payload["server"] = SERVER
    return payload


# --------------------------------------------------------------------------
# Resources
# --------------------------------------------------------------------------
@server.resource("reach://cubes", name="cached-cubes", mime_type="application/json")
def cached_cubes() -> str:
    """Index of what the cached reachability cube contains: clinics, days, hours,
    visit types, and block-group count."""
    try:
        cube, origins = _data()
    except FileNotFoundError:
        return json.dumps({"status": "no_cache", "cubes": [],
                           "note": "data/cache/cube.parquet not found"})
    except Exception as e:  # pragma: no cover
        return json.dumps({"status": "error", "error": str(e), "cubes": []})
    clinics = sorted(cube.clinic_id.unique().tolist())
    cubes = []
    for c in clinics:
        sub = cube[cube.clinic_id == c]
        cubes.append({
            "clinic_id": c,
            "days": sorted(sub.day.unique().tolist()),
            "hours": sorted(int(h) for h in sub.hour.unique()),
            "visit_types": sorted(sub.visit_type.unique().tolist()),
            "block_groups": int(sub.bg_geoid.nunique()),
        })
    return json.dumps({
        "status": "ok",
        "cubes": cubes,
        "origins_block_groups": int(origins.bg_geoid.nunique()),
        "sources": audit_mod.sources(),
    })


if __name__ == "__main__":
    server.run()
