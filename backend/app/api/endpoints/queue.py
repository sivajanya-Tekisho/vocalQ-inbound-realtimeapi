"""
Call Queue Management Endpoint
Uses Supabase call_queue table for persistent storage.
"""
import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter()


class QueueItem(BaseModel):
    call_id: str
    caller_number: str
    priority: int = 0  # 0=normal, 1=high, 2=urgent
    status: str = "waiting"  # waiting, assigned, completed, cancelled
    assigned_to: Optional[str] = None


@router.get("/queue")
def get_queue():
    """Get all items in the call queue, sorted by priority desc then created_at."""
    try:
        response = (
            supabase.table("call_queue")
            .select("*")
            .order("priority", desc=True)
            .order("created_at")
            .execute()
        )
        items = response.data or []
        return {"success": True, "count": len(items), "queue": items}
    except Exception as e:
        logger.error(f"Queue fetch error: {e}")
        return {"success": True, "count": 0, "queue": []}


@router.post("/queue")
def add_to_queue(item: QueueItem):
    """Add a call to the queue."""
    try:
        row = {
            "call_id": item.call_id,
            "caller_number": item.caller_number,
            "priority": item.priority,
            "status": item.status,
            "assigned_to": item.assigned_to,
        }
        response = supabase.table("call_queue").insert(row).execute()
        logger.info(f"Added call {item.call_id} to queue (priority {item.priority})")
        return {"success": True, "message": "Call added to queue", "item": response.data[0] if response.data else row}
    except Exception as e:
        logger.error(f"Queue insert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/queue/{call_id}")
def remove_from_queue(call_id: str):
    """Remove a call from the queue."""
    try:
        response = supabase.table("call_queue").delete().eq("call_id", call_id).execute()
        if response.data:
            logger.info(f"Removed call {call_id} from queue")
            return {"success": True, "message": f"Call {call_id} removed from queue"}
        raise HTTPException(status_code=404, detail="Call not found in queue")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Queue delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/queue/{call_id}")
def update_queue_item(call_id: str, updates: Dict):
    """Update a queue item (status, priority, assignment)."""
    try:
        # Add timestamp for status changes
        if updates.get("status") == "assigned":
            updates["assigned_at"] = datetime.now().isoformat()
        elif updates.get("status") == "completed":
            updates["completed_at"] = datetime.now().isoformat()

        response = supabase.table("call_queue").update(updates).eq("call_id", call_id).execute()
        if response.data:
            logger.info(f"Updated queue item {call_id}: {updates}")
            return {"success": True, "item": response.data[0]}
        raise HTTPException(status_code=404, detail="Call not found in queue")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Queue update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/stats")
def get_queue_stats():
    """Get queue statistics."""
    try:
        response = supabase.table("call_queue").select("*").execute()
        items = response.data or []
        waiting = len([i for i in items if i.get("status") == "waiting"])
        assigned = len([i for i in items if i.get("status") == "assigned"])
        high_priority = len([i for i in items if i.get("priority", 0) >= 1])
        return {
            "total": len(items),
            "waiting": waiting,
            "assigned": assigned,
            "high_priority": high_priority,
        }
    except Exception as e:
        logger.error(f"Queue stats error: {e}")
        return {"total": 0, "waiting": 0, "assigned": 0, "high_priority": 0}
