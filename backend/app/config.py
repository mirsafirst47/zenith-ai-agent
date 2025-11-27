from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    BASE_URL: str
    FRONTEND_URL: str
    
    # Database
    DATABASE_URL: str
    
    # Services (mock-friendly)
    REDIS_URL: str = "mock://localhost"
    OPENAI_API_KEY: str = "mock-key"
    ANTHROPIC_API_KEY: str = "mock-key"
    ELEVENLABS_API_KEY: str = "mock-key"
    ELEVENLABS_VOICE_ID: str = "mock-voice"
    TWILIO_ACCOUNT_SID: str = "mock-sid"
    TWILIO_AUTH_TOKEN: str = "mock-token"
    TWILIO_PHONE_NUMBER: str = "+15555551234"
    AWS_ACCESS_KEY_ID: str = "mock-key"
    AWS_SECRET_ACCESS_KEY: str = "mock-secret"
    AWS_S3_BUCKET: str = "mock-bucket"
    AWS_REGION: str = "us-east-1"
    STRIPE_SECRET_KEY: str = "mock-key"
    SENTRY_DSN: str = ""
    
    # Feature flags
    USE_REAL_OPENAI: bool = False
    USE_REAL_TWILIO: bool = False
    USE_REAL_ELEVENLABS: bool = False
    USE_REAL_S3: bool = False
    USE_REAL_REDIS: bool = False
    
    # Supported Languages
    SUPPORTED_LANGUAGES: List[str] = ["en", "es", "zh", "fr", "ru"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
