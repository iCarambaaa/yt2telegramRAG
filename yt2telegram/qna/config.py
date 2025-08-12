"""Configuration management for Q&A bot."""
import os
import yaml
from typing import Dict, Any

class QnAConfig:
    """Configuration manager for Q&A bot."""
    
    def __init__(self, config_path: str):
        """Load configuration from YAML file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    @property
    def bot_token(self) -> str:
        """Get Q&A bot token."""
        return self.config.get('qa_bot_token') or os.getenv('QA_BOT_TOKEN')
    
    @property
    def chat_id(self) -> str:
        """Get chat ID (shared with summary bot)."""
        return str(self.config.get('summary_chat_id') or os.getenv('SUMMARY_CHAT_ID'))
    
    @property
    def database_path(self) -> str:
        """Get database path relative to qna directory."""
        db_path = self.config.get('database_path', '../downloads/example.db')
        return os.path.join(os.path.dirname(__file__), db_path)
    
    @property
    def openrouter_key(self) -> str:
        """Get OpenRouter API key."""
        return self.config.get('openrouter_api_key') or os.getenv('OPENROUTER_API_KEY')
    
    @property
    def channel_name(self) -> str:
        """Get channel name for display."""
        return self.config.get('channel_name', 'Q&A Bot')
    
    def validate(self) -> bool:
        """Validate required configuration."""
        required = [self.bot_token, self.chat_id, self.database_path, self.openrouter_key]
        return all(required)
    
    def __repr__(self) -> str:
        return f"QnAConfig(channel={self.channel_name}, chat_id={self.chat_id})"