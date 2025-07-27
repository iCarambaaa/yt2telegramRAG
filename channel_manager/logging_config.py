"""
Centralized logging configuration for the channel_manager package.
Provides structured logging with different levels and output formats.
"""

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json

class LoggingConfig:
    """Centralized logging configuration manager."""
    
    DEFAULT_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'logs/channel_manager.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': 'logs/channel_manager_errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            'channel_manager': {
                'level': 'DEBUG',
                'handlers': ['console', 'file', 'error_file'],
                'propagate': False
            },
            'telegram': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'youtube': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'database': {
                'level': 'DEBUG',
                'handlers': ['file', 'error_file'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }

    @classmethod
    def setup_logging(
        cls,
        log_level: str = 'INFO',
        log_file: Optional[str] = None,
        log_dir: str = 'logs',
        json_logs: bool = False,
        debug: bool = False
    ) -> None:
        """
        Setup logging configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Custom log file path
            log_dir: Directory for log files
            json_logs: Use JSON format for structured logging
            debug: Enable debug mode with more verbose logging
        """
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        config = cls.DEFAULT_CONFIG.copy()
        
        # Update log level
        level = getattr(logging, log_level.upper(), logging.INFO)
        config['handlers']['console']['level'] = level
        config['handlers']['file']['level'] = level
        
        # Update log file paths
        if log_file:
            config['handlers']['file']['filename'] = log_file
        else:
            config['handlers']['file']['filename'] = str(log_path / 'channel_manager.log')
            config['handlers']['error_file']['filename'] = str(log_path / 'channel_manager_errors.log')
        
        # Use JSON formatter if requested
        if json_logs:
            config['handlers']['file']['formatter'] = 'json'
            config['handlers']['error_file']['formatter'] = 'json'
        
        # Enable debug mode
        if debug:
            config['handlers']['console']['formatter'] = 'detailed'
            config['loggers']['channel_manager']['level'] = 'DEBUG'
        
        # Configure logging
        logging.config.dictConfig(config)
        
        # Log configuration
        logger = logging.getLogger('channel_manager')
        logger.info(f"Logging configured: level={log_level}, json={json_logs}, debug={debug}")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a configured logger instance."""
        return logging.getLogger(f'channel_manager.{name}')

def setup_logging_from_env() -> None:
    """Setup logging based on environment variables."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_dir = os.getenv('LOG_DIR', 'logs')
    json_logs = os.getenv('JSON_LOGS', 'false').lower() == 'true'
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    LoggingConfig.setup_logging(
        log_level=log_level,
        log_dir=log_dir,
        json_logs=json_logs,
        debug=debug
    )