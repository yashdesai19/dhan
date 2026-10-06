"""Health check endpoint."""

from fastapi import APIRouter

from fastapi_app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    """Return application health status."""
    return HealthResponse(status="ok")
