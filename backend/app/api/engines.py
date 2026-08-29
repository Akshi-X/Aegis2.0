from fastapi import APIRouter
from pydantic import BaseModel

from app.services.orchestrator import ENGINE_TOGGLES
from app.services.engines.base import EngineStatus

router = APIRouter(tags=["Engines"])

class EngineToggleRequest(BaseModel):
    active: bool

@router.get("/engines/config", summary="Get the current toggle state for all engines")
def get_engine_config():
    return ENGINE_TOGGLES

@router.patch("/engines/config/{engine_key}", summary="Toggle a specific engine on or off")
def update_engine_config(engine_key: str, payload: EngineToggleRequest):
    ENGINE_TOGGLES[engine_key] = payload.active
    return ENGINE_TOGGLES
