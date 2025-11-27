from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.models.database import engine, Base
from app.api.routes import voice, dashboard, business

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="Zenith AI Agent API",
    description="Multilingual AI Phone Agent System",
    version="1.0.0",
    docs_url="/docs",
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
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(business.router, prefix="/api/business", tags=["Business"])

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "mode": settings.ENV,
        "features": {
            "real_openai": settings.USE_REAL_OPENAI,
            "real_twilio": settings.USE_REAL_TWILIO,
            "real_redis": settings.USE_REAL_REDIS
        }
    }

# Demo endpoint
@app.get("/demo")
async def demo():
    return {
        "message": "Zenith AI Agent - Ready to serve!",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "simulate_call": "/api/voice/test/simulate",
            "create_business": "/api/business/create",
            "dashboard_stats": "/api/dashboard/stats?business_id=YOUR_ID"
        },
        "status": "All systems operational"
    }

@app.get("/")
async def root():
    return {
        "app": "Zenith AI Phone Agent",
        "status": "running",
        "docs": "/docs",
        "demo": "/demo"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
