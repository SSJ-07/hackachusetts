"""Access resources: rural ride options, PT-1 pre-fill, visit rules (spec: access-resources-mcp).

Pure functions behind mcp/access-resources-mcp/server.py. They read M3's hand-verified
data and return plain dicts. Every response carries top-level ``source_url`` and
``vintage`` (AR-5) and passes the logistics-only guardrail.

Logistics only: no clinical advice, no eligibility decisions. Synthetic patients only.
"""

from __future__ import annotations

import csv
import difflib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from planner.guardrails import assert_logistics_only
from planner.pt1 import load_fields
from planner.rules import load_rules

ROOT = Path(__file__).resolve().parents[1]
RURAL_OPTIONS = ROOT / "data" / "manual" / "rural_options.csv"
RURAL_COVERAGE = ROOT / "data" / "manual" / "rural_coverage.csv"
PT1_FIELDS = ROOT / "data" / "manual" / "pt1_fields.json"
VISIT_RULES = ROOT / "planner" / "visit_rules.yaml"

# Citations, not wording: exempt from the word guardrail (see design.md).
PROVENANCE_KEYS = frozenset({"source_url", "source_name", "sources"})
_SYNTHETIC_ID = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


class NotSyntheticError(ValueError):
    """The patient id does not look like a synthetic id."""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _strip_provenance(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _strip_provenance(v) for k, v in value.items() if k not in PROVENANCE_KEYS}
    if isinstance(value, (list, tuple)):
        return [_strip_provenance(v) for v in value]
    return value


def _checked(resp: dict[str, Any]) -> dict[str, Any]:
    """Enforce AR-5: provenance present, wording logistics-only."""
    if "source_url" not in resp or "vintage" not in resp:
        raise ValueError("response missing source_url/vintage")  # programming error
    assert_logistics_only(_strip_provenance(resp))
    return resp


def _norm(town: str) -> str:
    return " ".join(town.split()).casefold()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def _rural_rows() -> dict[str, dict[str, Any]]:
    """Town (normalised) -> joined row from rural_options + rural_coverage."""
    coverage = {_norm(r["town"]): r for r in _read_csv(RURAL_COVERAGE)}
    rows: dict[str, dict[str, Any]] = {}
    for r in _read_csv(RURAL_OPTIONS):
        c = coverage.get(_norm(r["town"]), {})
        has_any = c.get("has_any_option", "").upper()
        rows[_norm(r["town"])] = {
            "town": r["town"],
            "county": r.get("county", ""),
            "options": {
                "dial_a_ride": r.get("dial_a_ride") or None,
                "coa_driver": r.get("coa_driver") or None,
                "pt1": r.get("pt1") or None,
                "hours": r.get("hours") or None,
            },
            "coverage": {
                "tier": c.get("coverage_tier") or None,
                "has_any_option": {"TRUE": True, "FALSE": False}.get(has_any),
            },
            "verified_by": r.get("verified_by", ""),
            "source_url": r.get("source_url", ""),
            "date": r.get("date", ""),
        }
    return rows


# --------------------------------------------------------------------------- #
# AR-1 rural_options
# --------------------------------------------------------------------------- #
def rural_options(town: str) -> dict[str, Any]:
    rows = _rural_rows()
    row = rows.get(_norm(town or ""))
    if row is None:
        names = [r["town"] for r in rows.values()]
        close = difflib.get_close_matches((town or "").strip().title(), names, n=3, cutoff=0.6)
        return _checked({
            "found": False, "town": town, "options": None, "suggestions": close,
            "source_url": str(RURAL_OPTIONS.relative_to(ROOT)).replace("\\", "/"),
            "vintage": max((r["date"] for r in rows.values()), default=""),
        })
    resp = {"found": True, **row, "vintage": row["date"]}
    resp.pop("date")
    return _checked(resp)


# --------------------------------------------------------------------------- #
# AR-4 resource
# --------------------------------------------------------------------------- #
def rural_table() -> dict[str, Any]:
    rows = sorted(_rural_rows().values(), key=lambda r: (r["county"], r["town"]))
    return _checked({
        "rows": rows,
        "count": len(rows),
        "source_url": str(RURAL_OPTIONS.relative_to(ROOT)).replace("\\", "/"),
        "sources": sorted({r["source_url"] for r in rows if r["source_url"]}),
        "vintage": max((r["date"] for r in rows), default=""),
    })


# --------------------------------------------------------------------------- #
# AR-3 visit_rules
# --------------------------------------------------------------------------- #
def _raw_rules() -> dict[str, Any]:
    return yaml.safe_load(VISIT_RULES.read_text(encoding="utf-8"))["visit_types"]


def visit_rules(visit_type: str) -> dict[str, Any]:
    rules = load_rules(VISIT_RULES)  # validates the schema (planner/rules.py)
    rule = rules.get((visit_type or "").strip().lower())
    if rule is None:
        return _checked({
            "found": False, "visit_type": visit_type, "known": sorted(rules),
            "source_url": "planner/visit_rules.yaml", "vintage": None,
        })
    raw = _raw_rules()[rule.visit_type]
    src = raw.get("source") or {}
    label = raw.get("label") or {}
    return _checked({
        "found": True,
        "visit_type": rule.visit_type,
        "label": {"en": label.get("en"), "es": label.get("es")},
        "duration_min": rule.duration_min,
        "escort_required": rule.escort_required,
        "telehealth_ok": rule.telehealth_ok,
        "prep": rule.prep,
        "recurrence_per_week": rule.recurrence_per_week,
        "source_status": rule.source_status,
        "source_name": src.get("name"),
        "source_url": src.get("url"),
        "vintage": src.get("vintage"),
    })


# --------------------------------------------------------------------------- #
# AR-2 pt1_prefill
# --------------------------------------------------------------------------- #
def _assert_synthetic(patient_id: str) -> str:
    pid = (patient_id or "").strip().lower()
    if not _SYNTHETIC_ID.match(pid):
        raise NotSyntheticError(
            "patient_id must be a synthetic slug (e.g. 'maria', 'syn-001'); real member IDs are not accepted"
        )
    return pid


def pt1_prefill(
    patient_id: str,
    visit_type: str,
    language: str = "en",
    clinic_id: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
) -> dict[str, Any]:
    pid = _assert_synthetic(patient_id)
    meta = json.loads(PT1_FIELDS.read_text(encoding="utf-8"))
    src = meta.get("source") or {}
    basis = src.get("basis") or []
    prov = {
        "source_url": basis[0] if basis else None,
        "sources": basis,
        "vintage": src.get("vintage"),
    }
    rules = load_rules(VISIT_RULES)
    rule = rules.get((visit_type or "").strip().lower())
    if rule is None:
        return _checked({"found": False, "visit_type": visit_type, "known": sorted(rules), **prov})

    values: dict[str, Any] = {
        "patient.id": pid,
        "patient.language": language,
        "visit.type": rule.visit_type,
        "visit.clinic_id": clinic_id,
        "visit.date": date,
        "visit.start_time": start_time,
        "visit.escort_required": rule.escort_required,
    }
    fields = load_fields(PT1_FIELDS)  # validates the shape (planner/pt1.py)
    prefill = {f.id: (values[f.source] if f.source else None) for f in fields}
    return _checked({
        "found": True,
        "patient_id": pid,
        "visit_type": rule.visit_type,
        "form_id": meta.get("form_id"),
        "fields": prefill,
        "human_fields": [f.id for f in fields if f.source is None],
        "missing_inputs": [f.id for f in fields if f.source and values[f.source] is None],
        "note": "Synthetic patient. Fields left empty are filled by the provider or MassHealth.",
        **prov,
    })
