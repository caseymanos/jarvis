"""
Speech-to-Text service using OpenAI Whisper API.
Handles real-time audio transcription for voice sessions.
"""
import io
import logging
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Service for transcribing audio using OpenAI Whisper."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Speech-to-Text service.

        Args:
            api_key: OpenAI API key (optional, reads from settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = settings.STT_MODEL
        self.language = settings.STT_LANGUAGE
        logger.info(f"Initialized SpeechToTextService with model: {self.model}")

    async def transcribe_audio(
        self,
        audio_data: bytes,
        session_id: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes (PCM format expected from frontend)
            session_id: Session ID for logging and tracking
            language: Optional language code (e.g., 'en', 'es')
            prompt: Optional context/prompt to guide transcription

        Returns:
            dict with:
                - text: Transcribed text
                - language: Detected language
                - duration: Audio duration in seconds
                - segments: List of timestamped segments (if available)
        """
        try:
            # Convert raw PCM audio to WAV format for Whisper
            audio_file = io.BytesIO()
            audio_file.name = "audio.wav"

            # Write WAV header for 16kHz mono PCM
            audio_file.write(self._create_wav_header(len(audio_data), 16000, 1))
            audio_file.write(audio_data)
            audio_file.seek(0)

            logger.info(f"Transcribing audio for session {session_id}: {len(audio_data)} bytes")

            # Call Whisper API
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=language or self.language,
                prompt=prompt,
                response_format="verbose_json",  # Get detailed response with timestamps
                temperature=0.0  # Deterministic transcription
            )

            result = {
                "text": response.text,
                "language": response.language,
                "duration": response.duration if hasattr(response, 'duration') else None,
                "segments": []
            }

            # Extract segments if available
            if hasattr(response, 'segments') and response.segments:
                result["segments"] = [
                    {
                        "id": seg.id,
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text
                    }
                    for seg in response.segments
                ]

            logger.info(f"Transcription complete for session {session_id}: '{response.text[:100]}...'")
            return result

        except Exception as e:
            logger.error(f"Error transcribing audio for session {session_id}: {str(e)}")
            raise

    def _create_wav_header(self, data_size: int, sample_rate: int, channels: int) -> bytes:
        """
        Create WAV file header for PCM audio data.

        Args:
            data_size: Size of audio data in bytes
            sample_rate: Sample rate (e.g., 16000)
            channels: Number of channels (1 for mono, 2 for stereo)

        Returns:
            WAV header bytes
        """
        byte_rate = sample_rate * channels * 2  # 16-bit PCM = 2 bytes per sample
        block_align = channels * 2

        header = bytearray()
        # RIFF header
        header.extend(b'RIFF')
        header.extend((data_size + 36).to_bytes(4, 'little'))
        header.extend(b'WAVE')

        # fmt chunk
        header.extend(b'fmt ')
        header.extend((16).to_bytes(4, 'little'))  # Chunk size
        header.extend((1).to_bytes(2, 'little'))   # Audio format (1 = PCM)
        header.extend(channels.to_bytes(2, 'little'))
        header.extend(sample_rate.to_bytes(4, 'little'))
        header.extend(byte_rate.to_bytes(4, 'little'))
        header.extend(block_align.to_bytes(2, 'little'))
        header.extend((16).to_bytes(2, 'little'))  # Bits per sample

        # data chunk
        header.extend(b'data')
        header.extend(data_size.to_bytes(4, 'little'))

        return bytes(header)

    async def close(self):
        """Clean up resources."""
        await self.client.close()
        logger.info("SpeechToTextService closed")


# Singleton instance
_stt_service: Optional[SpeechToTextService] = None


def get_stt_service() -> SpeechToTextService:
    """Get or create the Speech-to-Text service singleton."""
    global _stt_service
    if _stt_service is None:
        _stt_service = SpeechToTextService()
    return _stt_service


async def shutdown_stt_service():
    """Shutdown the Speech-to-Text service."""
    global _stt_service
    if _stt_service:
        await _stt_service.close()
        _stt_service = None
