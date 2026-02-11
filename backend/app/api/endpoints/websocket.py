"""
WebSocket endpoint for Twilio Media Streams.
Handles inbound voice calls via OpenAI Realtime API.
"""
import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime_orchestrator import RealtimeOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """Handle Twilio Media Stream WebSocket connection."""
    logger.info("[WS] New inbound connection")
    await websocket.accept()
    
    orchestrator = None
    
    try:
        orchestrator = RealtimeOrchestrator(None, websocket)
    except Exception as e:
        logger.error(f"[WS] Failed to initialize orchestrator: {e}", exc_info=True)
        await websocket.close()
        return
    
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")
            
            if event == "connected":
                logger.info("[WS] Twilio connected")
                
            elif event == "start":
                start_data = data.get("start", {})
                stream_sid = start_data.get("streamSid")
                custom_params = start_data.get("customParameters", {})
                caller_number = custom_params.get("callerNumber") or start_data.get("from") or "Unknown"
                
                logger.info(f"[WS] Stream started: {stream_sid}, Caller: {caller_number}")
                
                if orchestrator:
                    orchestrator.stream_sid = stream_sid
                    orchestrator.caller_number = caller_number
                    asyncio.create_task(orchestrator.start())
                
            elif event == "media":
                payload = data.get("media", {}).get("payload")
                if payload and orchestrator:
                    await orchestrator.process_media(payload)
                    
            elif event == "stop":
                logger.info("[WS] Stream stopped")
                break

    except WebSocketDisconnect:
        logger.info("[WS] Disconnected")
    except Exception as e:
        logger.error(f"[WS] Error: {e}", exc_info=True)
    finally:
        if orchestrator:
            await orchestrator.handle_disconnect()
        try:
            await websocket.close()
        except:
            pass

