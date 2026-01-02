import asyncio
import os
import sys

# Add the project root to sys.path to allow imports from 'app'
sys.path.append(os.getcwd())

from app.services.audio_service import AudioService
from app.services.llm_service import LLMService
from app.services.qdrant_service import QdrantService
from dotenv import load_dotenv

load_dotenv()

async def verify_tts():
    print("\n--- Verifying TTS Fix ---")
    text = "Hello, this is a test of the VocalQ AI greeting message."
    try:
        from app.services.audio_service import AudioService
        audio_content = await AudioService.generate_speech(text)
        if audio_content and len(audio_content) > 0:
            print(f"SUCCESS: Generated {len(audio_content)} bytes of audio.")
        else:
            print("FAILURE: Generated empty audio.")
    except Exception as e:
        print(f"FAILURE: Exception during TTS: {e}")

async def verify_summary_logic():
    print("\n--- Verifying Summary Logic ---")
    llm = LLMService()
    
    # 1. Test short history
    short_history = [{"role": "assistant", "content": "Hello, how can I help?"}]
    summary = await llm.generate_summary(short_history)
    print(f"Short history summary: {summary}")
    
    # 2. Test normal history
    normal_history = [
        {"role": "assistant", "content": "Hello, how can I help?"},
        {"role": "user", "content": "What is VocalQ?"},
        {"role": "assistant", "content": "VocalQ is an AI voice platform."}
    ]
    summary = await llm.generate_summary(normal_history)
    print(f"Normal history summary: {summary}")

async def verify_supabase_write():
    print("\n--- Verifying Supabase Write (with Fallbacks) ---")
    from app.core.supabase_client import supabase
    import uuid
    from datetime import datetime
    
    test_id = str(uuid.uuid4())
    full_data = {
        "call_id": test_id,
        "caller_number": "verify_test",
        "start_time": datetime.utcnow().isoformat(),
        "call_status": "active"
    }
    
    try:
        # 1. Try full insert
        try:
            supabase.table("calls").insert(full_data).execute()
            print(f"SUCCESS: Full insert for {test_id}")
        except Exception as e:
            print(f"Full insert failed (likely PGRST204): {str(e)[:100]}")
            # 2. Try minimal insert
            try:
                minimal = {"call_id": test_id, "call_status": "active"}
                supabase.table("calls").insert(minimal).execute()
                print(f"SUCCESS: Minimal insert for {test_id}")
            except Exception as e2:
                print(f"Minimal insert failed: {str(e2)[:100]}")
                # 3. Try ULTRA-MINIMAL
                ultra = {"call_id": test_id}
                supabase.table("calls").insert(ultra).execute()
                print(f"SUCCESS: Ultra-minimal insert for {test_id}")
        
        # Cleanup
        supabase.table("calls").delete().eq("call_id", test_id).execute()
        print("SUCCESS: Cleaned up test record")
    except Exception as e:
        print(f"FAILURE: All Supabase attempts failed: {e}")

async def main():
    await verify_tts()
    await verify_summary_logic()
    await verify_supabase_write()

if __name__ == "__main__":
    asyncio.run(main())
