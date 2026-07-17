"""Application configuration"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Zenith AI Agent"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"
    
    # Supabase (all read from environment / .env — never hardcode)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    # HS256 secret Supabase signs user JWTs with (Dashboard -> Settings
    # -> API -> JWT Secret). Required to verify dashboard logins.
    SUPABASE_JWT_SECRET: Optional[str] = None
    # Override for local testing against a plain PostgREST instance;
    # in production leave unset (derived from SUPABASE_URL/rest/v1).
    POSTGREST_URL: Optional[str] = None
    
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    USE_REAL_TWILIO: bool = False
    
    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    USE_REAL_OPENAI: bool = False
    
    # Anthropic/Claude (optional)
    ANTHROPIC_API_KEY: Optional[str] = None
    USE_CLAUDE: bool = False
    
    # ElevenLabs TTS (optional)
    ELEVENLABS_API_KEY: Optional[str] = None
    
    # Deepgram STT (optional)
    DEEPGRAM_API_KEY: Optional[str] = None
    
    # Auth
    # Escape hatch for local development: set AUTH_ENABLED=false in .env
    # to run the dashboard without logging in. Defaults to enforced.
    AUTH_ENABLED: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # This allows extra fields in .env without errors


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
