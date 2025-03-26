from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "sqlite:///./ihubpt.db"
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Agent settings
    DEFAULT_AGENT_TIMEOUT: int = 300  # 5 minutes
    
    # HITL settings
    HITL_ENABLED: bool = True
    HITL_TIMEOUT: int = 60  # 1 minute timeout for HITL operations
    
    class Config:
        env_file = ".env"

settings = Settings() 