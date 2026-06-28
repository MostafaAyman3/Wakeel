import io
import httpx
from openai import AsyncOpenAI
import structlog

from backend.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class SpeechService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.elevenlabs_api_key = settings.elevenlabs_api_key
        # Default voice ID (Adam) or any other. Can be overridden.
        self.elevenlabs_voice_id = "pNInz6obpgDQGcFmaJgB"
        
    async def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Convert speech audio bytes to text using OpenAI Whisper API.
        """
        try:
            logger.info("Transcribing audio", filename=filename, size=len(audio_bytes))
            # OpenAI requires a file-like object with a name attribute.
            file_obj = io.BytesIO(audio_bytes)
            file_obj.name = filename
            
            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=file_obj,
                response_format="text"
            )
            
            text = response.strip()
            logger.info("Audio transcribed successfully", text_length=len(text))
            return text
        except Exception as e:
            logger.error("Error in speech_to_text", error=str(e))
            raise e

    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech audio bytes using ElevenLabs API.
        Falls back to OpenAI TTS if ElevenLabs key is missing.
        """
        if not self.elevenlabs_api_key:
            logger.warning("ElevenLabs API key missing. Falling back to OpenAI TTS.")
            return await self._openai_tts(text)
            
        try:
            logger.info("Generating speech via ElevenLabs", text_length=len(text))
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            # Using elevelabs_v2 model for better multi-lingual including Arabic
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers, timeout=30.0)
                response.raise_for_status()
                audio_bytes = response.content
                
            logger.info("Speech generated successfully via ElevenLabs", audio_size=len(audio_bytes))
            return audio_bytes
        except Exception as e:
            logger.error("Error in ElevenLabs text_to_speech. Falling back to OpenAI", error=str(e))
            # Fallback to OpenAI if ElevenLabs fails
            return await self._openai_tts(text)

    async def _openai_tts(self, text: str) -> bytes:
        """Fallback TTS using OpenAI."""
        try:
            logger.info("Generating speech via OpenAI TTS", text_length=len(text))
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )
            audio_bytes = response.read()
            return audio_bytes
        except Exception as e:
            logger.error("Error in OpenAI TTS", error=str(e))
            raise e

speech_service = SpeechService()
