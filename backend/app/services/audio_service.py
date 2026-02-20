import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global OpenAI client instance
_openai_client = None

def get_openai_client():
    """Get or create async OpenAI client."""
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


class AudioService:
    """Audio service using OpenAI APIs for embeddings."""

    @staticmethod
    async def get_openai_embedding(text: str) -> list:
        """
        Generate embeddings using OpenAI text-embedding-3-small (1536 dims).
        Used for RAG/knowledge base semantic search.
        """
        try:
            client = get_openai_client()
            response = await client.embeddings.create(
                input=text,
                model=settings.EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI Embedding failed: {e}")
            return []
