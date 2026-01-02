
import asyncio
import sys
import os
import httpx
from dotenv import load_dotenv

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.qdrant_service import QdrantService
from app.services.audio_service import AudioService

async def verify_phase2():
    load_dotenv()
    
    print("--- Verifying Phase 2 Implementation ---")
    
    # 1. Check Qdrant Dimensions
    print("Checking Qdrant collection...")
    qdrant = QdrantService()
    info = qdrant.client.get_collection(qdrant.collection_name)
    size = info.config.params.vectors.size
    print(f"Collection: {qdrant.collection_name}, Size: {size}")
    if size != 1536:
        print("ERROR: Dimension mismatch! Expected 1536.")
        return
    else:
        print("SUCCESS: Dim 1536 detected.")

    # 2. Check OpenAI Embedding (Manual Test)
    print("Generating OpenAI embedding...")
    emb = AudioService.get_openai_embedding("Test knowledge base.")
    if len(emb) == 1536:
        print("SUCCESS: OpenAI Embedding generated 1536 dims.")
    else:
        print(f"ERROR: OpenAI Embedding returned {len(emb)} dims.")
        return

    # 3. Check Admin List API
    try:
        print("Checking Admin List API...")
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/admin/knowledge/list")
            if response.status_code == 200:
                print(f"SUCCESS: Admin List API reachable. Docs found: {len(response.json())}")
            else:
                print(f"ERROR: Admin List API returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Admin List API unreachable: {e}")

    print("--- Phase 2 Verification COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(verify_phase2())
