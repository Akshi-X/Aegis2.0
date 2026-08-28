"""Health and readiness endpoints.

Two distinct probes, deliberately:

* ``/health``    -- liveness. Answers "is the process up?" and must never
                    depend on external services, otherwise a database blip
                    would cause an orchestrator to kill a healthy container.
* ``/health/ready`` -- readiness. Answers "can this instance do useful work?"
                    and therefore does check PostgreSQL.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.database.session import check_database_connection
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    return HealthResponse(status="healthy", service=settings.service_name)


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe (includes PostgreSQL)",
)
def readiness(response: Response) -> ReadinessResponse:
    connected, error = check_database_connection()

    if not connected:
        # 503 so orchestrators stop routing traffic here, while the process
        # itself stays alive and keeps reporting on /health.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if connected else "degraded",
        service=settings.service_name,
        version=settings.version,
        database="connected" if connected else "unavailable",
        detail=None if connected else error,
    )
