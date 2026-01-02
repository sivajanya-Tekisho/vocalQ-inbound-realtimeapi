import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from app.services.llm_service import LLMService
from app.services.qdrant_service import QdrantService

async def verify():
    qdrant = QdrantService()
    llm = LLMService()
    
    # Wait for Qdrant to be ready
    await asyncio.sleep(2)
    
    query = "Can I know the short timing?"
    print(f"Query: {query}")
    
    # 1. Search Qdrant
    context = await qdrant.search(query)
    print(f"Context found: {context}")
    
    # 2. Process with LLM
    response, intent, _ = await llm.process_input(query, [], context)
    print(f"LLM Response: {response}")
    
    if "10:00 AM" in response and "8:30 PM" in response:
        print("VERIFICATION SUCCESS: Correct timings returned.")
    elif "9:00 AM" in response:
        print("VERIFICATION FAILED: Still returning incorrect timings.")
    else:
        print("VERIFICATION UNCERTAIN: Check response manually.")

if __name__ == "__main__":
    asyncio.run(verify())
