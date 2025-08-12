"""
Custom exception classes for the channel_manager package.
"""

class ChannelManagerError(Exception):
    """Base exception for all channel manager errors."""
    pass

class DatabaseError(ChannelManagerError):
    """Raised when database operations fail."""
    pass

class ConfigurationError(ChannelManagerError):
    """Raised when configuration is invalid or missing."""
    pass

class NetworkError(ChannelManagerError):
    """Raised when network operations fail."""
    pass

class YouTubeAPIError(NetworkError):
    """Raised when YouTube API operations fail."""
    pass

class TelegramAPIError(NetworkError):
    """Raised when Telegram API operations fail."""
    pass

class LLMError(NetworkError):
    """Raised when LLM operations fail."""
    pass

class SubtitleProcessingError(ChannelManagerError):
    """Raised when subtitle processing fails."""
    pass

class ValidationError(ChannelManagerError):
    """Raised when input validation fails."""
    pass

class RetryExhaustedError(ChannelManagerError):
    """Raised when all retry attempts are exhausted."""
    pass