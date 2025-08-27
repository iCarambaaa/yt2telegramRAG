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