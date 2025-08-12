import re
from typing import Any

class ValidationError(Exception):
    pass

class InputValidator:
    @staticmethod
    def validate_telegram_chat_id(chat_id: Any) -> int:
        """Validate and convert telegram chat ID to integer"""
        try:
            chat_id_int = int(chat_id)
            return chat_id_int
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid chat ID format: {chat_id}")
    
    @staticmethod
    def validate_youtube_channel_id(channel_id: str) -> str:
        """Validate YouTube channel ID format"""
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string")
        
        # YouTube channel IDs are typically 24 characters starting with UC
        if not re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id):
            raise ValidationError(f"Invalid YouTube channel ID format: {channel_id}")
        
        return channel_id

class Sanitizer:
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2"""
        if not text:
            return text
        escape_chars_pattern = r'([\\_*[\]()~`>#+-=|{}.!])'
        return re.sub(escape_chars_pattern, r'\\\\1', text)