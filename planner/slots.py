"""Candidate-slot source backed by data/manual/clinic_schedules.csv (content owner: M3).

The CSV lists appointment slots per facility *service* ("GI consultation", "OB/GYN",
"Primary care", ...), not per clinical visit type. The rulebook (planner/visit_rules.yaml)
is keyed by clinical visit type ("colonoscopy", "prenatal", ...). This module maps a
rulebook visit type to the facility service label(s) that offer it, then reads the
matching rows as CandidateSlot.

Every slot in the file is a DEMO/illustrative assumption (`is_template=TRUE`,
`status="Demo assumption"`): it is NOT a bookable slot. Callers must surface that
labelling (docs/contracts.md, AGENTS.md: template numbers are labelled "illustrative",
never stated as findings). `illustrative` is carried on every row this loader returns.

Times in the CSV are local "HH:MM" clock times on `appointment_date`. The planner works
in integer seconds since local midnight, so "08:00" -> 28800. A visit crossing midnight
is not represented in this file (all slots start within office hours), so no >86400 wrap
is produced here.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from planner.models import CandidateSlot, VisitRule

__all__ = ["ClinicScheduleError", "VISIT_TYPE_TO_SERVICE", "load_slots", "slots_for_rule"]


class ClinicScheduleError(ValueError):
    """The clinic schedule file is missing or malformed."""


# Rulebook visit type -> the facility service label(s) in clinic_schedules.csv that
# offer it. A rulebook type with no offering service (dialysis, chemo) maps to nothing
# and honestly yields zero slots in real mode rather than a guessed match.
VISIT_TYPE_TO_SERVICE: dict[str, frozenset[str]] = {
    "colonoscopy": frozenset({"GI consultation"}),
    "prenatal": frozenset({"OB/GYN"}),
    # dialysis, chemo: no infusion/dialysis service label in the demo schedule.
}

_REQUIRED_COLUMNS = frozenset(
    {"clinic_id", "visit_type", "appointment_date", "start_time"}
)


@dataclass(frozen=True)
class ScheduledSlot:
    """One CSV row as a CandidateSlot plus the provenance a caller must surface."""

    slot: CandidateSlot
    service_label: str
    illustrative: bool
    source_url: str


def _hhmm_to_seconds(value: str, where: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ClinicScheduleError(f"{where}: start_time must be HH:MM, got {value!r}")
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ClinicScheduleError(f"{where}: start_time out of range, got {value!r}")
    return hours * 3600 + minutes * 60


def load_slots(path: Path) -> list[ScheduledSlot]:
    """Read every row of the clinic schedule CSV into ScheduledSlot."""
    if not path.is_file():
        raise ClinicScheduleError(f"clinic schedule not found: {path}")
    out: list[ScheduledSlot] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = _REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ClinicScheduleError(f"clinic schedule missing columns: {sorted(missing)}")
        for i, row in enumerate(reader, start=2):  # row 1 is the header
            start = _hhmm_to_seconds(row["start_time"], f"row {i}")
            out.append(
                ScheduledSlot(
                    slot=CandidateSlot(
                        clinic_id=row["clinic_id"].strip(),
                        date=row["appointment_date"].strip(),
                        start=start,
                    ),
                    service_label=row["visit_type"].strip(),
                    illustrative=str(row.get("is_template", "")).strip().upper() == "TRUE",
                    source_url=str(row.get("source_url", "")).strip(),
                )
            )
    return out


def slots_for_rule(scheduled: list[ScheduledSlot], rule: VisitRule) -> list[CandidateSlot]:
    """The candidate slots whose facility service offers this rulebook visit type.

    Returns [] for a visit type with no offering service (e.g. dialysis), so real mode
    reports "no candidate slots" honestly instead of matching the wrong service.
    """
    services = VISIT_TYPE_TO_SERVICE.get(rule.visit_type, frozenset())
    if not services:
        return []
    return [s.slot for s in scheduled if s.service_label in services]
