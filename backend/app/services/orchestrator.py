import json
import logging
import base64
import asyncio
import sys
import audioop
import uuid
import time
from datetime import datetime, timezone, timedelta
from app.core.supabase_client import supabase
from app.services.llm_service import LLMService
from app.services.audio_service import AudioService, VADService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

class ConversationOrchestrator:
    def __init__(self, db, websocket):
        logger.info("--- Initializing ConversationOrchestrator ---")
        sys.stdout.flush()
        self.websocket = websocket
        # Generate call_id locally so we don't depend on DB response to find it
        self.call_id = str(uuid.uuid4())
        self.llm_service = LLMService()
        self.qdrant_service = QdrantService()
        self.vad_service = VADService(aggressiveness=3)
        self.IST = timezone(timedelta(hours=5, minutes=30))
        self.start_time_unix = time.time()
        self.conversation_history = []
        self.dashboard_transcript = []
        self.start_timestamp = None
        self.stream_sid = None # Captured from Twilio start event
        self.caller_number = "Unknown" # Captured from Twilio start event
        logger.info(f"--- Orchestrator Initialized: {self.call_id} ---")
        sys.stdout.flush()
        
        # Audio Buffers
        self.incoming_buffer = bytearray() # Buffer for VAD processing
        self.pcm_buffer = bytearray() # Buffer for detected speech
        self.speech_detected = False
        self.silence_frames = 0
        self.speech_frames = 0
        self.SILENCE_THRESHOLD = 8 # ~250ms (Increased from 6)
        self.MAX_SPEECH_FRAMES = 90 # ~2.8s (Increased for buffer)
        self.ENERGY_THRESHOLD = 400 # Increased from 300 to further reduce noise triggers
        self.MIN_SPEECH_DURATION = 0.5 # Seconds
        self.working_columns = set() # Track columns that work
        # Lock for processing to avoid overlapping transcriptions
        self.processing_lock = asyncio.Lock()
        self.interrupt_flag = False

    async def start(self):
        """Initialize a new call session, send greeting, and sync to DB."""
        logger.info(f"--- [CALL {self.call_id}] Orchestrator Start Initiated ---")
        sys.stdout.flush()
        
        # 1. Initialize call in Supabase
        self.start_timestamp = datetime.now(self.IST)
        self.start_time_unix = time.time() # Reset to actual call connection time
        # Initialize VAD model in background
        asyncio.create_task(self.vad_service.initialize())
        
        try:
            logger.info(f"--- [CALL {self.call_id}] Inserting into Supabase (Robust Mode)... ---")
            sys.stdout.flush()
            
            # ISO format with IST offset
            start_time_iso = self.start_timestamp.strftime('%Y-%m-%dT%H:%M:%S+05:30')
            
            full_data = {
                "call_id": self.call_id,
                "caller_number": self.caller_number, 
                "start_time": start_time_iso,
                "created_at": start_time_iso,
                "call_status": "active",
                "language": "en-US"
            }
            
            # First attempt: Try full data
            try:
                logger.info(f"[CALL {self.call_id}] Attempting full data insert: {full_data}")
                response = supabase.table("calls").insert(full_data).execute()
                logger.info(f"--- [CALL {self.call_id}] NEW CALL STARTED - Full data insert success: {response.data} ---")
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"--- [CALL {self.call_id}] Full insert failed: {err_msg[:200]}... Trying minimal... ---")
                
                # Second attempt: Minimal data (known safe columns)
                try:
                    minimal_data = {
                        "call_id": self.call_id, 
                        "caller_number": self.caller_number,
                        "start_time": self.start_timestamp.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                        "call_status": "active"
                    }
                    response = supabase.table("calls").insert(minimal_data).execute()
                    logger.info(f"--- [CALL {self.call_id}] NEW CALL STARTED - Minimal insert success: {response.data} ---")
                except Exception as e2:
                    err_msg2 = str(e2)
                    logger.warning(f"--- [CALL {self.call_id}] Minimal insert failed: {err_msg2[:200]}... Trying ULTRA-MINIMAL... ---")
                    
                    # Third attempt: ULTRA-MINIMAL (just the primary key)
                    try:
                        ultra_minimal = {"call_id": self.call_id}
                        response = supabase.table("calls").insert(ultra_minimal).execute()
                        logger.info(f"--- [CALL {self.call_id}] NEW CALL STARTED - Ultra-minimal insert success: {response.data} ---")
                    except Exception as e3:
                        logger.error(f"--- [CALL {self.call_id}] CRITICAL: All insert attempts failed: {e3} ---")
                        import traceback
                        logger.error(traceback.format_exc())
            
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Failed to start call in Supabase: {e}")
            print(f"--- ERROR: Failed to start call in Supabase: {e} ---")
            sys.stdout.flush()
            
        # 2. Initial Greeting - Wait for stream_sid and then greet
        logger.info(f"[CALL {self.call_id}] Waiting for stream_sid...")
        wait_start = datetime.utcnow()
        while not self.stream_sid and (datetime.utcnow() - wait_start).total_seconds() < 5:
            await asyncio.sleep(0.1)
            
        if not self.stream_sid:
            logger.error(f"[CALL {self.call_id}] Timeout: stream_sid never received. Greeting aborted.")
            return

        logger.info(f"[CALL {self.call_id}] Preparing initial greeting...")
        await asyncio.sleep(1.0) # Nice aesthetic pause
        
        try:
            greeting_text = await self.llm_service.generate_greeting()
            logger.info(f"[CALL {self.call_id}] Sending greeting: {greeting_text}")
            logger.info(f"--- [CALL {self.call_id}] Greeting text: {greeting_text} ---")
            sys.stdout.flush()
            
            self.conversation_history.append({"role": "assistant", "content": greeting_text})
            self.dashboard_transcript.append({
                "speaker": "ai",
                "text": greeting_text,
                "timestamp": datetime.now(self.IST).strftime('%Y-%m-%dT%H:%M:%S+05:30')
            })
            await self._sync_to_db()
            logger.info(f"[CALL {self.call_id}] --- CALLING SPEAK FOR GREETING ---")
            await self.speak(greeting_text)
            logger.info(f"[CALL {self.call_id}] --- SPEAK FOR GREETING FINISHED ---")
        except Exception as e:
            logger.error(f"[CALL {self.call_id}] Failed to send greeting: {e}")
            print(f"--- ERROR: Failed to send greeting: {e} ---")
            sys.stdout.flush()

    async def process_media(self, payload: str):
        """Process incoming media (base64 mu-law audio)."""
        try:
            # 1. Decode mu-law to PCM 16-bit (8000Hz)
            mulaw_data = base64.b64decode(payload)
            pcm_8k = AudioService.decode_mulaw(mulaw_data)
            
            if not pcm_8k:
                return

            # 2. Resample 8000Hz to 16000Hz for Silero VAD
            pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)

            # HEARTBEAT: Print a character for every packet to verify reception
            # This is extremely useful to see if data is actually arriving
            sys.stdout.write("·") 
            sys.stdout.flush()

            self.incoming_buffer.extend(pcm_16k)
            
            frame_size = self.vad_service.frame_size
            while len(self.incoming_buffer) >= frame_size:
                frame = bytes(self.incoming_buffer[:frame_size])
                self.incoming_buffer = self.incoming_buffer[frame_size:]
                
                is_speech = self.vad_service.is_speech(frame)
                rms = audioop.rms(frame, 2)
                
                # Low-volume diagnostic (only if not already speaking)
                if rms > 50 and not self.speech_detected:
                    sys.stdout.write(f"<{rms}>")
                    sys.stdout.flush()

                # Require BOTH VAD AND RMS to be active
                is_active = is_speech and rms > self.ENERGY_THRESHOLD

                # GRACE PERIOD: Ignore low-moderate noise in the first 1.5s to protect greeting
                if is_active and (time.time() - self.start_time_unix) < 1.5 and rms < 700:
                    is_active = False 

                if is_active:
                    # BARGE-IN: If AI is speaking and we detect speech, interrupt it
                    if self.processing_lock.locked() and not self.interrupt_flag:
                        if not self.speech_detected:
                            logger.info(f"--- [CALL {self.call_id}] BARGE-IN: Interrupting AI (RMS: {rms}) ---")
                            sys.stdout.flush()
                            self.interrupt_flag = True
                    
                    if not self.speech_detected:
                        self.speech_detected = True
                        logger.info(f"--- [CALL {self.call_id}] USER SPEECH STARTED (RMS: {rms}) ---")
                        logger.info(f"[CALL {self.call_id}] Speech/Activity detected")
                    
                    self.speech_frames += 1
                    self.silence_frames = 0
                    self.pcm_buffer.extend(frame)
                    
                    # Force response if user speaks for more than 2-3 seconds
                    if self.speech_frames >= self.MAX_SPEECH_FRAMES:
                        logger.info(f"[CALL {self.call_id}] 2-3s Limit reached - Triggering response")
                        asyncio.create_task(self.transcribe_and_respond())
                        self.reset_buffer()
                        break
                else:
                    if self.speech_detected:
                        self.silence_frames += 1
                        self.pcm_buffer.extend(frame)
                        
                        if self.silence_frames % 2 == 0:
                             logger.info(f"--- [CALL {self.call_id}] User silent: {self.silence_frames}/{self.SILENCE_THRESHOLD} (Buffer: {len(self.pcm_buffer)} bytes) ---")
                        
                        if self.silence_frames >= self.SILENCE_THRESHOLD:
                            # End of speech detected (or long enough pause)
                            logger.info(f"[CALL {self.call_id}] Pause detected - Triggering response")
                            asyncio.create_task(self.transcribe_and_respond())
                            self.reset_buffer()
                            break
                            
        except Exception as e:
            logger.error(f"Error processing media: {e}")

    def reset_buffer(self):
        # Keep incoming_buffer, only reset detection-specific state
        # DO NOT clear pcm_buffer here as it is captured by transcribe_and_respond
        self.speech_detected = False
        self.silence_frames = 0
        self.speech_frames = 0

    async def transcribe_and_respond(self):
        """Send buffered audio to STT and process valid text."""
        # Wait for the lock instead of giving up, ensuring we don't lose the trigger
        async with self.processing_lock:
            self.interrupt_flag = False 
            
            # Capture buffer at the MOMENT we get the lock
            audio_data = bytes(self.pcm_buffer)
            self.pcm_buffer = bytearray() # Clear it here so new speech doesn't mix with old
            
            if not audio_data:
                logger.info(f"--- [CALL {self.call_id}] EMPTY BUFFER - Ignoring ---")
                return

            logger.info(f"--- [CALL {self.call_id}] TRANSCRIBING {len(audio_data)} bytes ({len(audio_data)//2} samples) ---")
            sys.stdout.flush()
            # 1. STT (Faster Whisper)
            transcript = await AudioService.transcribe_audio(audio_data)
            
            if not transcript:
                 logger.info(f"--- [CALL {self.call_id}] STT returned nothing for {len(audio_data)} bytes ---")
                 return

            logger.info(f"[CALL {self.call_id}] Transcribed user speech: {transcript}")
            
            # 2. Garbage/Hallucination Filter
            if self._is_garbage_transcript(transcript):
                logger.info(f"--- [CALL {self.call_id}] GARBAGE FILTERED: {transcript} ---")
                return

            # Check for minimum audio duration
            duration = len(audio_data) / 32000.0 # 16k samples * 2 bytes
            if duration < self.MIN_SPEECH_DURATION:
                logger.info(f"--- [CALL {self.call_id}] AUDIO TOO SHORT ({duration:.2f}s) - Ignoring ---")
                return

            # Proceed if valid
            await self.handle_user_input(transcript)

    def _is_garbage_transcript(self, text: str) -> bool:
        """Filter out common Whisper hallucinations in silent/noisy environments."""
        hallucinations = [
            "thank you.", "thanks for watching.", "bye bye.", "you.",
            "subtitles by", "watching!", "please subscribe", "thank you very much."
        ]
        text_clean = text.lower().strip()
        if not text_clean or len(text_clean) <= 2:
            return True
        if text_clean in hallucinations:
            return True
        return False

    async def handle_user_input(self, text: str):
        """Handle recognized user text."""
        self.conversation_history.append({"role": "user", "content": text})
        
        timestamp_iso = datetime.now(self.IST).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        self.dashboard_transcript.append({
            "speaker": "user",
            "text": text,
            "timestamp": timestamp_iso
        })
        logger.info(f"[CALL {self.call_id}] User message: {text}")
        await self._sync_to_db()
        
        # 1. RAG Search (Qdrant)
        rag_context = await self.qdrant_service.search(text)
        
        # 2. LLM (OpenAI with RAG)
        response_text, intent, _ = await self.llm_service.process_input(text, self.conversation_history, rag_context)
        
        # Update intent and transcript in database
        self.conversation_history.append({"role": "assistant", "content": response_text})
        self.dashboard_transcript.append({
            "speaker": "ai",
            "text": response_text,
            "timestamp": datetime.now(self.IST).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        })
        
        if intent:
            logger.info(f"[CALL {self.call_id}] Intent detected: {intent}")
        
        await self._sync_to_db(intent=intent)
        logger.info(f"[CALL {self.call_id}] AI response: {response_text}")
        
        # 3. TTS & Playback
        await self.speak(response_text)

    async def _sync_to_db(self, intent=None):
        """Sync current transcript and intent to Supabase."""
        if not self.call_id:
            return
            
        try:
            # Explicitly serialize to ensure JSON safety
            transcript_json = json.loads(json.dumps(self.dashboard_transcript, default=str))
            
            update_data = {
                "transcript": transcript_json
            }
            if intent:
                update_data["intent"] = intent
                
            try:
                logger.info(f"[CALL {self.call_id}] Syncing transcript ({len(transcript_json)} items)...")
                response = supabase.table("calls").update(update_data).eq("call_id", self.call_id).execute()
                if not response.data:
                    logger.warning(f"[CALL {self.call_id}] Sync returned no data - row might not exist yet.")
                else:
                    logger.info(f"[CALL {self.call_id}] Sync successful")
            except Exception as e:
                logger.error(f"Real-time sync failed: {str(e)[:200]}")
        except Exception as e:
            logger.error(f"[CALL {self.call_id}] Failed to prepare sync data: {e}")

    async def speak(self, text: str):
        """Generate audio, convert to mu-law, and send to Twilio in chunks."""
        logger.info(f"[CALL {self.call_id}] Generating TTS audio: {text[:50]}...")
        logger.info(f"--- [CALL {self.call_id}] SPEAKING: {text[:50]}... ---")
        sys.stdout.flush()
        
        # Validate stream_sid is set
        if not self.stream_sid:
            logger.error(f"[CALL {self.call_id}] Cannot speak: stream_sid not set yet.")
            print(f"--- ERROR: Cannot speak - stream_sid not set ---")
            sys.stdout.flush()
            return
        
        try:
            # Generate TTS audio
            raw_pcm = await AudioService.generate_speech(text)
            
            if not raw_pcm:
                logger.error(f"[CALL {self.call_id}] TTS generation returned empty audio")
                print(f"--- ERROR: TTS generation failed - empty audio ---")
                sys.stdout.flush()
                return
            
            print(f"--- [CALL {self.call_id}] TTS generated {len(raw_pcm)} bytes of PCM ---")
            sys.stdout.flush()
            
            # Convert to mu-law for Twilio
            mulaw_audio = AudioService.pcm_to_mulaw8k(raw_pcm)
            
            if not mulaw_audio:
                logger.error(f"[CALL {self.call_id}] Audio conversion to mu-law failed")
                print(f"--- ERROR: Audio conversion to mu-law failed ---")
                sys.stdout.flush()
                return
            
            print(f"--- [CALL {self.call_id}] Converted to {len(mulaw_audio)} bytes of mu-law ---")
            sys.stdout.flush()
            
            # Send audio in chunks to avoid overwhelming the stream
            chunk_size = 160  # 20ms of audio at 8kHz
            chunks_sent = 0
            for i in range(0, len(mulaw_audio), chunk_size):
                chunk = mulaw_audio[i:i + chunk_size]
                payload = base64.b64encode(chunk).decode("utf-8")
                
                response_msg = {
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {
                        "payload": payload
                    }
                }
                if self.interrupt_flag:
                    logger.info(f"[CALL {self.call_id}] speak interrupted")
                    print(f"--- [CALL {self.call_id}] INTERRUPTED ---")
                    sys.stdout.flush()
                    break
                    
                await self.websocket.send_text(json.dumps(response_msg))
                await asyncio.sleep(0.02)  # 20ms delay between chunks
                chunks_sent += 1
                
            logger.info(f"[CALL {self.call_id}] TTS audio sent ({len(mulaw_audio)} bytes, {chunks_sent} chunks)")
            print(f"--- [CALL {self.call_id}] FINISHED SPEAKING ({len(mulaw_audio)} bytes, {chunks_sent} chunks) ---")
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"[CALL {self.call_id}] Error in speak(): {e}")
            print(f"--- ERROR in speak(): {e} ---")
            sys.stdout.flush()
            import traceback
            traceback.print_exc()

    async def handle_disconnect(self):
        """Clean up call on disconnect."""
        if self.call_id:
            end_time = datetime.now(self.IST)
            duration = int((end_time - (self.start_timestamp or end_time)).total_seconds())
            
            start_time_iso = (self.start_timestamp or end_time).strftime('%Y-%m-%dT%H:%M:%S+05:30')
            end_time_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
            
            summary = await self.llm_service.generate_summary(self.conversation_history)
            
            try:
                # 1. Update calls table (status and duration)
                # Ensure JSON serializable
                ts_json = json.loads(json.dumps(self.dashboard_transcript, default=str))
                
                update_data = {
                    "start_time": start_time_iso,
                    "end_time": end_time_iso,
                    "call_duration": int(duration),
                    "call_status": "completed",
                    "transcript": ts_json,
                    "summary": summary
                }
                
                logger.info(f"[CALL {self.call_id}] Final update data prepared. Attempting database update...")
                
                try:
                    response = supabase.table("calls").update(update_data).eq("call_id", self.call_id).execute()
                    if response.data:
                        logger.info(f"[CALL {self.call_id}] Calls table updated successfully: {response.data}")
                    else:
                        logger.warning(f"[CALL {self.call_id}] Final update returned no data. Record missing?")
                        # Last ditch: try to at least close the call even with minimal data
                        supabase.table("calls").update({"call_status": "completed"}).eq("call_id", self.call_id).execute()
                except Exception as e:
                    logger.error(f"Failed to update calls table on disconnect: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Try minimal update if full update failed
                    try:
                        supabase.table("calls").update({
                            "call_status": "completed", 
                            "summary": summary,
                            "end_time": end_time_iso,
                            "call_duration": int(duration)
                        }).eq("call_id", self.call_id).execute()
                    except:
                        pass

                # 2. Insert into call_summaries table
                if summary:
                    try:
                        summary_data = {
                            "call_id": self.call_id,
                            "summary_text": summary,
                            "created_at": end_time_iso
                        }
                        supabase.table("call_summaries").insert(summary_data).execute()
                        logger.info(f"[CALL {self.call_id}] Summary saved to call_summaries")
                    except Exception as e:
                        logger.error(f"Failed to save summary to call_summaries: {e}")
                
                logger.info(f"[CALL {self.call_id}] CALL ENDED - Duration: {duration}s")
            except Exception as e:
                logger.error(f"[CALL {self.call_id}] Failed during disconnect cleanup execution: {e}")
                import traceback
                logger.error(traceback.format_exc())
