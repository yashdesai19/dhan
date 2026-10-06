"""Health schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for GET /health response."""

    status: str
