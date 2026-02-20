"""
Quick script to create the payload index on existing Qdrant collection
"""
import asyncio
from app.services.qdrant_service import QdrantService
from qdrant_client.http import models

async def create_index():
    service = QdrantService()
    
    try:
        print("Creating payload index for metadata.doc_id...")
        await service.client.create_payload_index(
            collection_name=service.collection_name,
            field_name="metadata.doc_id",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        print("✅ Index created successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        if "already exists" in str(e).lower():
            print("Index already exists - this is fine!")

if __name__ == "__main__":
    asyncio.run(create_index())
