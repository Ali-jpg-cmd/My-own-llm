"""
Configuration settings for the AI API
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "My Own LLM API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=True, env="DEBUG")
    
    # Database (default to local SQLite for free setup)
    database_url: str = Field(default="sqlite:///./llm_api.db", env="DATABASE_URL")
    
    # Security
    secret_key: str = Field(default="dev-secret-change-me", env="SECRET_KEY")
    jwt_secret: str = Field(default="dev-jwt-secret-change-me", env="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    
    # LLM Configuration (default to llama.cpp for 100% free local inference)
    llm_provider: str = Field(default="llamacpp", env="LLM_PROVIDER")
    llm_model: str = Field(default="meta-llama/Llama-2-7b-chat-hf", env="LLM_MODEL")
    # llama.cpp model path (GGUF). Example: models/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf
    llm_model_path: Optional[str] = Field(default="models/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf", env="LLM_MODEL_PATH")
    llm_context_size: int = Field(default=4096, env="LLM_CONTEXT_SIZE")
    llm_n_gpu_layers: int = Field(default=0, env="LLM_N_GPU_LAYERS")  # 0 = CPU only (free)
    llm_threads: Optional[int] = Field(default=None, env="LLM_THREADS")

    # Optional hosted providers (not required for free setup)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # Redis (unused in free setup; kept for optional distributed rate limiting)
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Stripe (optional monetization; not needed for free setup)
    stripe_secret_key: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    
    # Pricing (informational only for local free setup)
    price_per_1k_tokens: float = Field(default=0.0, env="PRICE_PER_1K_TOKENS")
    
    # CORS
    allowed_origins: list = Field(default=["*", "https://ali-jpg-cmd.github.io"], env="ALLOWED_ORIGINS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
