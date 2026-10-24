"""GET /audit (owner: M2).

mock mode : return the labelled mock (api/mocks/audit.json), day stamped on each
            cell, so the existing contract tests stay green.
real mode : aggregate the reachability cube through engine.audit.audit (the ONE
            aggregation path). A clinic/day/community with no cube rows -> 404.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import AuditSource, get_audit_data
from api.schemas import AuditResponse, BlockGroupsResponse, Day, SourceRef
from engine.audit import AuditDataError, audit as engine_audit, blockgroups as engine_blockgroups

router = APIRouter(tags=["audit"])


def with_day(data: dict[str, Any], day: str) -> dict[str, Any]:
    """Mock helper: stamp the requested day on every cell."""
    return {**data, "cells": [{**c, "day": day} for c in data["cells"]]}


@router.get("/audit", response_model=AuditResponse, summary="Reachability for clinic x community x day")
def get_audit(
    clinic: Annotated[str, Query(min_length=1, max_length=64)],
    community: Annotated[str, Query(min_length=1, max_length=64)],
    day: Annotated[Day, Query()],
    source: Annotated[AuditSource, Depends(get_audit_data)],
) -> AuditResponse:
    if source.mode == "mock":
        return AuditResponse.model_validate(with_day(source.payload or {}, day))
    try:
        data = engine_audit(source.cube, source.origins, clinic, community, day)
    except AuditDataError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AuditResponse.model_validate(data)


@router.get("/audit/blockgroups", response_model=BlockGroupsResponse,
            summary="Per-block-group reachable share for the map")
def get_audit_blockgroups(
    clinic: Annotated[str, Query(min_length=1, max_length=64)],
    day: Annotated[Day, Query()],
    source: Annotated[AuditSource, Depends(get_audit_data)],
    hour: Annotated[int | None, Query(ge=0, le=23)] = None,
    community: Annotated[str, Query(min_length=1, max_length=64)] = "all",
) -> BlockGroupsResponse:
    if source.mode == "mock":
        # No per-block-group mock exists; an empty, labelled answer keeps the map honest.
        return BlockGroupsResponse(features=[], sources=[
            SourceRef(name="mock (no block-group data in mock mode)", vintage="illustrative")])
    try:
        data = engine_blockgroups(source.cube, source.origins, clinic, day, hour, community)
    except AuditDataError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BlockGroupsResponse.model_validate(data)
