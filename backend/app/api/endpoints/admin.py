import logging
from fastapi import APIRouter, HTTPException
from app.services.qdrant_service import QdrantService
from app.core.greeting_config import get_greeting, set_greeting
from app.core.inbound_config import get_inbound_status, set_inbound_status

router = APIRouter()
logger = logging.getLogger(__name__)
qdrant_service = QdrantService()

@router.get("/settings/greeting")
async def get_greeting_endpoint():
    """Get the current AI greeting."""
    return {"greeting": get_greeting()}

@router.post("/settings/greeting")
async def update_greeting(data: dict):
    """Update the AI greeting."""
    greeting = data.get("greeting")
    if not greeting:
        raise HTTPException(status_code=400, detail="Missing greeting text")
    set_greeting(greeting)
    return {"status": "success", "greeting": greeting}

@router.get("/settings/inbound")
async def get_inbound_endpoint():
    """Get the current inbound call status."""
    return {"enabled": get_inbound_status()}

@router.post("/settings/inbound")
async def update_inbound(data: dict):
    """Update the inbound call status."""
    if "enabled" not in data:
        raise HTTPException(status_code=400, detail="Missing 'enabled' field")
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=400, detail="'enabled' must be a boolean")
    set_inbound_status(enabled)
    logger.info(f"Inbound calls {'enabled' if enabled else 'disabled'}")
    return {"status": "success", "enabled": enabled}
