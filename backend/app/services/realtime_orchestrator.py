"""
Realtime Orchestrator - Ultra-low latency voice AI using OpenAI Realtime API.
Handles Twilio ↔ OpenAI Realtime WebSocket bridging.
"""
import json
import logging
import asyncio
import uuid
import time
from datetime import datetime, timezone, timedelta
import openai

from app.core.supabase_client import supabase
from app.core.greeting_config import get_greeting
from app.core.config import settings
from app.services.realtime_service import RealtimeService
from app.services.qdrant_service import QdrantService
from app.services.audio_service import get_openai_client

logger = logging.getLogger(__name__)

# System prompt for the AI assistant
SYSTEM_PROMPT = """You are VocalQ.ai's professional INBOUND AI phone assistant for Tekisho –
friendly, confident, and natural-sounding.

Your goal is to help callers politely and end the call once satisfied.

VOICE STYLE & DELIVERY:
- Speak with warmth, clarity, and natural pauses.
- Sound like a real human, never robotic.
- Use light conversational fillers only when natural.
- Vary tone: welcoming when greeting, calm when explaining, warm when asking.

CALL OPENING & LANGUAGE HANDLING:
- You MUST say EXACTLY this greeting at the start of EVERY call, word-for-word:
  "Hello, this is VocalQ from Tekisho. Which language do you prefer?"
- After saying this greeting, STOP SPEAKING IMMEDIATELY.
- WAIT and LISTEN for the caller's response.
- Do NOT add "How can I help you?" or any other words after the greeting.
- Automatically detect the caller's language from their response.
- Support multiple languages and mixed languages.
- DO NOT ask the caller to choose a language again.

LANGUAGE CONFIRMATION:
- If the user responds with a simple greeting (e.g., "Hi", "Hello"), DO NOT explicitly confirm the language. Just continue naturally.
- ONLY confirm the language if the user explicitly requests a switch or if there's ambiguity.
Examples:
- User: "Hi" -> You: "How can I help you today?"
- User: "Hindi mein bolo" -> You: "Theek hai, Hindi mein baat karte hain."

MULTILINGUAL & MIXED-LANGUAGE MIRRORING:
- Always mirror the caller's language and speaking style.
Rules:
- Pure English → respond in English.
- Pure Telugu → respond in Telugu.
- Hinglish / Tanglish / mixed language → respond in the same mix.
- If the caller switches language mid-call, switch immediately.
- Never force formal language if the caller is casual.

NAME USAGE (IF AVAILABLE):
- If a caller name is provided in context, use it ONCE naturally.
- Never guess or invent a name.
- If no name is available, use a polite neutral greeting.

INBOUND CALL BEHAVIOR:
- Answer the caller's questions politely and concisely.
- Use `search_knowledge_base` ONLY for business-related questions
  (services, pricing, plans, orders, policies, company details).
- If information is not found:
  - Say so politely.
  - Stop speaking after that.

GUARDRAILS & SCOPE CONTROL:
- If the caller asks about personal opinions, news, or unrelated topics,
  gently redirect back to Tekisho-related assistance.
- You CAN and SHOULD answer questions about VocalQ and Tekisho:
  - VocalQ is an AI voice assistant product built by Tekisho.
  - Tekisho is a technology company offering AI-powered solutions.
  - Use the knowledge base to find details about services, pricing, and features.
- If asked about INTERNAL technical implementation (APIs, code, models, infrastructure):
  - Say politely: "I can help with product information, but I don't have internal technical details."
- Do NOT explain how VocalQ is built internally.

INTERRUPTION HANDLING (CRITICAL):
- If the caller interrupts:
  - STOP speaking immediately.
  - Listen fully.
  - Respond only to the NEW input.
- Never talk over the caller.
- Never apologize for interruptions.

RESPONSE LENGTH:
- Keep responses to 1–2 short, conversational sentences.
- Under 10–15 words whenever possible.
- Ask permission before giving longer explanations.

CALL CLOSURE & TERMINATION:
- Once the caller sounds satisfied, move toward closing.

If the caller says:
"That's all", "I'm good", "No more questions", "Bye", "Thank you, bye"
1. Say: "Thank you for calling Tekisho. Have a wonderful day!"
2. CALL `end_call` IMMEDIATELY.

If the caller says only "Thank you":
1. Say: "You're welcome. Is there anything else I can help with?"
2. If they say "No": CALL `end_call` IMMEDIATELY.

STRICT DOs:
- Be polite, friendly, and calm.
- Stop immediately when interrupted.
- End the call once the caller is satisfied.

STRICT DON'Ts:
- Do NOT hallucinate.
- Do NOT discuss technology or internal systems.
- Do NOT repeat language selection.
- Do NOT exceed two sentences.
- Do NOT continue speaking when unsure.
"""

# Knowledge base search tool definition
KB_SEARCH_TOOL = {
    "type": "function",
    "name": "search_knowledge_base",
    "description": "Search the knowledge base for information about services, pricing, or policies.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant information."
            }
        },
        "required": ["query"]
    }
}


class RealtimeOrchestrator:
    """Orchestrator using OpenAI Realtime API for ultra-low latency voice AI."""
    
    def __init__(self, db, websocket):
        self.websocket = websocket
        self.call_id = str(uuid.uuid4())
        self.realtime_service = RealtimeService()
        self.qdrant_service = QdrantService()
        
        # Call state
        self.start_timestamp = None
        self.start_time_unix = time.time()
        self.stream_sid = None
        self.caller_number = "Unknown"
        self.greeting_triggered_at = 0
        self.total_token_usage = 0
        
        # Transcripts
        self.dashboard_transcript = []
        self.conversation_history = []
        
        # Events
        self.session_updated_event = asyncio.Event()
        
        logger.info(f"[{self.call_id}] Orchestrator initialized")

    async def start(self):
        """Initialize call session and connect to OpenAI Realtime API."""
        # Get current time in IST (UTC + 5:30)
        utc_now = datetime.now(timezone.utc)
        ist_offset = timedelta(hours=5, minutes=30)
        self.start_timestamp = utc_now + ist_offset
        logger.info(f"[{self.call_id}] Starting orchestrator, stream_sid={self.stream_sid}")
        
        # Initialize DB record in background
        asyncio.create_task(self._init_db_record())

        try:
            # Connect to OpenAI Realtime
            await self.realtime_service.connect()
            logger.info(f"[{self.call_id}] Connected to Realtime API")
            
            # Update session with system prompt and tools
            await self.realtime_service.update_session(
                instructions=SYSTEM_PROMPT, 
                tools=[KB_SEARCH_TOOL]
            )
            
            # Start event handler
            asyncio.create_task(self._handle_events())
            
            # Wait for session confirmation (reduced timeout for speed)
            try:
                await asyncio.wait_for(self.session_updated_event.wait(), timeout=1.5)
                logger.info(f"[{self.call_id}] Session updated confirmed")
            except asyncio.TimeoutError:
                logger.warning(f"[{self.call_id}] Session update timeout - proceeding anyway")

            # stream_sid should already be set before start() is called
            if not self.stream_sid:
                logger.error(f"[{self.call_id}] No stream_sid - cannot send greeting")
                return

            # Trigger initial greeting
            await self._send_greeting()

        except Exception as e:
            logger.error(f"[{self.call_id}] Start failed: {e}", exc_info=True)

    async def _send_greeting(self):
        """Send initial greeting to caller."""
        self.greeting_triggered_at = time.time()
        
        # Get dynamic greeting from config (set via UI)
        greeting_text = get_greeting()
        
        # Clear any noise in buffer
        await self.realtime_service.send_to_ws({"type": "input_audio_buffer.clear"})

        # Inject greeting as user instruction for AI to speak
        await self.realtime_service.send_to_ws({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": f"[SYSTEM INSTRUCTION - MANDATORY] You MUST say this exact greeting word-for-word, nothing more, nothing less: \"{greeting_text}\" Then STOP and WAIT for the caller to respond."
                }]
            }
        })
        
        # Request response with both text and audio
        await self.realtime_service.send_to_ws({
            "type": "response.create",
            "response": {"modalities": ["text", "audio"]}
        })
        
        logger.info(f"[{self.call_id}] Greeting triggered")

    async def _init_db_record(self):
        """Initialize call record in Supabase."""
        try:
            # Format IST timestamp (timezone-aware datetime already in IST)
            start_time_iso = self.start_timestamp.strftime('%Y-%m-%dT%H:%M:%S') + '+05:30'
            supabase.table("calls").insert({
                "call_id": self.call_id,
                "caller_number": self.caller_number,
                "start_time": start_time_iso,
                "created_at": start_time_iso,
                "call_status": "active",
                "language": "en-US"
            }).execute()
        except Exception as e:
            logger.warning(f"[{self.call_id}] DB insert failed: {e}")

    async def _handle_events(self):
        """Handle events from OpenAI Realtime API."""
        first_audio = False
        
        try:
            async for event in self.realtime_service.receive():
                event_type = event.get("type")
                
                # Session events
                if event_type == "session.updated":
                    self.session_updated_event.set()

                # Audio streaming to Twilio
                elif event_type == "response.audio.delta":
                    delta = event.get("delta")
                    if delta and self.stream_sid:
                        if not first_audio:
                            logger.info(f"[{self.call_id}] First audio delta")
                            first_audio = True
                        await self.websocket.send_text(json.dumps({
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": delta}
                        }))

                elif event_type == "response.audio.done":
                    first_audio = False
                
                # Token usage tracking - EXACT counts from OpenAI
                elif event_type == "response.done":
                    usage = event.get("response", {}).get("usage", {})
                    
                    # Get exact token breakdown
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    total = usage.get("total_tokens", 0)
                    
                    # If total is provided, use it; otherwise sum input+output
                    tokens_this_response = total if total > 0 else (input_tokens + output_tokens)
                    
                    if tokens_this_response > 0:
                        self.total_token_usage += tokens_this_response
                        logger.info(f"[{self.call_id}] Tokens this response: in={input_tokens}, out={output_tokens}, total={tokens_this_response} | Running total={self.total_token_usage}")
                    
                    # Log full usage object for debugging
                    if usage:
                        logger.debug(f"[{self.call_id}] Full usage data: {usage}")
                
                # Error handling
                elif event_type == "error":
                    logger.error(f"[{self.call_id}] OpenAI error: {event}")

                # User speech detection (for interruption)
                elif event_type == "input_audio_buffer.speech_started":
                    # Ignore noise during greeting
                    if time.time() - self.greeting_triggered_at < 1.5:
                        continue
                    
                    logger.info(f"[{self.call_id}] User speaking - interrupt")
                    await self.realtime_service.send_to_ws({"type": "response.cancel"})
                    if self.stream_sid:
                        await self.websocket.send_text(json.dumps({
                            "event": "clear",
                            "streamSid": self.stream_sid
                        }))

                # Tool calls (KB search)
                elif event_type == "response.function_call_arguments.done":
                    await self._handle_tool_call(event)

                # Transcript logging
                elif event_type == "response.audio_transcript.done":
                    transcript = event.get("transcript")
                    if transcript:
                        logger.info(f"[{self.call_id}] AI: {transcript}")
                        self._add_transcript("ai", transcript)

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript")
                    if transcript:
                        logger.info(f"[{self.call_id}] User: {transcript}")
                        self._add_transcript("user", transcript)

        except Exception as e:
            logger.error(f"[{self.call_id}] Event handler error: {e}")

    async def _handle_tool_call(self, event):
        """Handle knowledge base search tool call."""
        call_id = event.get("call_id")
        name = event.get("name")
        args = event.get("arguments")
        
        if name != "search_knowledge_base":
            return
            
        try:
            query = json.loads(args).get("query")
            logger.info(f"[{self.call_id}] KB search: '{query}'")
            
            results = await self.qdrant_service.search(query)
            result_text = "\n".join(results) if results else "No information found."
            
            await self.realtime_service.send_tool_output(call_id, result_text)
        except Exception as e:
            logger.error(f"[{self.call_id}] Tool call failed: {e}")
            await self.realtime_service.send_tool_output(call_id, "Error searching.")

    async def _translate_to_english_async(self, text: str) -> str:
        """Transliterate text to English/Roman script (non-blocking)."""
        # Skip transliteration if text is already ASCII (English)
        if text.isascii():
            return text
            
        try:
            client = get_openai_client()
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Transliterate to Roman script. Keep words, change script. Example: 'నమస్కారం' → 'Namaskaram'. Output only transliteration."
                    },
                    {"role": "user", "content": text}
                ],
                max_tokens=100,
                temperature=0.1
            )
            # Track tokens from transliteration
            if hasattr(response, 'usage') and response.usage:
                tokens = response.usage.total_tokens
                self.total_token_usage += tokens
                logger.info(f"[{self.call_id}] Transliteration tokens: +{tokens}")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Transliteration failed: {e}")
            return text

    def _add_transcript(self, speaker: str, text: str):
        """Add transcript entry immediately (transliteration happens in background)."""
        # Get current time in IST (UTC + 5:30)
        utc_now = datetime.now(timezone.utc)
        ist_offset = timedelta(hours=5, minutes=30)
        ist_time = utc_now + ist_offset
        now = ist_time.strftime('%Y-%m-%dT%H:%M:%S') + '+05:30'
        
        # Add transcript immediately with original text (no blocking)
        entry = {"speaker": speaker, "text": text, "timestamp": now}
        self.dashboard_transcript.append(entry)
        self.conversation_history.append({
            "role": "assistant" if speaker == "ai" else "user", 
            "content": text
        })
        
        # Transliterate in background if needed (non-blocking)
        if not text.isascii():
            asyncio.create_task(self._update_transcript_async(len(self.dashboard_transcript) - 1, text))
    
    async def _update_transcript_async(self, index: int, text: str):
        """Update transcript with transliterated text in background."""
        try:
            english_text = await self._translate_to_english_async(text)
            if index < len(self.dashboard_transcript):
                self.dashboard_transcript[index]["text"] = english_text
            if index < len(self.conversation_history):
                self.conversation_history[index]["content"] = english_text
        except Exception as e:
            logger.warning(f"Background transliteration failed: {e}")

    async def process_media(self, payload: str):
        """Forward audio from Twilio to OpenAI Realtime."""
        await self.realtime_service.send_audio(payload)

    async def handle_disconnect(self):
        """Clean up on call disconnect."""
        logger.info(f"[{self.call_id}] Call ended")
        await self.realtime_service.close()
        
        try:
            # Get current time in IST
            utc_now = datetime.now(timezone.utc)
            ist_offset = timedelta(hours=5, minutes=30)
            end_time = utc_now + ist_offset
            
            duration = int((end_time - self.start_timestamp).total_seconds())
            
            # Generate meaningful summary from conversation
            summary = self._generate_summary()
            
            supabase.table("calls").update({
                "call_status": "completed",
                "end_time": end_time.strftime('%Y-%m-%dT%H:%M:%S') + '+05:30',
                "call_duration": duration,
                "summary": summary,
                "transcript": self.dashboard_transcript,
                "token_usage": self.total_token_usage
            }).eq("call_id", self.call_id).execute()
            
            logger.info(f"[{self.call_id}] Saved. Duration: {duration}s, Tokens: {self.total_token_usage}")
        except Exception as e:
            logger.error(f"[{self.call_id}] DB update failed: {e}")

    def _generate_summary(self) -> str:
        """Generate short AI summary of the call."""
        if not self.conversation_history:
            return "No conversation."
        
        if len(self.conversation_history) <= 1:
            return "Short call - minimal interaction."
        
        # Build conversation text
        conversation_text = ""
        for msg in self.conversation_history:
            role = "Caller" if msg["role"] == "user" else "AI"
            conversation_text += f"{role}: {msg['content']}\n"
        
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Summarize this VocalQ call in 1-2 crisp sentences (max 3 if absolutely needed).

Format: "Caller asked about [topic]. [Outcome]."

Examples:
- "Caller asked about pricing plans. Provided VocalQ subscription details."
- "Caller inquired about Tekisho services. Information shared successfully."
- "Short call - caller hung up after greeting."

Be specific, professional, and ultra-concise."""
                    },
                    {"role": "user", "content": f"Call transcript:\n{conversation_text}"}
                ],
                max_tokens=80,
                temperature=0.2
            )
            # Track tokens from summary generation
            if hasattr(response, 'usage') and response.usage:
                tokens = response.usage.total_tokens
                self.total_token_usage += tokens
                logger.info(f"[{self.call_id}] Summary tokens: +{tokens}")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[{self.call_id}] Summary failed: {e}")
            return "Call completed."
