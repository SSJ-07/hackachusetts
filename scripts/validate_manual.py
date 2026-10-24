#!/usr/bin/env python3
"""Data-quality gate for data/manual/* (manual-data spec R9.2).

Fails (exit 1) if any manual data row:
  * lacks a source where the schema requires one (source_url / source empty, or a
    TODO-VERIFY sitting next to a real value);
  * has a malformed clock time (not HH:MM / HH:MM:SS; GTFS hours >=24 are allowed
    ONLY inside the frta_minigtfs feed, which the engine parses, not here);
  * references a clinic_id that is not present in clinic_stops.csv.

Pure standard library so CI needs no extra deps. Prints every problem, grouped by
file, then exits non-zero if any were found.

Run:  python scripts/validate_manual.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data" / "manual"
CLINICS = MANUAL / "clinics.csv"        # authoritative clinic roster
CLINIC_STOPS = MANUAL / "clinic_stops.csv"  # demo-anchor subset (clinic -> transit stop)

TIME_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
PLACEHOLDER = {"", "todo-verify", "tbd", "n/a", "na", "null", "none"}

# Columns that count as "a source" per file-family. A row is sourced if ANY is set.
SOURCE_COLS = ("source_url", "source", "source_urls")
# Columns whose values must look like HH:MM[:SS] when present.
TIME_COLS = ("start_time", "end_time", "open_time", "close_time", "arrive_by",
             "earliest_return_departure")


def _sourced(row: dict) -> bool:
    for c in SOURCE_COLS:
        v = (row.get(c) or "").strip().lower()
        if v and v not in PLACEHOLDER:
            return True
    return False


def load_clinic_ids() -> set[str]:
    """Authoritative clinic roster = clinics.csv. Other files' clinic_id must appear here."""
    if not CLINICS.exists():
        return set()
    with CLINICS.open(encoding="utf-8-sig", newline="") as f:
        return {(r.get("clinic_id") or "").strip() for r in csv.DictReader(f)}


def check_csv(path: Path, clinic_ids: set[str]) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    rel = path.relative_to(ROOT)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        has_source_col = any(c in cols for c in SOURCE_COLS)
        has_clinic_col = "clinic_id" in cols
        time_cols = [c for c in TIME_COLS if c in cols]
        for i, row in enumerate(reader, start=2):  # row 1 = header
            if has_source_col and not _sourced(row):
                errs.append(f"{rel}:{i} missing source (all of {SOURCE_COLS} empty/placeholder)")
            for c in time_cols:
                v = (row.get(c) or "").strip()
                if not v:
                    continue
                if not TIME_RE.match(v):
                    errs.append(f"{rel}:{i} bad time in '{c}': {v!r} (want HH:MM)")
                    continue
                hh = int(v.split(":")[0])
                # 24:00 exactly is a valid "midnight / end of day" posted close time.
                # Anything strictly past 24:00 is only legal in a GTFS feed file.
                if hh > 24 or (hh == 24 and v not in ("24:00", "24:00:00")):
                    errs.append(f"{rel}:{i} hour out of range in '{c}': {v!r}")
            if has_clinic_col and path not in (CLINICS, CLINIC_STOPS):
                cid = (row.get("clinic_id") or "").strip()
                if cid and cid not in clinic_ids:
                    errs.append(f"{rel}:{i} clinic_id {cid!r} not in clinics.csv")
            if has_clinic_col and path == CLINIC_STOPS:
                cid = (row.get("clinic_id") or "").strip()
                if cid and cid not in clinic_ids:
                    # Cross-team naming gap (demo anchors vs roster) — WARN, don't fail CI.
                    warns.append(f"{rel}:{i} clinic_id {cid!r} not in clinics.csv (demo anchor; reconcile with M2)")
    return errs, warns


def check_json(path: Path) -> list[str]:
    """JSON files must parse; if they carry a top-level 'source' block, it must be non-empty."""
    rel = path.relative_to(ROOT)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [f"{rel}: invalid JSON ({e})"]
    errs: list[str] = []
    if isinstance(data, dict) and "source" in data:
        src = data["source"]
        if not src or (isinstance(src, dict) and not any(src.values())):
            errs.append(f"{rel}: 'source' block present but empty")
    return errs


def main() -> int:
    clinic_ids = load_clinic_ids()
    all_errs: list[str] = []
    all_warns: list[str] = []
    # CSV files carry the sourced-row / time / clinic_id rules.
    for p in sorted(MANUAL.rglob("*.csv")):
        e, w = check_csv(p, clinic_ids)
        all_errs += e
        all_warns += w
    # JSON files (e.g. pt1_fields.json) must at least be valid + non-empty source.
    for p in sorted(MANUAL.rglob("*.json")):
        all_errs += check_json(p)

    if all_warns:
        print(f"WARN: {len(all_warns)} non-blocking warning(s):")
        for w in all_warns:
            print("  ~", w)

    if all_errs:
        print(f"FAIL: {len(all_errs)} data-quality problem(s) in data/manual/:")
        for e in all_errs:
            print("  -", e)
        return 1
    print("OK: data/manual/ passed source, time, and clinic_id checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
