"""AEGIS-X API entrypoint.

AEGIS-X is a pre-execution security and governance layer for autonomous
financial agents. Phase 0 establishes the service skeleton only: configuration,
database wiring, CORS, and health probes.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.actions import router as actions_router
from app.api.agent import router as agent_router
from app.api.engines import router as engines_router
from app.api.router import api_router
from app.core.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("aegis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "%s v%s starting (environment=%s)",
        settings.project_name,
        settings.version,
        settings.environment,
    )

    if settings.auto_init_db:
        # Deliberately non-fatal. The liveness contract established in Phase 0
        # is that the service boots and serves /health even with no database;
        # crashing here would break that and turn a slow-starting PostgreSQL
        # into a crash loop. /health/ready reports the real story.
        try:
            from app.database.init_db import init_db

            init_db(seed=True)
        except Exception:  # noqa: BLE001 - startup must not be fatal
            logger.warning(
                "Database initialisation failed; the API will start anyway. "
                "Check /health/ready for details.",
                exc_info=True,
            )

    yield
    logger.info("%s shutting down", settings.project_name)


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description=(
        "Pre-execution security and governance layer for autonomous "
        "financial agents."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health probes live at the service root by convention, so they stay stable
# across API versions. Versioned feature routers will mount under
# settings.api_v1_prefix.
app.include_router(agent_router)
app.include_router(actions_router)
app.include_router(engines_router)
app.include_router(api_router)


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict[str, str]:
    return {
        "service": settings.service_name,
        "name": settings.project_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
    }
