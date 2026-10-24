"""Single FastAPI entry point for Slot-to-Stop.

Run from the repo root:  make api   (or: python -m uvicorn api.main:app --reload)
"""

from __future__ import annotations

from fastapi import FastAPI, Request

from api import __version__
from api.deps import data_mode
from api.routers import audit, clinics, plan, provenance, rural, suggest, whatif
from api.schemas import HealthResponse


def create_app() -> FastAPI:
    mode = data_mode()
    app = FastAPI(
        title="Slot-to-Stop: Reachable Care API",
        version=__version__,
        description=(
            "Contracts: docs/contracts.md. Synthetic patients only; logistics only. "
            f"Data mode: {mode}."
        ),
    )

    @app.middleware("http")
    async def tag_data_mode(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Data-Mode"] = mode
        return response

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(version=__version__, data_mode=mode)

    app.include_router(audit.router)  # M2
    app.include_router(clinics.router)  # M1 (web Audit screen)
    app.include_router(whatif.router)  # M2
    app.include_router(suggest.router)  # M1 (optimizer -> Suggest panel)
    app.include_router(rural.router)  # M1 (rural lens)
    app.include_router(plan.router)  # M4
    app.include_router(provenance.router)  # M4

    return app


app = create_app()
