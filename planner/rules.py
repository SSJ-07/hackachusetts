"""Loader for the visit-type rulebook `planner/visit_rules.yaml` (content owner: M3).

Rules are data; code reads them and never hard-codes visit logic. The schema is the
one documented in the header of planner/visit_rules.yaml (schema_version 1):

    visit_types:
      <visit_type>:
        label:           {en: str, es: str | null}
        duration:        int | null           # minutes incl. prep + recovery
        escort_required: bool | null
        telehealth_ok:   bool | null
        prep:            bool | null
        recurrence:      {per_week: int} | null
        source:          {name, url, vintage, status: todo | verified}

`null` means unknown and is kept as None. It is never read as 0 or false.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from planner.models import VisitRule

SUPPORTED_SCHEMA_VERSIONS = frozenset({1})
_OPTIONAL_BOOLS = ("escort_required", "telehealth_ok", "prep")


class RulebookError(ValueError):
    """The rulebook is missing or malformed."""


def _positive_int_or_none(value: Any, where: str) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int; reject it explicitly.
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RulebookError(f"{where} must be a positive integer or null")
    return value


def parse_rules(data: Any) -> dict[str, VisitRule]:
    if not isinstance(data, Mapping) or not isinstance(data.get("visit_types"), Mapping):
        raise RulebookError("rulebook must have a top-level 'visit_types' mapping")
    version = data.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise RulebookError(f"unsupported schema_version {version!r}")

    rules: dict[str, VisitRule] = {}
    for visit_type, raw in data["visit_types"].items():
        name = str(visit_type)
        if not isinstance(raw, Mapping):
            raise RulebookError(f"{name}: entry must be a mapping")

        duration = _positive_int_or_none(raw.get("duration"), f"{name}.duration")
        flags: dict[str, bool | None] = {}
        for key in _OPTIONAL_BOOLS:
            value = raw.get(key)
            if value is not None and not isinstance(value, bool):
                raise RulebookError(f"{name}.{key} must be true, false or null")
            flags[key] = value

        recurrence = raw.get("recurrence")
        if recurrence is not None and not isinstance(recurrence, Mapping):
            raise RulebookError(f"{name}.recurrence must be {{per_week: int}} or null")
        per_week = _positive_int_or_none(
            recurrence.get("per_week") if recurrence else None, f"{name}.recurrence.per_week"
        )

        source = raw.get("source") or {}
        if not isinstance(source, Mapping):
            raise RulebookError(f"{name}.source must be a mapping")
        status = source.get("status", "todo")
        if status not in ("todo", "verified"):
            raise RulebookError(f"{name}.source.status must be 'todo' or 'verified'")

        rules[name] = VisitRule(
            visit_type=name,
            duration_min=duration,
            escort_required=flags["escort_required"],
            telehealth_ok=flags["telehealth_ok"],
            prep=flags["prep"],
            recurrence_per_week=per_week,
            source_status=status,
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
