"""Response models for the health endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness payload.

    The shape is contractual -- deployment probes and the frontend both depend
    on exactly these two fields.
    """

    status: str = Field(examples=["healthy"])
    service: str = Field(examples=["aegis-x"])


class ReadinessResponse(BaseModel):
    """Readiness payload: liveness plus dependency status."""

    status: str = Field(examples=["ready"])
    service: str = Field(examples=["aegis-x"])
    version: str = Field(examples=["0.1.0"])
    database: str = Field(examples=["connected", "unavailable"])
    detail: str | None = None
