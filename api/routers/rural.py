"""GET /rural?town — the rural lens (owner: M1).

mock mode : an empty, labelled answer (there is no per-block-group mock), so the map
            stays honest and the UI shows "needs real data".
real mode : engine.rural joins the cube (per block group) to the hand-collected rural
            tables (per town) through data/cache/bg_towns.parquet. Unknown town -> 404.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import RuralSource, get_rural_data
from api.schemas import RuralResponse, RuralSummary, SourceRef
from engine.rural import RuralDataError, rural as engine_rural

router = APIRouter(tags=["rural"])


@router.get("/rural", response_model=RuralResponse,
            summary="Rural lens: per-block-group 'no option at all' verdict")
def get_rural(
    source: Annotated[RuralSource, Depends(get_rural_data)],
    town: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> RuralResponse:
    if source.mode == "mock":
        return RuralResponse(
            town=town, features=[], options=[], towns_available=[],
            summary=RuralSummary(n_bg=0, carless_adults=0, by_verdict={}),
            sources=[SourceRef(name="mock (no block-group data in mock mode)", vintage="illustrative")],
        )
    try:
        data = engine_rural(source.cube, source.origins, source.towns, source.coverage, source.options, town)
    except RuralDataError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RuralResponse.model_validate(data)
