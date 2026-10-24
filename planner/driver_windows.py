"""Volunteer-driver / COA-van service windows (spec: visit-planner VP-24).

Data: data/manual/volunteer_driver_windows.csv (M3). A row with blank days/start/end is a
labelled GAP (hours not published) and is never used to place a ride: unknown is never
read as "always available". Times are seconds since local midnight of the service date.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

DAY_CODES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")  # date.weekday() order


class DriverWindowsError(ValueError):
    """The driver-window file is malformed."""


@dataclass(frozen=True)
class DriverWindow:
    town: str
    provider: str
    kind: str
    days: frozenset[str]
    start: int  # seconds since midnight
    end: int
    notice_days: int | None
    source_url: str
    date: str  # verification date (vintage)

    def covers(self, service_date: str, span: tuple[int, int]) -> bool:
        """True when the whole span [lo, hi] on service_date lies inside this window."""
        day = DAY_CODES[dt.date.fromisoformat(service_date).weekday()]
        lo, hi = span
        return day in self.days and self.start <= lo and hi <= self.end

    def as_details(self) -> dict:
        return {
            "provider": self.provider,
            "kind": self.kind,
            "days": sorted(self.days, key=DAY_CODES.index),
            "start": f"{self.start // 3600:02d}:{self.start % 3600 // 60:02d}",
            "end": f"{self.end // 3600:02d}:{self.end % 3600 // 60:02d}",
            "notice_days": self.notice_days,
            "source_url": self.source_url,
            "vintage": self.date,
        }


def _hhmm(value: str, where: str) -> int:
    try:
        h, m = value.split(":")
        hh, mm = int(h), int(m)
    except ValueError as exc:
        raise DriverWindowsError(f"{where}: bad HH:MM {value!r}") from exc
    if not (0 <= hh <= 24 and 0 <= mm < 60) or (hh == 24 and mm):
        raise DriverWindowsError(f"{where}: bad HH:MM {value!r}")
    return hh * 3600 + mm * 60


def parse_rows(rows: Iterable[dict[str, str]]) -> tuple[DriverWindow, ...]:
    out: list[DriverWindow] = []
    for i, raw in enumerate(rows, start=2):
        r = {k: (v or "").strip() for k, v in raw.items()}
        where = f"row {i}"
        if not r.get("source_url"):
            raise DriverWindowsError(f"{where}: missing source_url")
        if not (r.get("days") and r.get("start") and r.get("end")):
            continue  # labelled gap: hours unknown -> never used
        days = frozenset(d.strip().lower() for d in r["days"].split(";") if d.strip())
        if not days or not days <= set(DAY_CODES):
            raise DriverWindowsError(f"{where}: bad days {r['days']!r}")
        start, end = _hhmm(r["start"], where), _hhmm(r["end"], where)
        if start >= end:
            raise DriverWindowsError(f"{where}: start must be before end")
        notice = r.get("notice_days")
        out.append(DriverWindow(
            town=r["town"], provider=r["provider"], kind=r.get("kind", ""), days=days,
            start=start, end=end, notice_days=int(notice) if notice else None,
            source_url=r["source_url"], date=r.get("date", ""),
        ))
    return tuple(out)


def load_windows(path: Path) -> tuple[DriverWindow, ...]:
    if not path.is_file():
        raise DriverWindowsError(f"driver-window file not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return parse_rows(csv.DictReader(f))


def covering(
    windows: Iterable[DriverWindow], town: str | None, service_date: str, span: tuple[int, int]
) -> DriverWindow | None:
    """First window (in file order) for this town that covers the span, else None."""
    if not town:
        return None
    key = " ".join(town.split()).casefold()
    for w in windows:
        if " ".join(w.town.split()).casefold() == key and w.covers(service_date, span):
            return w
    return None
