"""GET /audit (owner: M2). MOCK scaffold by M4; M2 replaces the data source."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from api.deps import get_audit_data
from api.schemas import AuditResponse, Day

router = APIRouter(tags=["audit"])


def with_day(data: dict[str, Any], day: str) -> dict[str, Any]:
    """Mock helper: stamp the requested day on every cell."""
    return {**data, "cells": [{**c, "day": day} for c in data["cells"]]}


@router.get("/audit", response_model=AuditResponse, summary="Reachability for clinic x community x day")
def get_audit(
    clinic: Annotated[str, Query(min_length=1, max_length=64)],
    community: Annotated[str, Query(min_length=1, max_length=64)],
    day: Annotated[Day, Query()],
    data: Annotated[dict[str, Any], Depends(get_audit_data)],
) -> AuditResponse:
    return AuditResponse.model_validate(with_day(data, day))
