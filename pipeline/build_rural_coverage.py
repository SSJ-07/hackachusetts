#!/usr/bin/env python3
"""Build the rural "no option at all" coverage layer from rural_options.csv.

Classifies each Franklin/Hampshire town into a transport-coverage tier so the UI's
rural lens can flag transit deserts. Reads data/manual/rural_options.csv and writes
data/manual/rural_coverage.csv.

GUARDRAILS (AGENTS.md):
- Logistics only. This is a coverage classification, never a clinical/eligibility call.
- Every row carries provenance: it inherits source_url + verified_by from rural_options.
- Values are NOT invented. "none" only when every option column is empty/absent.

Tier definitions (best available option per town):
  fixed_route        PVTA/FRTA scheduled fixed-route bus serves the town
  demand_response    dial-a-ride / FRTA demand response / PVTA Senior Dial-A-Ride
  assisted_only      only COA volunteer driver and/or PT-1 (no bus, no dial-a-ride)
  none               no transit, no dial-a-ride, no COA driver, no PT-1

NOTE: This is the DATA layer. True reachability (can a patient actually get to a given
clinic and back) comes from the engine's reachability cube, not from this file. This
layer answers "does this town have ANY transport option at all", which the cube cannot
express for a town with zero service. Join on `town`.
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "manual" / "rural_options.csv"
OUT = ROOT / "data" / "manual" / "rural_coverage.csv"

EMPTY = {"", "none", "n/a", "na", "todo-verify", None}


def present(v: str | None) -> bool:
    return v is not None and v.strip().lower() not in EMPTY


def tier(row: dict) -> str:
    dar = (row.get("dial_a_ride") or "").strip()
    dar_l = dar.lower()
    coa = present(row.get("coa_driver"))
    pt1 = present(row.get("pt1"))
    # fixed-route bus named explicitly in the dial_a_ride cell
    if "fixed route" in dar_l or "pvta fixed" in dar_l:
        return "fixed_route"
    # any demand-response / dial-a-ride service
    if present(dar) and ("demand response" in dar_l or "dial-a-ride" in dar_l
                         or "easy ride" in dar_l or "senior" in dar_l):
        return "demand_response"
    # only assisted options remain
    if coa or pt1:
        return "assisted_only"
    return "none"


def main() -> int:
    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    out = []
    for r in rows:
        t = tier(r)
        out.append({
            "town": r["town"],
            "county": r.get("county", ""),
            "coverage_tier": t,
            "has_any_option": "FALSE" if t == "none" else "TRUE",
            "dial_a_ride": r.get("dial_a_ride", ""),
            "coa_driver": r.get("coa_driver", ""),
            "pt1": r.get("pt1", ""),
            "source_url": r.get("source_url", ""),
            "verified_by": r.get("verified_by", ""),
            "date": r.get("date", ""),
        })

    fieldnames = ["town", "county", "coverage_tier", "has_any_option", "dial_a_ride",
                  "coa_driver", "pt1", "source_url", "verified_by", "date"]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out)

    from collections import Counter
    c = Counter(r["coverage_tier"] for r in out)
    print(f"wrote {len(out)} towns to {OUT}")
    print("tiers:", dict(c))
    none_towns = [r["town"] for r in out if r["coverage_tier"] == "none"]
    print("no-option towns:", none_towns or "(none — every town has at least one option)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
