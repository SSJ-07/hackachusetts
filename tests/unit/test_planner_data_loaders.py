import pytest

from planner.pt1 import Pt1FieldsError, parse_fields
from planner.rules import RulebookError, load_rules, parse_rules

GOOD = {"visit_types": {"t": {"duration": 60, "escort_required": True, "telehealth_ok": False, "prep": True}}}


def test_parse_rules_ok():
    rule = parse_rules(GOOD)["t"]
    assert (rule.duration_min, rule.escort_required, rule.telehealth_ok, rule.prep) == (60, True, False, True)


@pytest.mark.parametrize(
    "patch",
    [
        {"duration": 0},
        {"duration": True},
        {"duration": "60"},
        {"escort_required": "yes"},
        {"telehealth_ok": None},
        {"recurrence": 3},
    ],
)
def test_parse_rules_rejects_bad_values(patch):
    bad = {"visit_types": {"t": {**GOOD["visit_types"]["t"], **patch}}}
    with pytest.raises(RulebookError):
        parse_rules(bad)


def test_parse_rules_requires_visit_types():
    with pytest.raises(RulebookError):
        parse_rules({"types": {}})


def test_missing_rulebook_file(tmp_path):
    with pytest.raises(RulebookError, match="not found"):
        load_rules(tmp_path / "visit_rules.yaml")


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
