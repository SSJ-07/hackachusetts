"""GET /clinics — the clinic picker for the web Audit screen.

Reads data/manual/clinic_stops.csv (committed, hand-collected manual data) in both
data modes: it is the list of clinics the cube is built for, not a mock.
"""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from api.schemas import Clinic, ClinicsResponse, SourceRef

router = APIRouter(tags=["clinics"])

CLINIC_STOPS = Path(__file__).resolve().parents[2] / "data" / "manual" / "clinic_stops.csv"


def load_clinics(path: Path = CLINIC_STOPS) -> list[Clinic]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [
            Clinic(
                clinic_id=row["clinic_id"],
                clinic_name=row["clinic_name"],
                visit_type=row["visit_type"],
                visit_minutes=int(row["visit_minutes"]),
                stop_id=row["stop_id"],
                is_demo_anchor=row.get("is_demo_anchor", "").strip().upper() == "TRUE",
            )
            for row in csv.DictReader(fh)
        ]


@router.get("/clinics", response_model=ClinicsResponse, summary="Clinics the audit covers")
def get_clinics() -> ClinicsResponse:
    try:
        clinics = load_clinics()
    except (FileNotFoundError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Clinic list (data/manual/clinic_stops.csv) is not available.") from exc
    return ClinicsResponse(
        clinics=clinics,
        sources=[SourceRef(name="clinic_stops.csv (clinic -> PVTA stop anchors, M3/M1)",
                           vintage="2026-09 PVTA feed", url=None)],
    )
