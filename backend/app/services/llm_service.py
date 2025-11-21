"""
Language Model service for generating contextual responses.
Supports multiple LLM providers: Grok (xAI), GPT (OpenAI), Claude (Anthropic).
"""
import logging
from typing import Optional, List
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for generating responses using various LLM providers."""

    def __init__(self):
        """Initialize the LLM service with configured provider."""
        settings = get_settings()
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

        # Initialize the appropriate client
        if self.provider == "xai":
            self.client = AsyncOpenAI(
                api_key=settings.XAI_API_KEY,
                base_url="https://api.x.ai/v1"
            )
        elif self.provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "openrouter":
            self.client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
        elif self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        logger.info(f"Initialized LLMService with provider: {self.provider}, model: {self.model}")

    async def generate_response(
        self,
        user_query: str,
        retrieved_context: str,
        session_id: str,
        conversation_history: Optional[List[dict]] = None
    ) -> dict:
        """
        Generate a contextual response using the LLM.

        Args:
            user_query: User's transcribed question/query
            retrieved_context: Retrieved document context from RAG
            session_id: Session ID for logging
            conversation_history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]

        Returns:
            dict with:
                - text: Generated response text
                - model: Model used for generation
                - tokens_used: Token count (if available)
        """
        try:
            # Build system prompt for Jarvis
            system_prompt = """You are JARVIS, a tactical AI assistant for frontline military operations.

Your role:
- Provide clear, concise, actionable information to operators in the field
- Use retrieved documents and manuals to answer questions accurately
- Prioritize safety and mission success
- Be direct and professional - avoid unnecessary elaboration
- If information is not in the retrieved context, say so clearly

Guidelines:
- Keep responses under 100 words when possible
- Use military/tactical terminology appropriately
- Cite sources when referencing specific procedures or data
- Flag critical safety information prominently"""

            # Build user message with context
            if retrieved_context:
                user_message = f"""Retrieved Context:
{retrieved_context}

User Query: {user_query}

Instructions: Answer the query using ONLY the information from the retrieved context above. If the context doesn't contain relevant information, state that clearly. Keep your response concise and actionable."""
            else:
                user_message = f"""No relevant documents were found in the knowledge base.

User Query: {user_query}

Instructions: Inform the user that you don't have specific information about their query in your knowledge base. Suggest they verify with official sources or clarify their question."""

            # Generate response based on provider
            if self.provider in ["xai", "openai", "openrouter"]:
                # OpenAI-compatible API (Grok, GPT, and OpenRouter)
                messages = [
                    {"role": "system", "content": system_prompt}
                ]

                # Add conversation history if provided
                if conversation_history:
                    messages.extend(conversation_history[-5:])  # Last 5 exchanges for context

                messages.append({"role": "user", "content": user_message})

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )

                result = {
                    "text": response.choices[0].message.content,
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens if response.usage else None
                }

            elif self.provider == "anthropic":
                # Claude API
                messages = []

                # Add conversation history if provided
                if conversation_history:
                    messages.extend(conversation_history[-5:])

                messages.append({"role": "user", "content": user_message})

                response = await self.client.messages.create(
                    model=self.model,
                    system=system_prompt,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )

                result = {
                    "text": response.content[0].text,
                    "model": self.model,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens if response.usage else None
                }

            logger.info(f"Generated response for session {session_id} using {self.model}: {result['text'][:100]}...")
            return result

        except Exception as e:
            logger.error(f"Error generating LLM response for session {session_id}: {str(e)}")
            raise

    async def close(self):
        """Clean up resources."""
        if hasattr(self.client, 'close'):
            await self.client.close()
        logger.info("LLMService closed")


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def shutdown_llm_service():
    """Shutdown the LLM service."""
    global _llm_service
    if _llm_service:
        await _llm_service.close()
        _llm_service = None
