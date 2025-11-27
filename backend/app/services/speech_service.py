"""Real Speech Services - Whisper (STT) and ElevenLabs (TTS)"""
from app.config import settings
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

class SpeechService:
    def __init__(self):
        # Initialize Whisper (OpenAI)
        if WHISPER_AVAILABLE and settings.USE_REAL_OPENAI:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ Whisper STT initialized")
        else:
            self.openai_client = None
            logger.info("📝 Using mock STT")
        
        # Initialize ElevenLabs
        if ELEVENLABS_AVAILABLE and settings.USE_REAL_ELEVENLABS:
            self.elevenlabs_client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
            self.voice_id = settings.ELEVENLABS_VOICE_ID
            logger.info("✅ ElevenLabs TTS initialized")
        else:
            self.elevenlabs_client = None
            logger.info("📝 Using mock TTS")
    
    async def transcribe_audio(self, audio_data: bytes, language: str = None) -> str:
        """Convert speech to text using Whisper"""
        if not self.openai_client:
            # Mock transcription
            return "This is a mock transcription. Enable USE_REAL_OPENAI to use Whisper."
        
        try:
            audio_file = BytesIO(audio_data)
            audio_file.name = "audio.wav"
            
            transcript = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language if language else None
            )
            
            return transcript.text
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return "Error transcribing audio"
    
    async def synthesize_speech(
        self, 
        text: str, 
        language: str = "en",
        voice_settings: dict = None
    ) -> bytes:
        """Convert text to speech using ElevenLabs"""
        if not self.elevenlabs_client:
            # Mock TTS
            return b"mock_audio_data"
        
        try:
            # Language-specific voice adjustments
            stability = voice_settings.get("stability", 0.5) if voice_settings else 0.5
            similarity = voice_settings.get("similarity", 0.75) if voice_settings else 0.75
            
            audio = self.elevenlabs_client.generate(
                text=text,
                voice=self.voice_id,
                voice_settings=VoiceSettings(
                    stability=stability,
                    similarity_boost=similarity,
                    style=0.0,
                    use_speaker_boost=True
                ),
                model="eleven_multilingual_v2"
            )
            
            # Convert generator to bytes
            audio_bytes = b"".join(audio)
            return audio_bytes
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            return b"error_audio_data"

speech_service = SpeechService()
