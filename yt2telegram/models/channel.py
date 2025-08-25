from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import yaml
import logging

logger = logging.getLogger(__name__)

@dataclass
class ChannelConfig:
    name: str
    channel_id: str
    db_path: str
    max_videos_to_fetch: int = 5
    cookies_file: Optional[str] = None
    subtitle_preferences: List[str] = None
    telegram_bots_config: List[Dict] = None
    llm_config: Dict[str, Any] = None
    multi_model_config: Optional[Dict[str, Any]] = None
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    def __post_init__(self):
        if self.subtitle_preferences is None:
            self.subtitle_preferences = []
        if self.telegram_bots_config is None:
            self.telegram_bots_config = []
        if self.llm_config is None:
            self.llm_config = {}
        if self.multi_model_config is None:
            self.multi_model_config = {}
        
        # Validate multi-model configuration if provided
        if self.multi_model_config:
            self._validate_multi_model_config()
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'ChannelConfig':
        """Load channel config from YAML file"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data['name'],
            channel_id=data['channel_id'],
            db_path=data['db_path'],
            max_videos_to_fetch=data.get('max_videos_to_fetch', 5),
            cookies_file=data.get('cookies_file'),
            subtitle_preferences=cls._extract_subtitle_languages(data.get('subtitles', [])),
            telegram_bots_config=data.get('telegram_bots', []),
            llm_config=data.get('llm_config', {}),
            multi_model_config=cls._parse_multi_model_config(data.get('llm_config', {})),
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
    
    def is_multi_model_enabled(self) -> bool:
        """Check if multi-model summarization is enabled for this channel"""
        return bool(self.multi_model_config and 
                    self.multi_model_config.get('enabled', False))
    
    def _validate_multi_model_config(self) -> None:
        """Validate multi-model configuration settings"""
        if not self.multi_model_config.get('enabled', False):
            return  # No validation needed if not enabled
        
        config = self.multi_model_config
        
        # Required fields when multi-model is enabled
        required_fields = ['primary_model', 'secondary_model', 'synthesis_model']
        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Multi-model configuration missing required field: {field}")
        
        # Validate fallback strategy
        valid_strategies = ['best_summary', 'primary_summary', 'single_model']
        fallback_strategy = config.get('fallback_strategy', 'best_summary')
        if fallback_strategy not in valid_strategies:
            raise ValueError(f"Invalid fallback_strategy: {fallback_strategy}. Must be one of: {valid_strategies}")
        
        # Validate cost threshold (if provided)
        cost_threshold = config.get('cost_threshold_tokens')
        if cost_threshold is not None:
            if not isinstance(cost_threshold, int) or cost_threshold <= 0:
                raise ValueError("cost_threshold_tokens must be a positive integer")
        
        # Validate synthesis prompt template path (if provided)
        synthesis_prompt_path = config.get('synthesis_prompt_template_path')
        if synthesis_prompt_path and not isinstance(synthesis_prompt_path, str):
            raise ValueError("synthesis_prompt_template_path must be a string")
        
        # Validate temperature (if provided)
        temperature = config.get('temperature')
        if temperature is not None:
            if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
                raise ValueError("temperature must be a number between 0 and 2")
        
        # Validate top_p (if provided)
        top_p = config.get('top_p')
        if top_p is not None:
            if not isinstance(top_p, (int, float)) or top_p < 0 or top_p > 1:
                raise ValueError("top_p must be a number between 0 and 1")
        
        logger.debug(f"Multi-model configuration validated for channel {self.name}")
    
    @classmethod
    def _parse_multi_model_config(cls, llm_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse multi-model configuration from llm_config section"""
        multi_model_data = llm_config.get('multi_model')
        if not multi_model_data:
            return None
        
        # Set default values for optional fields
        parsed_config = {
            'enabled': multi_model_data.get('enabled', False),
            'primary_model': multi_model_data.get('primary_model'),
            'secondary_model': multi_model_data.get('secondary_model'),
            'synthesis_model': multi_model_data.get('synthesis_model'),
            'synthesis_prompt_template_path': multi_model_data.get('synthesis_prompt_template_path'),
            'cost_threshold_tokens': multi_model_data.get('cost_threshold_tokens'),
            'fallback_strategy': multi_model_data.get('fallback_strategy', 'best_summary'),
            'temperature': multi_model_data.get('temperature'),
            'top_p': multi_model_data.get('top_p')
        }
        
        # Remove None values to keep config clean
        return {k: v for k, v in parsed_config.items() if v is not None}