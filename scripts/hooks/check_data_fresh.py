#!/usr/bin/env python3
"""Hook #9 action — data freshness check (warn only).

Invoked by the `data-freshness-pre-task` IDE hook before a task runs. It warns
when the cached source data is getting stale, so an agent does not silently plan
on a feed that has expired. It is advisory: it ALWAYS exits 0 and only prints
warnings to stderr — it never blocks a task.

Warn conditions:
  1. data/raw/manifest.json is missing.
  2. manifest.json is older than 7 days (by its mtime, or its newest per-source
     `downloaded` timestamp if present — whichever is newer).
  3. The PVTA GTFS feed_end_date is within 14 days (or already passed). The end
     date is read from manifest `pvta_gtfs.validation.service_window[1]`
     (YYYYMMDD) when present.

Env override: DATA_ROOT points at the repo root to check (default: cwd).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path

STALE_DAYS = 7
FEED_END_WARN_DAYS = 14


def _root() -> Path:
    return Path(os.environ.get("DATA_ROOT", ".")).expanduser()


def _parse_iso(ts: str) -> _dt.datetime | None:
    try:
        return _dt.datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _parse_yyyymmdd(s: str) -> _dt.date | None:
    try:
        return _dt.datetime.strptime(str(s).strip(), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


def check(root: Path, now: _dt.datetime | None = None) -> list[str]:
    """Return a list of warning strings (empty == all fresh)."""
    now = now or _dt.datetime.now()
    today = now.date()
    warnings: list[str] = []

    manifest = root / "data" / "raw" / "manifest.json"
    if not manifest.exists():
        warnings.append(f"data manifest missing: {manifest} — run scripts/get_data.py")
        return warnings

    data: dict = {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"could not read {manifest}: {exc}")
        data = {}

    # Freshness: newer of file mtime and newest per-source `downloaded`.
    newest = _dt.datetime.fromtimestamp(manifest.stat().st_mtime)
    if isinstance(data, dict):
        for src in data.values():
            if isinstance(src, dict):
                dl = _parse_iso(src.get("downloaded", ""))
                if dl and dl > newest:
                    newest = dl
    age_days = (now - newest).days
    if age_days > STALE_DAYS:
        warnings.append(
            f"data is {age_days} days old (> {STALE_DAYS}); newest download "
            f"{newest.date().isoformat()} — consider re-running scripts/get_data.py"
        )

    # PVTA feed_end_date within 14 days.
    end: _dt.date | None = None
    try:
        window = data.get("pvta_gtfs", {}).get("validation", {}).get("service_window")
        if isinstance(window, (list, tuple)) and len(window) >= 2:
            end = _parse_yyyymmdd(window[1])
    except AttributeError:
        end = None
    if end is not None:
        days_left = (end - today).days
        if days_left < 0:
            warnings.append(
                f"PVTA GTFS feed EXPIRED {-days_left} days ago (feed_end_date "
                f"{end.isoformat()}) — routing on an expired feed"
            )
        elif days_left <= FEED_END_WARN_DAYS:
            warnings.append(
                f"PVTA GTFS feed_end_date {end.isoformat()} is in {days_left} days "
                f"(<= {FEED_END_WARN_DAYS}) — refresh the feed soon"
            )

    return warnings


def main(argv: list[str] | None = None) -> int:
    warnings = check(_root())
    if warnings:
        print("data-freshness: WARNINGS (advisory, not blocking):", file=sys.stderr)
        for w in warnings:
            print(f"  ! {w}", file=sys.stderr)
    else:
        print("data-freshness: cached data looks fresh")
    return 0  # always succeed — warn only


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
