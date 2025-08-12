from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import yaml

@dataclass
class ChannelConfig:
    name: str
    channel_id: str
    db_path: str
    schedule: str
    max_videos_to_fetch: int = 5
    cookies_file: Optional[str] = None
    subtitle_preferences: List[str] = None
    telegram_bots_config: List[Dict] = None
    llm_config: Dict[str, Any] = None
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    def __post_init__(self):
        if self.subtitle_preferences is None:
            self.subtitle_preferences = []
        if self.telegram_bots_config is None:
            self.telegram_bots_config = []
        if self.llm_config is None:
            self.llm_config = {}
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'ChannelConfig':
        """Load channel config from YAML file"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data['name'],
            channel_id=data['channel_id'],
            db_path=data['db_path'],
            schedule=data['schedule'],
            max_videos_to_fetch=data.get('max_videos_to_fetch', 5),
            cookies_file=data.get('cookies_file'),
            subtitle_preferences=cls._extract_subtitle_languages(data.get('subtitles', [])),
            telegram_bots_config=data.get('telegram_bots', []),
            llm_config=data.get('llm_config', {}),
            retry_attempts=data.get('retry_attempts', 3),
            retry_delay_seconds=data.get('retry_delay_seconds', 5)
        )
    
    @classmethod
    def _extract_subtitle_languages(cls, subtitle_config: List) -> List[str]:
        """Extract language codes from subtitle configuration"""
        languages = []
        
        # Handle both old format (list of dicts) and new format (list of strings)
        for item in subtitle_config:
            if isinstance(item, dict):
                lang = item.get('lang', 'en')
                if lang not in languages:
                    languages.append(lang)
            elif isinstance(item, str):
                if item not in languages:
                    languages.append(item)
        
        return languages or ['en']  # Default to English if empty