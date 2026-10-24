"""POST /whatif (owner: M2). MOCK scaffold by M4; M2 replaces the recompute.

Returns the same shape as GET /audit (docs/contracts.md §3).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from api.deps import get_audit_data
from api.routers.audit import with_day
from api.schemas import AuditResponse, WhatIfRequest

router = APIRouter(tags=["whatif"])


@router.post("/whatif", response_model=AuditResponse, summary="Recompute after moving a clinic block")
def post_whatif(
    request: WhatIfRequest,
    data: Annotated[dict[str, Any], Depends(get_audit_data)],
) -> AuditResponse:
    day = request.shift.block.split("-", 1)[0]
    return AuditResponse.model_validate(with_day(data, day))
