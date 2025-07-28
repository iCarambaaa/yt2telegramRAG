

import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
import yaml

from .exceptions import ValidationError

class InputValidator:
    """Comprehensive input validation and sanitization utilities."""
    
    # Regex patterns for validation
    YOUTUBE_CHANNEL_ID_PATTERN = re.compile(r'^UC[a-zA-Z0-9_-]{22}$')
    YOUTUBE_VIDEO_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    YOUTUBE_URL_PATTERN = re.compile(
        r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|channel/|c/|@)?([a-zA-Z0-9_-]+)'
    )
    TELEGRAM_CHAT_ID_PATTERN = re.compile(r'^-?\d+$')
    ENV_VAR_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*$')
    
    # Limits
    MAX_TITLE_LENGTH = 500
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_FILE_PATH_LENGTH = 4096
    MAX_CONFIG_FILE_SIZE = 1024 * 1024  # 1MB
    DEFAULT_SUMMARY_LENGTH = 5000   # limit
    
    @classmethod
    def validate_youtube_channel_id(cls, channel_id: str) -> str:
        """Validate and sanitize YouTube channel ID."""
        if not isinstance(channel_id, str):
            raise ValidationError(f"Channel ID must be a string, got {type(channel_id)}")
        
        channel_id = channel_id.strip()
        
        # Handle full URLs
        if channel_id.startswith('http'):
            channel_id = cls.extract_channel_id_from_url(channel_id)
        
        # Validate format
        if not cls.YOUTUBE_CHANNEL_ID_PATTERN.match(channel_id):
            raise ValidationError(
                f"Invalid YouTube channel ID format: {channel_id}. "
                f"Expected format: UC followed by 22 characters"
            )
        
        return channel_id
    
    @classmethod
    def validate_youtube_video_id(cls, video_id: str) -> str:
        """Validate and sanitize YouTube video ID."""
        if not isinstance(video_id, str):
            raise ValidationError(f"Video ID must be a string, got {type(video_id)}")
        
        video_id = video_id.strip()
        
        # Handle full URLs
        if video_id.startswith('http'):
            video_id = cls.extract_video_id_from_url(video_id)
        
        # Validate format
        if not cls.YOUTUBE_VIDEO_ID_PATTERN.match(video_id):
            raise ValidationError(
                f"Invalid YouTube video ID format: {video_id}. "
                f"Expected format: 11 characters"
            )
        
        return video_id
    
    @classmethod
    def validate_telegram_chat_id(cls, chat_id: Union[str, int]) -> int:
        """Validate and sanitize Telegram chat ID."""
        if isinstance(chat_id, int):
            return chat_id
        
        if not isinstance(chat_id, str):
            raise ValidationError(f"Chat ID must be a string or integer, got {type(chat_id)}")
        
        chat_id = chat_id.strip()
        
        if not cls.TELEGRAM_CHAT_ID_PATTERN.match(chat_id):
            raise ValidationError(
                f"Invalid Telegram chat ID format: {chat_id}. "
                f"Expected format: numeric value"
            )
        
        try:
            return int(chat_id)
        except ValueError:
            raise ValidationError(f"Invalid Telegram chat ID: {chat_id}")
    
    @classmethod
    def validate_environment_variable(cls, env_var: str) -> str:
        """Validate environment variable name."""
        if not isinstance(env_var, str):
            raise ValidationError(f"Environment variable must be a string, got {type(env_var)}")
        
        env_var = env_var.strip()
        
        if not cls.ENV_VAR_PATTERN.match(env_var):
            raise ValidationError(
                f"Invalid environment variable name: {env_var}. "
                f"Must start with uppercase letter and contain only uppercase letters, numbers, and underscores"
            )
        
        return env_var
    
    @classmethod
    def validate_file_path(cls, file_path: str, must_exist: bool = False) -> str:
        """Validate and sanitize file path."""
        if not isinstance(file_path, str):
            raise ValidationError(f"File path must be a string, got {type(file_path)}")
        
        file_path = file_path.strip()
        
        if not file_path:
            raise ValidationError("File path cannot be empty")
        
        if len(file_path) > cls.MAX_FILE_PATH_LENGTH:
            raise ValidationError(
                f"File path too long: {len(file_path)} characters (max: {cls.MAX_FILE_PATH_LENGTH})"
            )
        
        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            raise ValidationError(f"Invalid file path: {file_path}")
        
        # Normalize path
        try:
            normalized_path = Path(file_path).resolve()
        except Exception as e:
            raise ValidationError(f"Invalid file path: {file_path} - {e}")
        
        if must_exist and not normalized_path.exists():
            raise ValidationError(f"File does not exist: {normalized_path}")
        
        return str(normalized_path)
    
    @classmethod
    def validate_text_content(cls, text: str, max_length: int = None, allow_empty: bool = True) -> str:
        """Validate and sanitize text content."""
        if not isinstance(text, str):
            raise ValidationError(f"Text must be a string, got {type(text)}")
        
        text = text.strip()
        
        if not allow_empty and not text:
            raise ValidationError("Text cannot be empty")
        
        if max_length and len(text) > max_length:
            raise ValidationError(
                f"Text too long: {len(text)} characters (max: {max_length})"
            )
        
        # Basic sanitization
        text = cls.sanitize_text(text)
        
        return text
    
    @classmethod
    def validate_configuration(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize configuration dictionary."""
        if not isinstance(config, dict):
            raise ValidationError(f"Configuration must be a dictionary, got {type(config)}")
        
        validated_config = {}
        
        # Validate channels configuration
        if 'channels' not in config:
            raise ValidationError("Configuration must contain 'channels' key")
        
        channels = config['channels']
        if not isinstance(channels, list):
            raise ValidationError("'channels' must be a list")
        
        validated_channels = []
        for idx, channel_config in enumerate(channels):
            if not isinstance(channel_config, dict):
                raise ValidationError(f"Channel configuration at index {idx} must be a dictionary")
            
            validated_channel = cls.validate_channel_config(channel_config)
            validated_channels.append(validated_channel)
        
        validated_config['channels'] = validated_channels
        
        # Validate optional settings
        if 'database' in config:
            validated_config['database'] = cls.validate_database_config(config['database'])
        
        if 'logging' in config:
            validated_config['logging'] = cls.validate_logging_config(config['logging'])
        
        return validated_config
    
    @classmethod
    def validate_channel_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual channel configuration."""
        validated = {}
        
        # Required fields
        required_fields = ['name', 'channel_id', 'telegram_bots']
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate name
        validated['name'] = cls.validate_text_content(
            config['name'], 
            max_length=100, 
            allow_empty=False
        )
        
        # Validate channel_id
        validated['channel_id'] = cls.validate_youtube_channel_id(config['channel_id'])
        
        # Validate telegram_bots
        telegram_bots = config['telegram_bots']
        if not isinstance(telegram_bots, list):
            raise ValidationError("'telegram_bots' must be a list")
        
        validated_bots = []
        for idx, bot_config in enumerate(telegram_bots):
            if not isinstance(bot_config, dict):
                raise ValidationError(f"Telegram bot configuration at index {idx} must be a dictionary")
            
            validated_bot = cls.validate_telegram_bot_config(bot_config)
            validated_bots.append(validated_bot)
        
        validated['telegram_bots'] = validated_bots
        
        # Optional fields
        if 'check_interval' in config:
            try:
                check_interval = int(config['check_interval'])
                if check_interval < 60:  # Minimum 1 minute
                    raise ValidationError("check_interval must be at least 60 seconds")
                validated['check_interval'] = check_interval
            except (ValueError, TypeError):
                raise ValidationError("check_interval must be a positive integer")
        
        # Validate schedule
        if 'schedule' in config:
            schedule_type = config['schedule']
            if schedule_type not in ['daily', 'weekly', 'monthly']:
                raise ValidationError(f"Invalid schedule type: {schedule_type}. Must be 'daily', 'weekly', or 'monthly'.")
            validated['schedule'] = schedule_type
        else:
            # Default schedule if not provided
            validated['schedule'] = 'daily'

        # Validate db_path
        if 'db_path' in config:
            validated['db_path'] = cls.validate_file_path(config['db_path'])
        else:
            raise ValidationError("Missing required field: 'db_path'")

        # Validate cookies_file
        if 'cookies_file' in config and config['cookies_file'] is not None:
            validated['cookies_file'] = cls.validate_file_path(config['cookies_file'], must_exist=True)
        else:
            validated['cookies_file'] = None

        # Validate max_videos_to_fetch
        if 'max_videos_to_fetch' in config:
            try:
                max_videos = int(config['max_videos_to_fetch'])
                if max_videos < 1:
                    raise ValidationError("max_videos_to_fetch must be at least 1")
                validated['max_videos_to_fetch'] = max_videos
            except (ValueError, TypeError):
                raise ValidationError("max_videos_to_fetch must be an integer")
        else:
            validated['max_videos_to_fetch'] = 5 # Default value

        # Validate retry_attempts
        if 'retry_attempts' in config:
            try:
                attempts = int(config['retry_attempts'])
                if attempts < 1:
                    raise ValidationError("retry_attempts must be at least 1")
                validated['retry_attempts'] = attempts
            except (ValueError, TypeError):
                raise ValidationError("retry_attempts must be an integer")
        else:
            validated['retry_attempts'] = 3 # Default value

        # Validate retry_delay_seconds
        if 'retry_delay_seconds' in config:
            try:
                delay = int(config['retry_delay_seconds'])
                if delay < 0:
                    raise ValidationError("retry_delay_seconds cannot be negative")
                validated['retry_delay_seconds'] = delay
            except (ValueError, TypeError):
                raise ValidationError("retry_delay_seconds must be an integer")
        else:
            validated['retry_delay_seconds'] = 5 # Default value

        # Validate llm_config
        if 'llm_config' in config:
            validated['llm_config'] = cls.validate_llm_config(config['llm_config'])
        else:
            validated['llm_config'] = {} # Default empty config

        # Validate subtitles
        if 'subtitles' in config:
            subtitles = config['subtitles']
            if not isinstance(subtitles, list):
                raise ValidationError("'subtitles' must be a list")
            validated_subtitles = []
            for idx, sub_config in enumerate(subtitles):
                if not isinstance(sub_config, dict):
                    raise ValidationError(f"Subtitle configuration at index {idx} must be a dictionary")
                validated_subtitles.append(cls.validate_subtitle_config(sub_config))
            validated['subtitles'] = validated_subtitles
        else:
            validated['subtitles'] = [] # Default empty list

        return validated
    
    @classmethod
    def validate_telegram_bot_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Telegram bot configuration."""
        validated = {}
        
        # Validate token_env (required)
        if 'token_env' not in config:
            raise ValidationError("Missing required field: 'token_env' for Telegram bot")
        validated['token_env'] = cls.validate_environment_variable(config['token_env'])
        
        # Validate chat_id_env or chat_id (one is required)
        chat_id_env = config.get('chat_id_env')
        chat_id = config.get('chat_id')

        if chat_id_env is None and chat_id is None:
            raise ValidationError("Missing required field: 'chat_id_env' or 'chat_id' for Telegram bot")

        if chat_id_env is not None:
            validated['chat_id_env'] = cls.validate_environment_variable(chat_id_env)
        
        if chat_id is not None:
            validated['chat_id'] = cls.validate_telegram_chat_id(chat_id)
        
        # Validate optional name
        if 'name' in config:
            validated['name'] = cls.validate_text_content(
                config['name'], 
                max_length=50, 
                allow_empty=False
            )
        else:
            validated['name'] = 'Unnamed Bot'
        
        return validated
    
    @classmethod
    def validate_llm_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate LLM configuration."""
        validated = {}

        # Validate llm_api_key_env (required)
        if 'llm_api_key_env' not in config:
            raise ValidationError("Missing required field: 'llm_api_key_env' for LLM config")
        validated['llm_api_key_env'] = cls.validate_environment_variable(config['llm_api_key_env'])

        # Validate llm_model_env or llm_model
        llm_model_env = config.get('llm_model_env')
        llm_model = config.get('llm_model')
        if llm_model_env is not None:
            validated['llm_model_env'] = cls.validate_environment_variable(llm_model_env)
        if llm_model is not None:
            validated['llm_model'] = cls.validate_text_content(llm_model, allow_empty=False)
        if llm_model_env is None and llm_model is None:
            # If neither is provided, it will fall back to hardcoded default in LLMSummarizer
            pass 

        # Validate llm_base_url_env or llm_base_url
        llm_base_url_env = config.get('llm_base_url_env')
        llm_base_url = config.get('llm_base_url')
        if llm_base_url_env is not None:
            validated['llm_base_url_env'] = cls.validate_environment_variable(llm_base_url_env)
        if llm_base_url is not None:
            # Basic URL validation (can be more robust if needed)
            if not re.match(r'^https?://', llm_base_url):
                raise ValidationError(f"Invalid LLM base URL format: {llm_base_url}. Must start with http(s)://")
            validated['llm_base_url'] = cls.validate_text_content(llm_base_url, allow_empty=False)
        if llm_base_url_env is None and llm_base_url is None:
            # If neither is provided, it will fall back to hardcoded default in LLMSummarizer
            pass

        # Validate llm_prompt_template_path or llm_prompt_template
        llm_prompt_template_path = config.get('llm_prompt_template_path')
        llm_prompt_template = config.get('llm_prompt_template')
        if llm_prompt_template_path is not None:
            validated['llm_prompt_template_path'] = cls.validate_file_path(llm_prompt_template_path, must_exist=True)
        if llm_prompt_template is not None:
            validated['llm_prompt_template'] = cls.validate_text_content(llm_prompt_template, allow_empty=False)
        if llm_prompt_template_path is None and llm_prompt_template is None:
            # If neither is provided, it will fall back to hardcoded default in LLMSummarizer
            pass

        return validated

    @classmethod
    def validate_subtitle_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate subtitle configuration."""
        validated = {}

        # Validate lang (required)
        if 'lang' not in config:
            raise ValidationError("Missing required field: 'lang' for subtitle config")
        validated['lang'] = cls.validate_text_content(config['lang'], max_length=10, allow_empty=False)

        # Validate type (required)
        if 'type' not in config:
            raise ValidationError("Missing required field: 'type' for subtitle config")
        if config['type'] not in ['manual', 'automatic']:
            raise ValidationError(f"Invalid subtitle type: {config['type']}. Must be 'manual' or 'automatic'.")
        validated['type'] = config['type']

        return validated
    
    @classmethod
    def validate_database_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate database configuration."""
        validated = {}
        
        if 'path' in config:
            validated['path'] = cls.validate_file_path(config['path'])
        
        if 'max_connections' in config:
            try:
                max_connections = int(config['max_connections'])
                if max_connections < 1 or max_connections > 100:
                    raise ValidationError("max_connections must be between 1 and 100")
                validated['max_connections'] = max_connections
            except (ValueError, TypeError):
                raise ValidationError("max_connections must be an integer")
        
        return validated
    
    @classmethod
    def validate_logging_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate logging configuration."""
        validated = {}
        
        if 'level' in config:
            level = config['level'].upper()
            if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                raise ValidationError(f"Invalid log level: {level}")
            validated['level'] = level
        
        if 'file' in config:
            validated['file'] = cls.validate_file_path(config['file'])
        
        return validated
    
    @classmethod
    def validate_yaml_file(cls, file_path: str) -> Dict[str, Any]:
        """Validate and load YAML configuration file."""
        file_path = cls.validate_file_path(file_path, must_exist=True)
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > cls.MAX_CONFIG_FILE_SIZE:
            raise ValidationError(
                f"Configuration file too large: {file_size} bytes (max: {cls.MAX_CONFIG_FILE_SIZE})"
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML file: {e}")
        except Exception as e:
            raise ValidationError(f"Error reading configuration file: {e}")
        
        return cls.validate_configuration(config)
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitize text content."""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    @classmethod
    def extract_channel_id_from_url(cls, url: str) -> str:
        """Extract channel ID from YouTube URL."""
        parsed = urlparse(url)
        
        # Handle different URL formats
        if '/channel/' in url:
            match = re.search(r'/channel/([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
        elif '/c/' in url:
            # Custom URL - need to resolve to actual channel ID
            raise ValidationError(
                f"Custom URL detected: {url}. Please provide the actual channel ID (UC...)"
            )
        elif '@' in url:
            # Handle @username format
            raise ValidationError(
                f"Username URL detected: {url}. Please provide the actual channel ID (UC...)"
            )
        
        raise ValidationError(f"Cannot extract channel ID from URL: {url}")
    
    @classmethod
    def extract_video_id_from_url(cls, url: str) -> str:
        """Extract video ID from YouTube URL."""
        parsed = urlparse(url)
        
        # Handle different URL formats
        if 'v=' in url:
            match = re.search(r'[?&]v=([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
        elif 'youtu.be' in url:
            match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
        
        raise ValidationError(f"Cannot extract video ID from URL: {url}")

class Sanitizer:
    """Text sanitization utilities."""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        
        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename
    
    @staticmethod
    def sanitize_path_component(path: str) -> str:
        """Sanitize path component for safe directory usage."""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            path = path.replace(char, '_')
        
        # Remove leading/trailing spaces
        path = path.strip()
        
        # Ensure not empty
        if not path:
            path = 'unnamed'
        
        return path
    
    @staticmethod
    def sanitize_telegram_message(text: str, max_length: int = 4096) -> str:
        """Sanitize text for Telegram message."""
        # Telegram has a 4096 character limit
        if len(text) > max_length:
            text = text[:max_length - 3] + '...'
        
        # Escape special characters for MarkdownV2
        special_chars = '_*[]()~`>#+-=|{}.!'
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
