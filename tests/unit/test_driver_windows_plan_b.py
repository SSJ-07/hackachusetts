"""Unit tests for planner/driver_windows.py and planner/plan_b.py (VP-23, VP-24)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner.driver_windows import DriverWindowsError, covering, load_windows, parse_rows
from planner.guardrails import find_banned
from planner.plan_b import PlanBTemplateError, load_plan_b, parse_sections, render

ROOT = Path(__file__).resolve().parents[2]
REAL_WINDOWS = ROOT / "data/manual/volunteer_driver_windows.csv"


def _row(**kw):
    base = {"town": "Hadley", "provider": "p", "kind": "coa_van", "days": "mon", "start": "09:00",
            "end": "12:00", "notice_days": "", "source_url": "https://x.org", "date": "2026-10-24"}
    return {**base, **kw}


# ------------------------------------------------------------- driver windows
def test_real_file_loads_and_skips_gaps():
    ws = load_windows(REAL_WINDOWS)
    assert ws and all(w.source_url and w.date for w in ws)
    assert all(w.kind != "volunteer_driver" or w.days for w in ws)
    # the Hadley volunteer-driver row has no published hours -> not usable
    assert not any(w.provider.endswith("volunteer drivers") for w in ws)


def test_gap_row_is_skipped_not_guessed():
    assert parse_rows([_row(days="", start="", end="")]) == ()


@pytest.mark.parametrize("bad", [
    {"source_url": ""}, {"days": "funday"}, {"start": "9am"}, {"start": "13:00", "end": "12:00"},
    {"end": "24:30"},
])
def test_bad_rows_raise(bad):
    with pytest.raises(DriverWindowsError):
        parse_rows([_row(**bad)])


def test_covering_matches_town_day_and_bounds():
    (w,) = parse_rows([_row()])
    mon = "2026-11-09"
    assert covering([w], " hadley ", mon, (9 * 3600, 12 * 3600)) is w
    assert covering([w], "Hadley", mon, (8 * 3600, 10 * 3600)) is None  # starts too early
    assert covering([w], "Hadley", "2026-11-10", (9 * 3600, 10 * 3600)) is None  # tuesday
    assert covering([w], "Amherst", mon, (9 * 3600, 10 * 3600)) is None
    assert covering([w], None, mon, (9 * 3600, 10 * 3600)) is None


# ------------------------------------------------------------- plan B
@pytest.mark.parametrize("lang", ["en", "es"])
def test_real_templates_parse_and_are_clean(lang):
    text = (ROOT / f"planner/templates/{lang}/plan_b.md").read_text(encoding="utf-8")
    sections = parse_sections(text)
    for body in sections.values():
        assert not find_banned(body)
    assert "{{later_bus_time}}" in sections["later_bus"]


def test_unsigned_template_is_not_used():
    # repo signoff ships plan_b reviewed=false until a human signs
    signoff = json.loads((ROOT / "planner/templates/signoff.json").read_text(encoding="utf-8"))
    entry = next(t for t in signoff["templates"] if t["path"] == "planner/templates/en/plan_b.md")
    if not entry["reviewed"]:
        assert load_plan_b("en") is None


def _signoff(tmp_path, reviewed, reviewer="Reviewer"):
    p = tmp_path / "signoff.json"
    p.write_text(json.dumps({"templates": [
        {"path": "planner/templates/en/plan_b.md", "reviewed": reviewed, "reviewer": reviewer}]}))
    return p


def test_signed_template_loads(tmp_path):
    s = load_plan_b("en", signoff_path=_signoff(tmp_path, True))
    assert s and set(s) >= {"later_bus", "last_bus"}


@pytest.mark.parametrize("reviewed,reviewer", [(False, "R"), (True, ""), (True, None)])
def test_not_signed_means_none(tmp_path, reviewed, reviewer):
    assert load_plan_b("en", signoff_path=_signoff(tmp_path, reviewed, reviewer)) is None


def test_no_language_fallback(tmp_path):
    # EN is signed, ES is not: ES must NOT fall back to EN text
    assert load_plan_b("es", signoff_path=_signoff(tmp_path, True)) is None
    assert load_plan_b("fr", signoff_path=_signoff(tmp_path, True)) is None


def test_render_fills_tokens_and_rejects_missing():
    s = {"later_bus": "Bus at {{later_bus_time}}.", "last_bus": "Last bus."}
    assert render(s, "later_bus", {"later_bus_time": "17:05"}) == "Bus at 17:05."
    with pytest.raises(PlanBTemplateError):
        render(s, "later_bus", {})
    with pytest.raises(PlanBTemplateError):
        render(s, "nope", {})


def test_missing_section_raises():
    with pytest.raises(PlanBTemplateError):
        parse_sections("## later_bus\nx\n")
