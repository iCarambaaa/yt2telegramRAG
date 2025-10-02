"""
Configuration settings for the Unified GUI Platform.

CRITICAL: Core configuration management
"""

import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    reload: bool = True
    log_level: str = "INFO"
    
    # Database configuration
    database_url: str = "sqlite:///gui/data/gui.db"
    
    # Security
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # CORS settings
    cors_origins: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "https://localhost:3000"
    ]
    
    # Rate limiting
    rate_limit_requests_per_minute: int = 120
    
    # WebSocket settings
    websocket_ping_interval: int = 30
    websocket_ping_timeout: int = 10
    
    # Telegram integration (optional)
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # File paths
    data_directory: str = "gui/data"
    static_directory: str = "gui/static"
    
    class Config:
        env_file = ".env"
        env_prefix = "GUI_"


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings