import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Response, Request
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter()

def normalize_transcript(transcript):
    """Convert old role/content format to speaker/text format for frontend."""
    if not transcript:
        return []
    if isinstance(transcript, str):
        try:
            transcript = json.loads(transcript)
        except:
            return []
    
    normalized = []
    for item in transcript:
        if isinstance(item, dict):
            # Already in correct format
            if "speaker" in item and "text" in item:
                normalized.append(item)
            # Old format: role/content
            elif "role" in item and "content" in item:
                speaker = "ai" if item["role"] in ["assistant", "ai"] else "user"
                normalized.append({
                    "speaker": speaker,
                    "text": item["content"],
                    "timestamp": item.get("timestamp", "")
                })
    return normalized

def map_call(c):
    # Extract summary from nested call_summaries list if using join
    summaries = c.get("call_summaries", [])
    summary_text = ""
    if summaries and isinstance(summaries, list) and len(summaries) > 0:
        summary_text = summaries[0].get("summary_text") or ""
    elif isinstance(summaries, dict):
        summary_text = summaries.get("summary_text") or ""

    timestamp = c.get("start_time") or c.get("created_at")
    if timestamp and isinstance(timestamp, str):
        # Convert space to 'T' if needed (database format compatibility)
        timestamp = timestamp.replace(' ', 'T')
        # Don't add 'Z' if timezone info (+05:30) already exists
        # Only add 'Z' for timestamps without any timezone info
        if 'Z' not in timestamp and '+' not in timestamp and '-' not in timestamp[10:]:
            timestamp += 'Z'

    return {
        "id": c.get("call_id") or c.get("id", "Unknown"),
        "caller": c.get("caller_number") or "Unknown",
        "timestamp": timestamp,
        "duration": c.get("call_duration") or 0,
        "status": c.get("call_status") or "active",
        "intent": c.get("intent") or "N/A",
        "summary": summary_text or c.get("summary") or "",
        "transcript": normalize_transcript(c.get("transcript")),
        "language": c.get("language") or "en-US",
        "token_usage": c.get("token_usage") or 0
    }

@router.get("/")
def read_calls(skip: int = 0, limit: int = 100, status: Optional[str] = None):
    # Fallback to created_at if start_time is missing in cache
    # Also fetch summary_text from call_summaries join
    # Primary sort by start_time, secondary by created_at to handle legacy/null cases
    query = supabase.table("calls").select("*, call_summaries(summary_text)").order("start_time", desc=True).order("created_at", desc=True).range(skip, skip + limit - 1)
    if status:
        query = query.eq("call_status", status)
    
    try:
        response = query.execute()
    except Exception as e:
        logger.error(f"Error fetching calls: {e}")
        # Fallback to just created_at
        response = supabase.table("calls").select("*, call_summaries(summary_text)").order("created_at", desc=True).range(skip, skip + limit - 1).execute()
        
    data = response.data or []
    return [map_call(c) for c in data]

@router.get("/active")
def read_active_calls():
    response = supabase.table("calls").select("*").eq("call_status", "active").execute()
    data = response.data or []
    return [map_call(c) for c in data]

@router.get("/analytics")
def get_analytics():
    try:
        # Fetch all calls for analytics
        response = supabase.table("calls").select("*").execute()
        calls = response.data or []
        
        total_calls = len(calls)
        completed_calls = len([c for c in calls if c.get("call_status") == "completed"])
        missed_calls = len([c for c in calls if c.get("call_status") in ["missed", "dropped", "no-answer"]])
        
        durations = [c.get("call_duration") or 0 for c in calls if c.get("call_duration")]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        intent_counts = {}
        for c in calls:
            intent = c.get("intent") or "unknown"
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        # Calculate calls by hour for "Peak Window"
        from datetime import datetime
        from collections import defaultdict
        import dateutil.parser

        calls_by_hour = defaultdict(int)
        for c in calls:
            start_time_str = c.get("start_time") or c.get("created_at")
            if start_time_str:
                try:
                     dt = dateutil.parser.parse(start_time_str)
                     # Use 24-hour format for sorting, then convert to 12-hour for display
                     hour_24 = dt.hour
                     calls_by_hour[hour_24] += 1
                except:
                    pass

        # Convert to sorted list with proper time labels
        def hour_to_label(h):
            if h == 0:
                return "12 AM"
            elif h < 12:
                return f"{h} AM"
            elif h == 12:
                return "12 PM"
            else:
                return f"{h-12} PM"
        
        # Sort by hour and create display data
        hour_wise_data = [{"name": hour_to_label(h), "value": calls_by_hour[h]} for h in sorted(calls_by_hour.keys())]
        
        # Calculate peak window (2-hour range with most calls)
        peak_window = "N/A"
        if calls_by_hour:
            # Group into 2-hour windows
            windows = {}
            for h in range(0, 24, 2):
                window_calls = calls_by_hour.get(h, 0) + calls_by_hour.get(h+1, 0)
                if window_calls > 0:
                    windows[h] = window_calls
            
            if windows:
                peak_start = max(windows, key=windows.get)
                peak_end = peak_start + 2
                peak_window = f"{hour_to_label(peak_start)} - {hour_to_label(peak_end if peak_end < 24 else 0)}"
        
        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "missed_calls": missed_calls,
            "avg_duration": avg_duration,
            "intent_distribution": intent_counts,
            "calls_by_hour": hour_wise_data,
            "peak_window": peak_window
        }
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return {
            "total_calls": 0,
            "completed_calls": 0,
            "missed_calls": 0,
            "avg_duration": 0,
            "intent_distribution": {},
            "calls_by_hour": [],
            "peak_window": "N/A"
        }

@router.post("/twilio")
@router.post("/voice")
async def twilio_webhook(request: Request):
    """
    TwiML webhook for Twilio to handle incoming calls.
    Instructs Twilio to start a bidirectional media stream to our WebSocket.
    """
    host = request.headers.get("host")
    is_secure = request.headers.get("x-forwarded-proto") == "https" or \
                ".ngrok" in host or \
                ".loca.lt" in host or \
                "serveo" in host
    protocol = "wss" if is_secure else "ws"
    ws_url = f"{protocol}://{host}/api/v1/stream"
    
    # Capture caller info from Twilio POST body
    form_data = await request.form()
    caller_number = form_data.get("From", "Unknown")
    
    logger.info("--- TWILIO WEBHOOK CALLED ---")
    logger.info(f"Caller: {caller_number}")
    logger.info(f"Host: {host}")
    logger.info(f"Protocol: {protocol}")
    logger.info(f"Generated WS URL: {ws_url}")
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="callerNumber" value="{caller_number}" />
        </Stream>
    </Connect>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")

@router.get("/{call_id}")
def read_call(call_id: str):
    # Fetch call details with summary join
    call_response = supabase.table("calls").select("*, call_summaries(summary_text)").eq("call_id", call_id).single().execute()
    if not call_response.data:
        return None
        
    return map_call(call_response.data)
