"""Loader for the visit-type rulebook `planner/visit_rules.yaml` (content owner: M3).

Rules are data; code reads them and never hard-codes visit logic.

Expected YAML shape (proposed by M4; confirm with M3 before the rulebook lands):

    visit_types:
      <visit_type>:
        duration: <int minutes, incl. prep + recovery>
        escort_required: <bool>
        telehealth_ok: <bool>
        prep: <bool>
        recurrence: <str, optional>   # e.g. "3x/week"
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from planner.models import VisitRule

_REQUIRED_BOOLS = ("escort_required", "telehealth_ok", "prep")


class RulebookError(ValueError):
    """The rulebook is missing or malformed."""


def parse_rules(data: Any) -> dict[str, VisitRule]:
    if not isinstance(data, Mapping) or not isinstance(data.get("visit_types"), Mapping):
        raise RulebookError("rulebook must have a top-level 'visit_types' mapping")

    rules: dict[str, VisitRule] = {}
    for visit_type, raw in data["visit_types"].items():
        if not isinstance(raw, Mapping):
            raise RulebookError(f"{visit_type}: entry must be a mapping")

        duration = raw.get("duration")
        # bool is a subclass of int; reject it explicitly.
        if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
            raise RulebookError(f"{visit_type}: 'duration' must be a positive integer (minutes)")

        for key in _REQUIRED_BOOLS:
            if not isinstance(raw.get(key), bool):
                raise RulebookError(f"{visit_type}: '{key}' must be true or false")

        recurrence = raw.get("recurrence")
        if recurrence is not None and not isinstance(recurrence, str):
            raise RulebookError(f"{visit_type}: 'recurrence' must be a string if present")

        rules[str(visit_type)] = VisitRule(
            visit_type=str(visit_type),
            duration_min=duration,
            escort_required=raw["escort_required"],
            telehealth_ok=raw["telehealth_ok"],
            prep=raw["prep"],
            recurrence=recurrence,
        )
    return rules


def load_rules(path: Path) -> dict[str, VisitRule]:
    if not path.is_file():
        raise RulebookError(f"rulebook not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RulebookError(f"rulebook is not valid YAML: {exc}") from exc
    return parse_rules(data)
