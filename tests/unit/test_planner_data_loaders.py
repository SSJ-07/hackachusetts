from pathlib import Path

import pytest

from planner.pt1 import Pt1FieldsError, parse_fields
from planner.rules import RulebookError, load_rules, parse_rules

REPO = Path(__file__).resolve().parents[2]
ENTRY = {
    "label": {"en": "Test", "es": None},
    "duration": 60,
    "escort_required": True,
    "telehealth_ok": False,
    "prep": True,
    "recurrence": {"per_week": 3},
    "source": {"name": "test", "url": None, "vintage": None, "status": "verified"},
}


def book(**patch):
    return {"schema_version": 1, "visit_types": {"t": {**ENTRY, **patch}}}


def test_parse_rules_ok():
    rule = parse_rules(book())["t"]
    assert (rule.duration_min, rule.escort_required, rule.telehealth_ok, rule.prep) == (60, True, False, True)
    assert rule.recurrence_per_week == 3
    assert rule.source_status == "verified"
    assert rule.is_complete


def test_null_means_unknown_not_false():
    rule = parse_rules(book(duration=None, escort_required=None, recurrence=None))["t"]
    assert rule.duration_min is None and rule.escort_required is None
    assert not rule.is_complete


@pytest.mark.parametrize(
    "patch",
    [
        {"duration": 0},
        {"duration": True},
        {"duration": "60"},
        {"escort_required": "yes"},
        {"telehealth_ok": 0},
        {"recurrence": 3},
        {"recurrence": {"per_week": 0}},
        {"source": {"status": "done"}},
    ],
)
def test_parse_rules_rejects_bad_values(patch):
    with pytest.raises(RulebookError):
        parse_rules(book(**patch))


def test_parse_rules_requires_schema_version():
    with pytest.raises(RulebookError, match="schema_version"):
        parse_rules({"visit_types": {}})


def test_parse_rules_requires_visit_types():
    with pytest.raises(RulebookError):
        parse_rules({"schema_version": 1, "types": {}})


def test_missing_rulebook_file(tmp_path):
    with pytest.raises(RulebookError, match="not found"):
        load_rules(tmp_path / "visit_rules.yaml")


def test_real_rulebook_parses():
    """M3's planner/visit_rules.yaml (currently a placeholder) loads with this schema."""
    rules = load_rules(REPO / "planner" / "visit_rules.yaml")
    assert "colonoscopy" in rules


def test_mock_rulebook_matches_schema():
    rules = load_rules(REPO / "api" / "mocks" / "planner" / "visit_rules.yaml")
    assert rules["colonoscopy"].is_complete


def test_parse_pt1_fields():
    fields = parse_fields({"fields": [{"id": "a", "source": "patient.id"}, {"id": "b", "source": None}]})
    assert [(f.id, f.source) for f in fields] == [("a", "patient.id"), ("b", None)]


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"fields": [{"source": "patient.id"}]},
        {"fields": [{"id": "a", "source": "patient.ssn"}]},
        {"fields": [{"id": "a"}, {"id": "a"}]},
    ],
)
def test_parse_pt1_fields_rejects_bad(data):
    with pytest.raises(Pt1FieldsError):
        parse_fields(data)
