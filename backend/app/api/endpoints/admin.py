import logging
from fastapi import APIRouter, HTTPException
from app.services.qdrant_service import QdrantService
from app.core.greeting_config import get_greeting, set_greeting

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




