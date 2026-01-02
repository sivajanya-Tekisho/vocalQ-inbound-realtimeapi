from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.orchestrator import ConversationOrchestrator
import logging
import json
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

import sys

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("\n[TELEPHONY] --- NEW INBOUND WEBSOCKET CONNECTION ---")
    sys.stdout.flush()
    await websocket.accept()
    logger.info("[TELEPHONY] --- CONNECTION ACCEPTED ---")
    sys.stdout.flush()
    
    orchestrator = None
    
    try:
        orchestrator = ConversationOrchestrator(None, websocket)
        logger.info("WebSocket connection accepted")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        logger.error(f"--- ERROR: Failed to initialize orchestrator: {e} ---")
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
        await websocket.close()
        return
    
    try:
        try:
            while True:
                # Twilio sends JSON messages
                message = await websocket.receive_text()
                data = json.loads(message)
                event = data.get("event")
                
                if event == "connected":
                    logger.info("Twilio connected")
                    logger.info("--- Twilio Connected ---")
                    sys.stdout.flush()
                    
                elif event == "start":
                    start_data = data.get("start", {})
                    stream_sid = start_data.get("streamSid")
                    # Caller data is passed via custom parameters in the Twilio webhook TwiML
                    custom_params = start_data.get("customParameters", {})
                    caller_number = custom_params.get("callerNumber") or start_data.get("from") or "Unknown"
                    
                    logger.info(f"Stream started: {stream_sid}, Caller: {caller_number}")
                    logger.info(f"--- Stream started: {stream_sid}, Caller: {caller_number} ---")
                    sys.stdout.flush()
                    
                    if orchestrator:
                        orchestrator.stream_sid = stream_sid
                        orchestrator.caller_number = caller_number
                        
                        # Start orchestrator in background so it doesn't block receiving media
                        asyncio.create_task(orchestrator.start())
                        logger.info(f"--- Orchestrator Start Task Created for Stream: {stream_sid} ---")
                        sys.stdout.flush()
                    
                elif event == "media":
                    # Payload is base64 encoded audio (8k mulaw usually)
                    payload = data.get("media", {}).get("payload")
                    if payload and orchestrator:
                        await orchestrator.process_media(payload)
                        
                elif event == "stop":
                    logger.info("Stream stopped message received")
                    logger.info("--- Stream Stopped ---")
                    sys.stdout.flush()
                    break
                    
                elif event == "dtmf":
                    pass
        finally:
            # Ensure cleanup happens even if the loop breaks or errors
            if orchestrator:
                logger.info(f"[TELEPHONY] Triggering manual disconnect cleanup for {orchestrator.call_id}")
                await orchestrator.handle_disconnect()
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        logger.info("--- WebSocket Disconnected ---")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        logger.error(f"--- ERROR: WebSocket error: {e} ---")
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
    finally:
        try:
            await websocket.close()
        except:
            pass

