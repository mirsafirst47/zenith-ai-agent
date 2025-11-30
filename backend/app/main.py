"""Zenith AI Agent - Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables FIRST
load_dotenv()

from app.config import settings
from app.models.database import engine, Base
from app.api.routes import voice, businesses, calls, analytics

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="Multilingual AI Phone Agent System",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(businesses.router, prefix="/api/businesses", tags=["Businesses"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

# Initialize Claude if available
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key and anthropic_key != "mock":
    try:
        from app.services.claude_service import claude_service
        if claude_service.is_available:
            print("✅ Claude AI initialized successfully")
        else:
            print("⚠️ Claude service created but not available")
    except Exception as e:
        print(f"⚠️ Claude initialization skipped: {e}")
else:
    print("ℹ️ Running without Claude (using mock responses)")


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "claude_enabled": bool(os.getenv("ANTHROPIC_API_KEY"))
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "claude_available": bool(os.getenv("ANTHROPIC_API_KEY")),
        "database": "connected"
    }
