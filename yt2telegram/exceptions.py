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

class MembersOnlyError(YouTubeAPIError):
    """Raised when video is permanently restricted to channel members."""
    pass

class MembersFirstError(YouTubeAPIError):
    """Raised when video is temporarily restricted (early access for members).
    
    Attributes:
        release_timestamp: Unix timestamp when video becomes public (if available)
    """
    def __init__(self, message: str, release_timestamp: int = None):
        super().__init__(message)
        self.release_timestamp = release_timestamp