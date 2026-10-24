"""GET /provenance?id (owner: M4, with M1). Powers the "How we know this is right" drawer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from api.deps import get_provenance_index
from api.schemas import ProvenanceResponse

router = APIRouter(tags=["provenance"])


@router.get("/provenance", response_model=ProvenanceResponse, summary="Trace an on-screen number")
def get_provenance(
    id: Annotated[str, Query(min_length=1, max_length=128, description="On-screen number id.")],
    index: Annotated[Mapping[str, Mapping[str, Any]], Depends(get_provenance_index)],
) -> ProvenanceResponse:
    record = index.get(id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No provenance record for id {id!r}.")
    try:
        return ProvenanceResponse.model_validate(record)
    except ValidationError:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provenance record {id!r} does not match the contract shape.",
        ) from None
