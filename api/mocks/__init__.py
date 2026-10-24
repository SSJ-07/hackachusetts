"""MOCK DATA for the H1 scaffold. Illustrative only: nothing here is computed or sourced.

Every file in this folder carries a `_mock_notice` key (stripped before responses are
built) and every mock source is named "MOCK ...". The server reports
`X-Data-Mode: mock` on every response while mocks are active.

Replace with real data as owners land it:
  audit.json / whatif   -> M2 (reachability cube)
  provenance.json       -> M4 + M1 (docs/traceability.md, docs/provenance.jsonl)
  planner/*             -> M3 (visit_rules.yaml, pt1_fields.json, clinic_schedules.csv)
                           and M1 (engine.round_trip)
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

MOCKS_DIR = Path(__file__).resolve().parent
PLANNER_MOCKS_DIR = MOCKS_DIR / "planner"


def _strip_private(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_private(v) for k, v in value.items() if not k.startswith("_")}
    if isinstance(value, list):
        return [_strip_private(v) for v in value]
    return value


@cache
def _load(relative: str) -> Any:
    return json.loads((MOCKS_DIR / relative).read_text(encoding="utf-8"))


def load(relative: str) -> Any:
    """Load a mock JSON file with `_`-prefixed keys removed. Returns a fresh copy."""
    return _strip_private(_load(relative))
