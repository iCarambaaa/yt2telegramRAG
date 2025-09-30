<<<<<<< Updated upstream
"""Configuration classes for the GUI application."""
import os
from pathlib import Path

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('GUI_SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Flask settings
    DEBUG = False
    TESTING = False
    
    # Application settings
    HOST = os.environ.get('GUI_HOST', 'localhost')
    PORT = int(os.environ.get('GUI_PORT', 5000))
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent
    CHANNELS_DIR = PROJECT_ROOT / 'yt2telegram' / 'channels'
    PROMPTS_DIR = PROJECT_ROOT / 'yt2telegram' / 'prompts'
    DOWNLOADS_DIR = PROJECT_ROOT / 'downloads'
    
    # Database settings
    DATABASE_TIMEOUT = 30.0
    MAX_DATABASE_CONNECTIONS = 10
    
    # WebSocket settings
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_CORS_ALLOWED_ORIGINS = ['http://localhost:5000']

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SOCKETIO_LOGGER = True
    SOCKETIO_ENGINEIO_LOGGER = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SECRET_KEY = os.environ.get('GUI_SECRET_KEY')
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
=======
"""
Configuration management for the Unified GUI Platform.

SECURITY: Environment-based configuration with secure defaults
"""

import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Unified GUI Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    
    # Database settings
    database_url: str = "sqlite:///gui/data/gui_main.db"
    
    # Security settings
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # CORS settings
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Logging settings
    log_level: str = "INFO"
    
    # Integration settings
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # LLM settings
    llm_provider_api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
>>>>>>> Stashed changes
