"""PT-1 (MassHealth Provider Request for Transportation) pre-fill.

The field list is data from data/manual/pt1_fields.json (owner: M3). Each field names
the planner value that fills it, or null when a person must fill it (e.g. provider
attestation). Code never invents field names.

Proposed file shape (confirm with M3):

    {"fields": [{"id": "<field id>", "label": "<form label>", "source": "<source key>|null"}]}
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from planner.models import CandidateSlot, Patient, VisitRule

SOURCE_KEYS: frozenset[str] = frozenset(
    {
        "patient.id",
        "patient.language",
        "visit.type",
        "visit.clinic_id",
        "visit.date",
        "visit.start_time",
        "visit.escort_required",
    }
)


class Pt1FieldsError(ValueError):
    """The PT-1 field list is missing or malformed."""


@dataclass(frozen=True)
class Pt1Field:
    id: str
    source: str | None


def parse_fields(data: Any) -> tuple[Pt1Field, ...]:
    if not isinstance(data, Mapping) or not isinstance(data.get("fields"), list):
        raise Pt1FieldsError("PT-1 fields file must have a top-level 'fields' list")
    fields: list[Pt1Field] = []
    seen: set[str] = set()
    for raw in data["fields"]:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str) or not raw["id"]:
            raise Pt1FieldsError("each PT-1 field needs a non-empty string 'id'")
        if raw["id"] in seen:
            raise Pt1FieldsError(f"duplicate PT-1 field id: {raw['id']!r}")
        source = raw.get("source")
        if source is not None and source not in SOURCE_KEYS:
            raise Pt1FieldsError(f"{raw['id']}: unknown source {source!r}")
        seen.add(raw["id"])
        fields.append(Pt1Field(id=raw["id"], source=source))
    return tuple(fields)


def load_fields(path: Path) -> tuple[Pt1Field, ...]:
    if not path.is_file():
        raise Pt1FieldsError(f"PT-1 fields file not found: {path}")
    try:
        return parse_fields(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise Pt1FieldsError(f"PT-1 fields file is not valid JSON: {exc}") from exc


def _hhmm(seconds: int) -> str:
    # Appointment starts are same-day; keep >24h values visible rather than wrapping.
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}"


def prefill(
    fields: tuple[Pt1Field, ...],
    patient: Patient,
    rule: VisitRule,
    slot: CandidateSlot,
    language: str,
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "patient.id": patient.id,
        "patient.language": language,
        "visit.type": rule.visit_type,
        "visit.clinic_id": slot.clinic_id,
        "visit.date": slot.date,
        "visit.start_time": _hhmm(slot.start),
        "visit.escort_required": rule.escort_required,
    }
    return {f.id: (values[f.source] if f.source else None) for f in fields}
