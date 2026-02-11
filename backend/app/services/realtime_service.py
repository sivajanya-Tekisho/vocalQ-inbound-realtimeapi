import asyncio
import json
import logging
import websockets
from app.core.config import settings

logger = logging.getLogger(__name__)

class RealtimeService:
    def __init__(self):
        # Use GPT-4o-mini Realtime Model (cheaper and faster)
        self.url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
        self.api_key = settings.OPENAI_API_KEY
        self.ws = None
        self.session_config = None

    async def connect(self):
        """Establish WebSocket connection to OpenAI Realtime API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        try:
            logger.info(f"Connecting to OpenAI Realtime at {self.url}...")
            self.ws = await websockets.connect(self.url, additional_headers=headers)
            logger.info("Connected to OpenAI Realtime API - WebSocket Open")
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            raise

    async def update_session(self, instructions: str = None, tools: list = None):
        """Update session configuration."""
        if not self.ws:
            raise RuntimeError("WebSocket is not connected")

        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": "alloy",
                "temperature": 0.6,
                "max_response_output_tokens": 150,
                "input_audio_transcription": {
                    "model": "whisper-1"
                }, 
                "turn_detection": {
                     "type": "server_vad",
                     "threshold": 0.4,
                     "prefix_padding_ms": 150,
                     "silence_duration_ms": 200,
                     "create_response": True
                }
            }
        }
        
        
        if instructions:
            session_update["session"]["instructions"] = instructions
        
        if tools:
            session_update["session"]["tools"] = tools
            session_update["session"]["tool_choice"] = "auto"

        logger.info("Sending session.update to OpenAI")
        await self.ws.send(json.dumps(session_update))

    async def send_audio(self, base64_audio: str):
        """Send audio delta to OpenAI."""
        if not self.ws:
             return
    
        event = {
            "type": "input_audio_buffer.append",
            "audio": base64_audio
        }
        await self.ws.send(json.dumps(event))
        
        
    async def commit_audio(self):
         """Commit audio buffer (usually not needed with VAD enabled, but good practice)."""
         if not self.ws:
             return
         await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
         
    async def create_response(self):
        """Trigger a response generation."""
        if not self.ws:
            return
        await self.ws.send(json.dumps({"type": "response.create"}))

    async def send_to_ws(self, event: dict):
        """Send a raw event dictionary to the WebSocket."""
        if not self.ws:
            return
        await self.ws.send(json.dumps(event))

    async def send_conversation_item(self, item: dict):
        """Send a conversation item (e.g. system message or user message)."""
        if not self.ws:
            return
        event = {
            "type": "conversation.item.create",
            "item": item
        }
        await self.ws.send(json.dumps(event))

    async def send_tool_output(self, call_id: str, output: str):
        """Send tool output back to OpenAI."""
        if not self.ws:
            return
            
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output
            }
        }
        await self.ws.send(json.dumps(event))
        
        # Trigger another response after tool output
        await self.create_response()

    async def receive(self):
        """Yield events from OpenAI WebSocket."""
        if not self.ws:
            return
        
        async for message in self.ws:
            try:
                data = json.loads(message)
                yield data
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON from OpenAI")
    
    async def close(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
