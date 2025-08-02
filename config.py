from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    openai_model_name: str = "gpt-4"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 1000
    
    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "chatbot_knowledge"
    qdrant_vector_size: int = 1536
    
    # Application Configuration
    app_name: str = "Production Chatbot"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Monitoring
    enable_metrics: bool = True
    prometheus_port: int = 9090
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()