import io
import logging
import base64
import wave
import torch
import audioop
import numpy as np
import sys
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global model instances
_whisper_model = None
_embedding_model = None
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        print(f"--- Loading Faster Whisper model: {settings.WHISPER_MODEL} ---")
        sys.stdout.flush()
        _whisper_model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
        print("--- Faster Whisper Loaded OK ---")
        sys.stdout.flush()
    return _whisper_model

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print("--- Loading Sentence Transformer model ---")
        sys.stdout.flush()
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("--- Sentence Transformer Loaded OK ---")
            sys.stdout.flush()
        except Exception as e:
            print(f"--- Sentence Transformer Load FAILED: {e} ---")
            sys.stdout.flush()
            logger.error(f"Failed to load sentence-transformers: {e}")
    return _embedding_model

class VADService:
    def __init__(self, aggressiveness=3):
        self._model = None
        self.sample_rate = 16000
        # Silero VAD v4+ requires 512, 1024, or 1536 samples for 16000Hz
        self.frame_size = 512 * 2 # 512 samples * 2 bytes/sample (int16)

    async def initialize(self):
        """Pre-load the VAD model asynchronously."""
        if self._model is not None:
            return
        
        try:
            print("--- Pre-loading Silero VAD model ---")
            sys.stdout.flush()
            # Run the blocking torch load in a thread
            def _load():
                model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                            model='silero_vad',
                                            trust_repo=True)
                return model
            
            self._model = await asyncio.to_thread(_load)
            print("--- Silero VAD Loaded OK ---")
            sys.stdout.flush()
        except Exception as e:
            print(f"--- Silero VAD Load FAILED (will use energy fallback): {e} ---")
            sys.stdout.flush()
            self._model = "FAILED"

    def is_speech(self, pcm_data: bytes) -> bool:
        """
        Detect speech. Fallback to energy if model isn't loaded.
        """
        rms = audioop.rms(pcm_data, 2)
        
        # If model isn't ready, just use energy (very fast)
        if self._model is None or self._model == "FAILED":
             return rms > 150 

        try:
            # Convert PCM bytes to float32 tensor
            audio_int16 = np.frombuffer(pcm_data, dtype=np.int16)
            audio_float32 = torch.from_numpy(audio_int16.astype(np.float32) / 32768.0)
            
            # Simple inference
            speech_prob = self._model(audio_float32, self.sample_rate).item()
            return speech_prob > 0.5
        except Exception as e:
            # Fallback on inference error
            return rms > 150

class AudioService:
    @staticmethod
    async def transcribe_audio(audio_data: bytes) -> str:
        """
        Transcribe audio bytes using Faster Whisper in a background thread.
        """
        try:
            # Convert bytes to numpy float32 array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Run blocking Whisper call in a thread
            def _transcribe():
                # Force language to English to prevent mis-detection of noise as other languages
                segments, info = get_whisper_model().transcribe(
                    audio_array, 
                    beam_size=5,
                    language="en"
                )
                return " ".join([segment.text for segment in segments])
            
            transcript = await asyncio.to_thread(_transcribe)
            return transcript.strip()
        except Exception as e:
            logger.error(f"Faster Whisper Transcription failed: {e}")
            return ""

    @staticmethod
    async def generate_speech(text: str) -> bytes:
        """
        Generate raw PCM 16-bit 24kHz audio from text using OpenAI TTS (Async).
        """
        try:
            print(f"--- Generating TTS (Async) for: {text[:50]}... ---")
            sys.stdout.flush()
            
            if not text or not text.strip():
                logger.error("TTS: Empty text provided") # Kept this line as it's good practice, though diff removed print
                return b""
            
            response = await get_openai_client().audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="pcm"
            )
            
            # In OpenAI v1.0+, response from audio.speech.create is an HttpxBinaryResponseContent
            # which already contains the full content in .content.
            # Using .content is more reliable than awaiting .read() in some versions.
            if hasattr(response, 'content'):
                audio_content = response.content
            else:
                # Fallback for other versions or streaming responses
                audio_content = await response.read()
            
            if not audio_content:
                logger.error("TTS: OpenAI returned empty audio content")
                return b""
            
            logger.info(f"--- TTS Success: Generated {len(audio_content)} bytes ---")
            return audio_content
            
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            print(f"--- ERROR: TTS failed: {e} ---") # Kept this line as it's good practice, though diff removed print
            sys.stdout.flush()
            # import traceback # Removed as per diff
            # traceback.print_exc() # Removed as per diff
            return b""

    @staticmethod
    def pcm_to_mulaw8k(pcm_data: bytes, input_rate: int = 24000) -> bytes:
        """
        Resample PCM from input_rate to 8000Hz and encode to mu-law.
        """
        if not pcm_data:
            return b""
        
        try:
            # 1. Resample from 24kHz (OpenAI) to 8kHz (Twilio)
            # audioop.ratecv(fragment, width, nchannels, inrate, outrate, state)
            resampled_pcm, _ = audioop.ratecv(pcm_data, 2, 1, input_rate, 8000, None)
            
            # 2. Convert to mu-law
            mulaw_data = audioop.lin2ulaw(resampled_pcm, 2)
            
            return mulaw_data
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            return b""

    @staticmethod
    def get_embedding(text: str) -> list:
        """
        Generate embeddings for a given text.
        By default uses local Sentence Transformer (384 dims).
        """
        try:
            model = get_embedding_model()
            if model is None:
                return []
            embedding = model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    @staticmethod
    async def get_openai_embedding(text: str) -> list:
        """
        Generate embeddings using OpenAI (1536 dims) asynchronously.
        """
        try:
            client = get_openai_client()
            response = await client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI Embedding failed: {e}")
            return []

    @staticmethod
    def decode_mulaw(mulaw_data: bytes) -> bytes:
        """
        Decode Twilio G.711 mu-law to PCM 16-bit.
        """
        return audioop.ulaw2lin(mulaw_data, 2)

    @staticmethod
    def encode_mulaw(pcm_data: bytes) -> bytes:
        """
        Encode PCM 16-bit back to mu-law for Twilio.
        """
        return audioop.lin2ulaw(pcm_data, 2)
