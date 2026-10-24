"""Unit tests for planner/access.py (spec: .kiro/specs/access-resources-mcp, AR-1..AR-5)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from planner import access
from planner.guardrails import find_banned, iter_strings
from planner.pt1 import load_fields

ROOT = Path(__file__).resolve().parents[2]


def _towns() -> list[str]:
    with (ROOT / "data/manual/rural_options.csv").open(encoding="utf-8-sig", newline="") as f:
        return [r["town"] for r in csv.DictReader(f)]


def _assert_provenance(resp: dict) -> None:
    assert "source_url" in resp and "vintage" in resp


def _assert_clean(resp: dict) -> None:
    for text in iter_strings(access._strip_provenance(resp)):
        assert not find_banned(text), text


# ---------------------------------------------------------------- AR-1
def test_rural_options_known_town_joins_coverage():
    r = access.rural_options("Greenfield")
    assert r["found"] is True and r["town"] == "Greenfield"
    assert r["county"] == "Franklin"
    assert r["options"]["dial_a_ride"]
    assert r["coverage"]["tier"] in {"fixed_route", "demand_response", "assisted_only", "none"}
    assert isinstance(r["coverage"]["has_any_option"], bool)
    assert r["source_url"].startswith("http")
    assert r["vintage"]


def test_rural_options_ignores_case_and_whitespace():
    assert access.rural_options("  gREENfield  ")["town"] == "Greenfield"


def test_rural_options_unknown_town_does_not_guess():
    r = access.rural_options("Greenfeld")
    assert r["found"] is False and r["options"] is None
    assert "Greenfield" in r["suggestions"]
    _assert_provenance(r)


@pytest.mark.parametrize("town", _towns())
def test_every_town_has_provenance_and_is_clean(town):
    r = access.rural_options(town)
    assert r["found"] is True
    _assert_provenance(r)
    assert r["source_url"], town
    _assert_clean(r)


# ---------------------------------------------------------------- AR-2
def test_pt1_prefill_maps_sources_and_lists_human_fields():
    r = access.pt1_prefill("maria", "colonoscopy", "es", "BAY_GI_SPRINGFIELD", "2026-11-12")
    assert r["found"] is True
    fields = load_fields(ROOT / "data/manual/pt1_fields.json")
    assert set(r["fields"]) == {f.id for f in fields}
    assert r["fields"]["member_id"] == "maria"
    assert r["fields"]["treatment_address"] == "BAY_GI_SPRINGFIELD"
    assert r["fields"]["effective_dates"] == "2026-11-12"
    for fid in r["human_fields"]:
        assert r["fields"][fid] is None
    assert r["fields"]["masshealth_determination"] is None
    assert "masshealth_determination" in r["human_fields"]
    assert r["missing_inputs"] == []
    _assert_provenance(r)
    _assert_clean(r)


def test_pt1_prefill_reports_missing_inputs():
    r = access.pt1_prefill("maria", "colonoscopy")
    assert set(r["missing_inputs"]) == {"treatment_address", "effective_dates"}


@pytest.mark.parametrize("pid", ["100012345678", "", "  ", "Robert'); DROP", "a" * 41, "123abc"])
def test_pt1_prefill_rejects_non_synthetic_ids(pid):
    with pytest.raises(access.NotSyntheticError):
        access.pt1_prefill(pid, "colonoscopy")


def test_pt1_prefill_unknown_visit_type():
    r = access.pt1_prefill("maria", "brain_surgery")
    assert r["found"] is False and "colonoscopy" in r["known"]
    _assert_provenance(r)


# ---------------------------------------------------------------- AR-3
def test_visit_rules_colonoscopy_matches_rulebook():
    r = access.visit_rules("Colonoscopy")
    assert r["found"] is True and r["visit_type"] == "colonoscopy"
    assert r["escort_required"] is True and r["telehealth_ok"] is False
    assert isinstance(r["duration_min"], int) and r["duration_min"] > 0
    assert r["label"]["en"] and r["label"]["es"]
    _assert_provenance(r)


@pytest.mark.parametrize("vt", ["colonoscopy", "prenatal", "dialysis", "chemo"])
def test_every_visit_type_is_clean_and_sourced(vt):
    r = access.visit_rules(vt)
    assert r["found"] is True and r["source_url"] and r["vintage"]
    _assert_clean(r)


def test_dialysis_recurrence():
    assert access.visit_rules("dialysis")["recurrence_per_week"] == 3


def test_visit_rules_unknown():
    r = access.visit_rules("nope")
    assert r["found"] is False and set(r["known"]) >= {"colonoscopy", "dialysis"}
    _assert_provenance(r)


# ---------------------------------------------------------------- AR-4
def test_rural_table_resource_shape():
    t = access.rural_table()
    assert t["count"] == len(_towns()) == len(t["rows"])
    assert all(row["source_url"] and row["date"] for row in t["rows"])
    assert t["vintage"] and t["sources"]
    json.dumps(t)  # serialisable for the MCP resource
    _assert_clean(t)


# ---------------------------------------------------------------- AR-5
def test_guardrail_still_applies_outside_provenance(monkeypatch):
    real = access._rural_rows

    def poisoned():
        rows = real()
        rows["greenfield"]["options"]["hours"] = "only if you are eligible"
        return rows

    monkeypatch.setattr(access, "_rural_rows", poisoned)
    with pytest.raises(Exception, match="non-logistics"):
        access.rural_options("Greenfield")
