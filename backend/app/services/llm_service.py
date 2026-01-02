import asyncio
import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class LLMService:
    _greeting = "Hello, thank you for calling VocalQ.ai support. How can I help you today?"

    @classmethod
    def get_greeting(cls):
        return cls._greeting
                                                 
                                                 
    @classmethod
    def set_greeting(cls, text: str):
        cls._greeting = text
        logger.info(f"AI Greeting updated to: {text}")

    async def generate_greeting(self):
        return self._greeting

    async def process_input(self, text: str, history: list, rag_context: list = None):
        """
        Process user input using OpenAI Chat Completion.
        Allows conversational responses even without KB context for natural dialogue.
        """
        try:
            # Check for common conversational phrases that don't need KB
            conversational_phrases = ["thank you", "thanks", "hello", "hi", "hey", "bye", "goodbye"]
            is_simple_phrase = any(phrase in text.lower() for phrase in conversational_phrases)
            
            # Build system prompt that prioritizes KB but allows natural flow
            system_prompt = """You are VocalQ.ai's professional phone assistant.
STRICT RULES:
1. PRIMARY SOURCE: Use ONLY the provided KNOWLEDGE BASE for all technical, service, or business-related questions (like office hours, contact info, price, policies).
2. GREETINGS: For "hello", "hi", "how are you", etc., be polite and professional.
3. KB MISS: If the answer is NOT explicitly in the provided KNOWLEDGE BASE context, say EXACTLY: "I'm sorry, I don't have that information in my knowledge base. Is there anything else I can help you with?"
4. NO DEFAULT HOURS: Do NOT use 9:00 AM to 6:00 PM or any other default office hours. ONLY use hours provided in the KB.
5. CONCISENESS: Keep every response under 10-15 words. This is a phone call.
6. NO HALLUCINATIONS: Do not make up facts about VocalQ.ai. If not in the KB, use the fallback message.
7. LANGUAGE: Respond ONLY in English.
8. URGENCY: If the user indicates an emergency, stay calm and professional. """

            messages = [{"role": "system", "content": system_prompt}]
            
            if rag_context and any(rag_context):
                context_str = "\n".join(rag_context)
                messages[0]["content"] += f"\n\nKNOWLEDGE BASE CONTEXT:\n{context_str}"

            # Add conversation history (last 5 turns)
            for entry in history[-5:]:
                messages.append(entry)
            
            # Add current user input if not already in history
            if not history or history[-1]["content"] != text:
                messages.append({"role": "user", "content": text})

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=100,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            intent = "support"
            
            logger.info(f"LLM Response: {response_text[:100]}")
            return response_text, intent, False
            
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            return "I apologize, I'm having a technical issue. Could you repeat that?", "error", False

    async def generate_summary(self, history: list):
        if not history or len(history) <= 1:
            return "Call ended after initial greeting."
        
        try:
            messages = [
                {"role": "system", "content": "Summarize the following conversation in one or two sentences. If it was just a greeting and a 'thank you', say 'Short greeting call.'"},
                {"role": "user", "content": str(history)}
            ]
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            summary = response.choices[0].message.content
            logger.info(f"Call summary generated: {summary}")
            return summary
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "Conversation summary unavailable."
