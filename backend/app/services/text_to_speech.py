"""
Text-to-Speech service for converting text responses to audio.
Supports multiple TTS providers: OpenAI TTS, ElevenLabs.
"""
import logging
from typing import Optional, AsyncIterator
from openai import AsyncOpenAI
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """Service for converting text to speech using various TTS providers."""

    def __init__(self):
        """Initialize the TTS service with configured provider."""
        settings = get_settings()
        self.provider = settings.TTS_PROVIDER
        self.model = settings.TTS_MODEL
        self.voice = settings.TTS_VOICE

        # Initialize the appropriate client
        if self.provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "elevenlabs":
            self.api_key = settings.ELEVENLABS_API_KEY
            self.base_url = "https://api.elevenlabs.io/v1"
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

        logger.info(f"Initialized TextToSpeechService with provider: {self.provider}, voice: {self.voice}")

    async def synthesize_speech(
        self,
        text: str,
        session_id: str,
        stream: bool = True
    ) -> AsyncIterator[bytes]:
        """
        Convert text to speech and return audio stream.

        Args:
            text: Text to convert to speech
            session_id: Session ID for logging
            stream: Whether to stream audio chunks (default: True)

        Yields:
            Audio chunks as bytes (for streaming)

        Returns:
            Complete audio data as bytes (if not streaming)
        """
        try:
            if self.provider == "openai":
                logger.info(f"Synthesizing speech for session {session_id} using OpenAI TTS: '{text[:50]}...'")

                # OpenAI TTS streaming
                response = await self.client.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    response_format="pcm",  # Raw PCM for WebSocket streaming
                    speed=1.0
                )

                # Stream audio chunks
                if stream:
                    async for chunk in response.iter_bytes(chunk_size=4096):
                        if chunk:
                            yield chunk
                else:
                    # Return all audio data at once
                    audio_data = b""
                    async for chunk in response.iter_bytes():
                        audio_data += chunk
                    yield audio_data

            elif self.provider == "elevenlabs":
                logger.info(f"Synthesizing speech for session {session_id} using ElevenLabs: '{text[:50]}...'")

                # ElevenLabs TTS streaming
                url = f"{self.base_url}/text-to-speech/{self.voice}/stream"
                headers = {
                    "Accept": "audio/mpeg",
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
                data = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }

                async with httpx.AsyncClient() as client:
                    async with client.stream("POST", url, headers=headers, json=data, timeout=30.0) as response:
                        response.raise_for_status()

                        if stream:
                            async for chunk in response.aiter_bytes(chunk_size=4096):
                                if chunk:
                                    yield chunk
                        else:
                            audio_data = await response.aread()
                            yield audio_data

            logger.info(f"Speech synthesis complete for session {session_id}")

        except Exception as e:
            logger.error(f"Error synthesizing speech for session {session_id}: {str(e)}")
            raise

    async def close(self):
        """Clean up resources."""
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            await self.client.close()
        logger.info("TextToSpeechService closed")


# Singleton instance
_tts_service: Optional[TextToSpeechService] = None


def get_tts_service() -> TextToSpeechService:
    """Get or create the TTS service singleton."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TextToSpeechService()
    return _tts_service


async def shutdown_tts_service():
    """Shutdown the TTS service."""
    global _tts_service
    if _tts_service:
        await _tts_service.close()
        _tts_service = None
