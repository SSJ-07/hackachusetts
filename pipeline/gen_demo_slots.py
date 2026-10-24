#!/usr/bin/env python3
"""Generate FICTIONAL demo appointment slots from real posted clinic hours.

Reads data/manual/clinics.csv (real posted office hours, one row per clinic-day,
possibly split for lunch), expands into 30-minute demo appointment slots for every
date 2026-10-10 .. 2026-11-10 that matches the clinic's open weekday, and writes
data/manual/clinic_schedules.csv in the existing demo schema.

GUARDRAILS (AGENTS.md):
- Every slot is FICTIONAL / not bookable; labelled in `is_template` + `notes`.
- Hours come from the real clinics.csv (source_url carried through). Slots do NOT.
- Times are local "HH:MM"; visit + check-in are demo assumptions, stated as such.

Density: EVERY matching date gets slots. 2026-10-25 (Saturday) is emphasised by
adding a denser 20-minute cadence on that date on top of the normal 30-minute grid.
"""
from __future__ import annotations
import csv
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "manual" / "clinics.csv"
OUT = ROOT / "data" / "manual" / "clinic_schedules.csv"

START = date(2026, 10, 10)
END = date(2026, 11, 10)          # inclusive
FOCUS = date(2026, 10, 25)        # Saturday — extra density
CHECKIN_MIN = 15                  # demo assumption
TZ = "America/New_York"

WEEKDAY = {  # python weekday() -> clinics.csv day name
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}

# Visit length per visit_type (minutes) — demo assumptions.
VISIT_MIN = {
    "GI consultation": 30,
    "OB/GYN": 30,
    "Urgent care": 20,
    "Retail clinic": 20,
    "Acute care": 20,
    "Adult primary care": 30,
    "Pediatrics": 30,
    "Primary care": 30,
}
DEFAULT_VISIT = 30


def hhmm(t: int) -> str:
    return f"{t // 60:02d}:{t % 60:02d}"


def to_min(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def main() -> int:
    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    # group open intervals by (clinic_id, weekday-name)
    out_rows = []
    for d in daterange(START, END):
        dayname = WEEKDAY[d.weekday()]
        focus = d == FOCUS
        for r in rows:
            if r["day"].strip() != dayname:
                continue
            open_min = to_min(r["open_time"])
            close_min = to_min(r["close_time"])
            visit = VISIT_MIN.get(r["visit_type"].strip(), DEFAULT_VISIT)
            span = close_min - open_min
            if span < visit:
                continue
            # A few REPRESENTATIVE slots per clinic-day, not a full grid:
            #   normal day -> up to 3 anchor times (early / mid / late)
            #   focus date -> up to 6 anchor times
            n = 6 if focus else 3
            last_start = close_min - visit
            if n == 1 or last_start == open_min:
                starts = [open_min]
            else:
                starts = sorted({
                    open_min + round(i * (last_start - open_min) / (n - 1))
                    for i in range(n)
                })
            for t in starts:
                start = hhmm(t)
                end = hhmm(t + visit)
                arrive = hhmm(max(open_min, t - CHECKIN_MIN))
                slot_id = (
                    f"DEMO_{r['clinic_id']}_{d:%Y%m%d}_{start.replace(':','')}"
                )
                note = (
                    f"FICTIONAL slot; {visit}-min visit and {CHECKIN_MIN}-min "
                    f"check-in are demo assumptions. Not bookable. Hours from "
                    f"clinics.csv ({r['schedule_basis']}). Add walking time after "
                    f"leaving clinic when routing return."
                )
                if focus:
                    note = "FOCUS DATE 2026-10-25. " + note
                out_rows.append({
                    "slot_id": slot_id,
                    "clinic_id": r["clinic_id"],
                    "clinic_name": r["clinic_name"],
                    "address": r["address"],
                    "town": r["town"],
                    "visit_type": r["visit_type"],
                    "appointment_date": f"{d:%Y-%m-%d}",
                    "start_time": start,
                    "end_time": end,
                    "visit_minutes": visit,
                    "arrive_by": arrive,
                    "earliest_return_departure": end,
                    "timezone": TZ,
                    "office_hours": f"{r['open_time']}-{r['close_time']}",
                    "source_url": r["source_url"],
                    "is_template": "TRUE",
                    "status": "Demo assumption",
                    "notes": note,
                })

    fieldnames = [
        "slot_id", "clinic_id", "clinic_name", "address", "town", "visit_type",
        "appointment_date", "start_time", "end_time", "visit_minutes", "arrive_by",
        "earliest_return_departure", "timezone", "office_hours", "source_url",
        "is_template", "status", "notes",
    ]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    focus_n = sum(1 for r in out_rows if r["appointment_date"] == "2026-10-25")
    print(f"wrote {len(out_rows)} slots to {OUT}")
    print(f"focus 2026-10-25: {focus_n} slots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
