"""Configuration settings for the iHubPT application.

This module defines the application's configuration settings using Pydantic's BaseSettings.
All settings can be overridden using environment variables or a .env file.
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings configuration.
    
    This class defines all configurable settings for the application. Settings can be
    overridden using environment variables or a .env file.
    
    Attributes:
        DATABASE_URL (str): SQLite database connection URL.
        API_V1_PREFIX (str): URL prefix for API v1 endpoints.
        SECRET_KEY (str): Secret key for JWT token generation.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): JWT token expiration time in minutes.
        DEFAULT_AGENT_TIMEOUT (int): Default timeout for agent operations in seconds.
        HITL_ENABLED (bool): Whether human-in-the-loop functionality is enabled.
        HITL_TIMEOUT (int): Timeout for HITL operations in seconds.
        OPENAI_MODEL (str): OpenAI model to use for chat completions.
        OPENAI_TEMPERATURE (float): Temperature setting for model responses.
        OPENAI_MAX_TOKENS (Optional[int]): Maximum tokens per response.
    """
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
    
    # OpenAI settings
    OPENAI_MODEL: str = "gpt-4-turbo-preview"  # Model to use for chat
    OPENAI_TEMPERATURE: float = 0.7  # Temperature for model responses
    OPENAI_MAX_TOKENS: Optional[int] = None  # Max tokens per response, None for no limit
    
    class Config:
        """Pydantic configuration for environment variable loading."""
        env_file = ".env"

# Global settings instance
settings = Settings() 