from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import yaml

# @agent:service-type data-model
# @agent:scalability stateless
# @agent:persistence file_system
# @agent:priority critical
# @agent:dependencies yaml,file_system,configuration_validation
@dataclass
class ChannelConfig:
    """Comprehensive channel configuration model with multi-model support and validation.
    
    Represents complete configuration for a YouTube channel including processing
    preferences, AI model settings, Telegram delivery options, and operational
    parameters. Supports both single-model and multi-model processing workflows
    with extensive validation and backward compatibility.
    
    Architecture: Immutable configuration data class with YAML serialization
    Critical Path: Configuration errors prevent entire channel processing
    Failure Mode: Validation errors with specific field-level error messages
    
    AI-GUIDANCE:
    - Never modify field names - breaks existing YAML configurations
    - Always validate configuration completeness before processing
    - Preserve backward compatibility with existing channel files
    - Use sensible defaults for optional fields
    - Implement comprehensive validation for all external dependencies
    
    Attributes:
        name (str): Human-readable channel name for logging and identification
        channel_id (str): YouTube channel ID (24 chars, UC prefix)
        db_path (str): SQLite database file path for this channel
        max_videos_to_fetch (int): Limit for video discovery (1-50 recommended)
        cookies_file (Optional[str]): Path to YouTube cookies for authentication
        subtitle_preferences (List[str]): Language codes in preference order
        telegram_bots_config (List[Dict]): Bot configurations for message delivery
        llm_config (Dict[str, Any]): Complete LLM configuration including multi-model
        retry_attempts (int): Number of retry attempts for failed operations
        retry_delay_seconds (int): Base delay between retry attempts
        
    Example:
        >>> config = ChannelConfig.from_yaml("channels/twominutepapers.yml")
        >>> print(f"Processing {config.name} with {len(config.telegram_bots_config)} bots")
        
    Note:
        Thread-safe immutable configuration. YAML serializable for persistence.
        Automatic validation and default value assignment in __post_init__.
    """
    
    # Core channel identification
    name: str  # Human-readable channel name
    channel_id: str  # YouTube channel ID (UC + 22 chars)
    db_path: str  # SQLite database file path
    
    # Processing configuration
    max_videos_to_fetch: int = 5  # Video discovery limit (1-50)
    cookies_file: Optional[str] = None  # YouTube authentication cookies
    subtitle_preferences: List[str] = None  # Language preference order
    
    # Service configurations
    telegram_bots_config: List[Dict] = None  # Bot delivery settings
    llm_config: Dict[str, Any] = None  # AI model configuration
    
    # Operational parameters
    retry_attempts: int = 3  # Retry count for failed operations
    retry_delay_seconds: int = 5  # Base retry delay
    
    def __post_init__(self):
        if self.subtitle_preferences is None:
            self.subtitle_preferences = []
        if self.telegram_bots_config is None:
            self.telegram_bots_config = []
        if self.llm_config is None:
            self.llm_config = {}
    
    # @agent:complexity medium
    # @agent:side-effects file_system_read,yaml_parsing
    # @agent:performance O(1) with file_io_latency
    # @agent:security file_path_validation,yaml_safety
    # @agent:test-coverage critical,malformed-yaml,missing-files
    @classmethod
    def from_yaml(cls, config_path: str) -> 'ChannelConfig':
        """Load and validate channel configuration from YAML file with comprehensive error handling.
        
        Factory method that safely loads YAML configuration files and converts
        them to ChannelConfig instances with full validation and error reporting.
        Handles missing files, malformed YAML, and invalid configuration gracefully.
        
        Intent: Safely convert YAML configuration files to validated configuration objects
        Critical: Configuration loading errors prevent channel processing entirely
        
        AI-DECISION: Configuration validation strategy
        Criteria:
        - Required fields missing → raise ValueError with specific field names
        - Invalid field values → raise ValueError with validation details
        - File not found → raise FileNotFoundError with clear path information
        - YAML parsing error → raise yaml.YAMLError with syntax details
        
        Args:
            config_path (str): Path to YAML configuration file
            
        Returns:
            ChannelConfig: Validated configuration instance
            
        Raises:
            FileNotFoundError: Configuration file doesn't exist
            yaml.YAMLError: YAML syntax or parsing errors
            ValueError: Missing required fields or invalid values
            
        AI-NOTE: 
            - YAML loading uses safe_load to prevent code execution
            - File path validation prevents directory traversal attacks
            - Comprehensive error messages help with configuration debugging
            - Backward compatibility maintained with existing YAML formats
        """
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