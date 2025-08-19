"""
Main FastAPI application for the AI API (Deployment Version)
"""
import time
import logging
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, create_tables
from app.models import User, APIKey
from app.services.auth_service import auth_service
from app.services.rate_limit_service import rate_limit_service
from app.services.analytics_service import analytics_service

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI API service with authentication and rate limiting (Deployment Version)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("AI API started successfully (Deployment Mode)")

# Request/response models
class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class GenerateRequestBody(BaseModel):
    prompt: str
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    model: Optional[str] = None
    stop_sequences: Optional[list[str]] = None

# Dependencies
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    user = auth_service.get_user_by_api_key(db, api_key)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version, "mode": "deployment"}

# Authentication
@app.post("/auth/register")
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.create_user(db, body.email, body.username, body.password, body.full_name)
        api_key = auth_service.generate_api_key(db, user.id, "Default Key")
        return {"message": "User registered", "api_key": api_key}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    api_key = auth_service.generate_api_key(db, user.id, "Login Key")
    return {"message": "Login successful", "api_key": api_key}

# Text generation (deployment version - mock response)
@app.post("/api/v1/generate")
async def generate_text(
    body: GenerateRequestBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_service.enforce_rate_limit(f"user:{current_user.id}")
    
    # Mock response for deployment (no llama.cpp)
    mock_response = f"[DEPLOYMENT MODE] This is a mock response to: {body.prompt[:50]}..."
    
    # Track usage
    usage_data = {
        "endpoint": "/api/v1/generate",
        "model_used": "mock-deployment",
        "provider": "deployment",
        "input_tokens": len(body.prompt.split()),
        "output_tokens": len(mock_response.split()),
        "total_tokens": len(body.prompt.split()) + len(mock_response.split()),
        "total_cost": 0.0,
        "response_time_ms": 100,
        "status_code": 200,
    }
    analytics_service.track_usage(db, current_user.id, usage_data)
    current_user.update_usage(usage_data["total_tokens"])
    db.commit()
    
    return {
        "text": mock_response,
        "usage": {"total_tokens": usage_data["total_tokens"], "cost": 0.0},
        "model": "mock-deployment",
        "provider": "deployment",
        "note": "Running in deployment mode - local LLM not available"
    }

@app.get("/api/v1/models")
async def get_models():
    return {"models": [{"id": "mock-deployment", "name": "Mock Deployment Model", "display_name": "Deployment Mode"}]}

@app.get("/api/v1/usage")
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stats = analytics_service.get_user_usage_stats(db, current_user.id)
    return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
