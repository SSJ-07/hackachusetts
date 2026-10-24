#!/usr/bin/env python3
"""Hook #8 action — structural GTFS validator.

Invoked by the `validate-gtfs-on-create` IDE file hook as:
    scripts/hooks/validate_gtfs.py <path>
where <path> is a .zip GTFS feed OR a directory of GTFS .txt files (or a single
file inside such a feed — we validate the containing feed).

Structural checks only (NOT a schedule/graph check):
  1. Required files present: stops, routes, trips, stop_times, and a calendar
     (calendar.txt OR calendar_dates.txt — GTFS allows either).
  2. Required columns present in each required file.
  3. Times in stop_times (arrival_time / departure_time) parse as HH:MM:SS and
     allow hours >= 24 (GTFS "after midnight" times are never wrapped).

Exit 0 when the feed is structurally valid, 1 otherwise. Problems print to
stderr; a one-line OK summary prints to stdout on success.
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

# file stem -> required columns
REQUIRED: dict[str, list[str]] = {
    "stops": ["stop_id", "stop_lat", "stop_lon"],
    "routes": ["route_id", "route_type"],
    "trips": ["route_id", "service_id", "trip_id"],
    "stop_times": ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
}
# at least one of these (any columns-check is light: service_id present)
CALENDAR_ANY = {
    "calendar": ["service_id"],
    "calendar_dates": ["service_id", "date", "exception_type"],
}


class GtfsError(Exception):
    pass


def _parse_time(value: str) -> bool:
    """True if value is a valid GTFS time HH:MM:SS (hours may exceed 23)."""
    value = value.strip()
    if value == "":
        return True  # empty allowed (e.g. non-timepoint rows)
    parts = value.split(":")
    if len(parts) != 3:
        return False
    try:
        h, m, s = (int(p) for p in parts)
    except ValueError:
        return False
    if h < 0:
        return False
    if not (0 <= m < 60 and 0 <= s < 60):
        return False
    return True


def _read_rows(text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip().lstrip("\ufeff") for h in (reader.fieldnames or [])]
    reader.fieldnames = header
    return header, list(reader)


def _feed_files(path: Path) -> dict[str, str]:
    """Return {stem: file_text} for the GTFS feed at `path`.

    `path` may be a .zip, a directory, or a single .txt/.zip inside a feed
    (we resolve to the containing feed).
    """
    if path.is_file() and path.suffix.lower() == ".zip":
        out: dict[str, str] = {}
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                p = Path(name)
                if p.suffix.lower() == ".txt":
                    out[p.stem] = zf.read(name).decode("utf-8-sig", errors="replace")
        return out
    if path.is_file() and path.suffix.lower() == ".txt":
        path = path.parent  # validate the containing feed directory
    if path.is_dir():
        out = {}
        for p in path.glob("*.txt"):
            out[p.stem] = p.read_text(encoding="utf-8-sig", errors="replace")
        return out
    raise GtfsError(f"{path}: not a .zip or directory GTFS feed")


def validate(path: Path) -> list[str]:
    """Return a list of problem strings (empty == valid)."""
    problems: list[str] = []
    try:
        files = _feed_files(path)
    except (GtfsError, zipfile.BadZipFile, OSError) as exc:
        return [str(exc)]

    if not files:
        return [f"{path}: no GTFS .txt files found"]

    # 1 + 2: required files and their columns.
    for stem, cols in REQUIRED.items():
        if stem not in files:
            problems.append(f"missing required file: {stem}.txt")
            continue
        header, _rows = _read_rows(files[stem])
        for c in cols:
            if c not in header:
                problems.append(f"{stem}.txt: missing required column '{c}'")

    # calendar OR calendar_dates
    present_cal = [c for c in CALENDAR_ANY if c in files]
    if not present_cal:
        problems.append("missing service calendar: neither calendar.txt nor calendar_dates.txt present")
    else:
        for cal in present_cal:
            header, _ = _read_rows(files[cal])
            for c in CALENDAR_ANY[cal]:
                if c not in header:
                    problems.append(f"{cal}.txt: missing required column '{c}'")

    # 3: time parsing in stop_times
    if "stop_times" in files:
        header, rows = _read_rows(files["stop_times"])
        if {"arrival_time", "departure_time"} <= set(header):
            bad = 0
            for i, row in enumerate(rows, start=2):  # +1 header, +1 to 1-base
                for col in ("arrival_time", "departure_time"):
                    if not _parse_time(row.get(col, "") or ""):
                        bad += 1
                        if bad <= 5:
                            problems.append(
                                f"stop_times.txt line {i}: bad {col} "
                                f"{row.get(col)!r} (expected HH:MM:SS, hours may exceed 23)"
                            )
            if bad > 5:
                problems.append(f"stop_times.txt: {bad} rows with unparseable times (showing first 5)")

    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: validate_gtfs.py <feed.zip | feed_dir | file-in-feed>", file=sys.stderr)
        return 1
    target = Path(args[0]).expanduser()
    if not target.exists():
        print(f"validate_gtfs: path does not exist: {target}", file=sys.stderr)
        return 1

    problems = validate(target)
    if problems:
        print(f"GTFS structural check FAILED for {target}:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"GTFS structural check OK: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
