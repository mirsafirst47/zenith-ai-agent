"""Mock Speech services for development"""

class MockSpeechService:
    async def transcribe_audio(self, audio_data: bytes, language: str = None) -> str:
        """Mock transcription"""
        return "I would like to make a reservation for tomorrow at 7 PM"
    
    async def synthesize_speech(self, text: str, language: str = "en") -> bytes:
        """Mock TTS - returns empty bytes"""
        return b"mock_audio_data"

mock_speech_service = MockSpeechService()
