"""Unit tests for engine.optimizer on tiny hand-built cubes.

No cache needed — every cube/origins here is constructed in-memory, so these run
in CI. Covers: a known best move, never-worse when no move helps, open-hours
clamp, non-overlap, output shape, and the AuditDataError path.
"""

from __future__ import annotations

import pandas as pd
import pytest

from engine.audit import AuditDataError
from engine import optimizer as opt


# --------------------------------------------------------------------------- #
# tiny fixtures
# --------------------------------------------------------------------------- #
def make_cube(reach_by_hour: dict[int, dict[str, bool]], clinic="C", day="mon",
              visit_type="colonoscopy") -> pd.DataFrame:
    """reach_by_hour: {hour: {bg_geoid: reachable}}."""
    rows = []
    for hour, bgs in reach_by_hour.items():
        for bg, reach in bgs.items():
            rows.append({"clinic_id": clinic, "visit_type": visit_type, "day": day,
                         "hour": int(hour), "bg_geoid": bg, "reachable": bool(reach),
                         "reason": ""})
    df = pd.DataFrame(rows)
    df["bg_geoid"] = df["bg_geoid"].astype(str)
    df["hour"] = df["hour"].astype(int)
    df["reachable"] = df["reachable"].astype(bool)
    return df


def make_origins(spec: dict[str, tuple[int, bool]]) -> pd.DataFrame:
    """spec: {bg_geoid: (carless_adults, ej_flag)}."""
    rows = [{"bg_geoid": str(bg), "lat": 42.0, "lon": -72.0, "carless_adults": ca,
             "pop": ca * 2, "ej_flag": bool(ej), "lep_pct": 0.1, "age65_pct": 0.1}
            for bg, (ca, ej) in spec.items()]
    df = pd.DataFrame(rows)
    df["bg_geoid"] = df["bg_geoid"].astype(str)
    return df


# a weight dict that is 1.0 everywhere, so expected scores are easy to reason about
UNIT_WEIGHTS = {"default": 1.0, "weights": {}, "source": "test", "vintage": "test"}


# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #
def test_known_best_move_shifts_to_higher_reach_hour():
    # hour 7: nobody reachable; hour 9: 100 reachable EJ adults. Baseline block at 7.
    cube = make_cube({7: {"b": False}, 8: {"b": False}, 9: {"b": True}})
    origins = make_origins({"b": (100, True)})
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=1,
                             weights=UNIT_WEIGHTS, baseline_blocks=[7])
    assert len(r["changes"]) == 1
    ch = r["changes"][0]["change"]
    assert ch == {"kind": "shift", "day": "mon", "block": "mon-07", "to": 9}
    assert r["changes"][0]["gain_visit_hours"] == pytest.approx(100.0)
    assert r["changes"][0]["gain_people"] == 100
    assert r["suggested_score"] == pytest.approx(100.0)
    assert r["baseline_score"] == pytest.approx(0.0)


def test_never_worse_when_no_move_helps():
    # baseline block sits on the single best hour; every shift target is worse.
    cube = make_cube({7: {"b": False}, 8: {"b": True}, 9: {"b": False}})
    origins = make_origins({"b": (50, True)})
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=3,
                             weights=UNIT_WEIGHTS, baseline_blocks=[8])
    assert r["changes"] == []
    assert r["suggested_score"] == pytest.approx(r["baseline_score"])
    assert r["suggested_blocks"] == [8]


def test_non_ej_adults_excluded_from_score():
    # bg "x" is reachable but NOT EJ -> contributes nothing. bg "y" is EJ.
    cube = make_cube({7: {"x": True, "y": False}, 9: {"x": True, "y": True}})
    origins = make_origins({"x": (1000, False), "y": (10, True)})
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=1,
                             weights=UNIT_WEIGHTS, baseline_blocks=[7])
    # hour 7 EJ-reachable = 0, hour 9 EJ-reachable = 10 -> shift 7->9 gains 10
    assert r["baseline_score"] == pytest.approx(0.0)
    assert r["changes"][0]["change"]["to"] == 9
    assert r["changes"][0]["gain_people"] == 10


def test_weight_applied_per_visit_type():
    cube = make_cube({7: {"b": False}, 9: {"b": True}}, visit_type="dialysis")
    origins = make_origins({"b": (10, True)})
    weights = {"default": 1.0, "weights": {"dialysis": 2.0}, "source": "t", "vintage": "t"}
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=1,
                             weights=weights, baseline_blocks=[7])
    # visit_hours weighted by 2.0; people unweighted
    assert r["changes"][0]["gain_visit_hours"] == pytest.approx(20.0)
    assert r["changes"][0]["gain_people"] == 10


def test_open_hours_clamp_blocks_out_of_range_targets(monkeypatch):
    # force open hours to {7,8} only -> a block at 8 cannot shift to 9 even though
    # hour 9 has higher reach.
    cube = make_cube({7: {"b": True}, 8: {"b": True}, 9: {"b": True}})
    origins = make_origins({"b": (10, True)})
    monkeypatch.setattr(opt, "open_hours", lambda clinic, day, cube_hours: ([7, 8], "test-clamp"))
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=3,
                             weights=UNIT_WEIGHTS, baseline_blocks=[8])
    assert r["open_hours_source"] == "test-clamp"
    # only legal target is 7 (same reach) -> no positive move
    assert r["changes"] == []


def test_non_overlap_target_already_occupied():
    # two blocks at 7 and 9; the only better hour (9) is already occupied by a block.
    cube = make_cube({7: {"b": False}, 8: {"b": False}, 9: {"b": True}})
    origins = make_origins({"b": (10, True)})
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=3,
                             weights=UNIT_WEIGHTS, baseline_blocks=[7, 9])
    # 9 is occupied; 7 can move to 8 (reach 0, no gain) -> no positive move
    assert r["changes"] == []
    assert set(r["suggested_blocks"]) == {7, 9}


def test_output_shape_has_all_required_fields():
    cube = make_cube({7: {"b": False}, 9: {"b": True}})
    origins = make_origins({"b": (10, True)})
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=1,
                             weights=UNIT_WEIGHTS, baseline_blocks=[7])
    for key in ("clinic", "day", "k", "baseline_score", "suggested_score",
                "open_hours", "open_hours_source", "changes", "sources"):
        assert key in r
    ch = r["changes"][0]
    for key in ("change", "gain_visit_hours", "gain_people", "sources"):
        assert key in ch
    assert isinstance(ch["sources"], list) and ch["sources"]


def test_missing_clinic_day_raises_audit_error():
    cube = make_cube({7: {"b": True}})
    origins = make_origins({"b": (10, True)})
    with pytest.raises(AuditDataError):
        opt.suggest_schedule(cube, origins, "NOPE", "mon", k=1, weights=UNIT_WEIGHTS)


def test_k_zero_returns_baseline():
    cube = make_cube({7: {"b": False}, 9: {"b": True}})
    origins = make_origins({"b": (10, True)})
    r = opt.suggest_schedule(cube, origins, "C", "mon", k=0,
                             weights=UNIT_WEIGHTS, baseline_blocks=[7])
    assert r["changes"] == []
    assert r["suggested_blocks"] == [7]
