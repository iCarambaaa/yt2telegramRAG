import logging
import sys
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.text import Text
    from rich.style import Style
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    import logging as fallback_log


# Global variable to track if file handler has been initialized
_file_handler_initialized = False
_log_file_path = None


@dataclass
class LogConfig:
    """Configuration for logging system"""
    level: str = "info"
    component: Optional[str] = None
    enable_colors: bool = True
    enable_timestamps: bool = True


class StructuredLogger:
    """Wrapper for Rich logging functionality with fallback to standard logging"""
    
    def __init__(self, component: str, level: str = "info"):
        self.component = component
        self.level = level.lower()
        self._context = {}
        
        if RICH_AVAILABLE:
            # Configure Rich logging
            self._setup_rich_logging()
        else:
            # Fallback to standard Python logging
            self._setup_fallback_logging()
    
    def _get_or_create_file_handler(self, log_level):
        """Get or create a shared file handler for all loggers"""
        global _file_handler_initialized, _log_file_path
        
        if not _file_handler_initialized:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Create log filename with timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            _log_file_path = log_dir / f"run_{timestamp}.log"
            
            # Create file handler
            file_handler = logging.FileHandler(_log_file_path, encoding='utf-8')
            file_handler.setLevel(getattr(logging, log_level, logging.INFO))
            
            # Use detailed format for file logs
            file_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            
            _file_handler_initialized = True
            return file_handler
        else:
            # Return existing file handler
            file_handler = logging.FileHandler(_log_file_path, encoding='utf-8')
            file_handler.setLevel(getattr(logging, log_level, logging.INFO))
            file_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            return file_handler
    
    def _setup_rich_logging(self):
        """Setup Rich logging configuration"""
        # Set log level based on environment or config
        log_level = os.getenv('LOG_LEVEL', self.level).upper()
        
        # Create Rich logger
        self._rich_logger = logging.getLogger(self.component)
        
        # Convert string level to logging constant
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'WARN': logging.WARNING,
            'ERROR': logging.ERROR
        }
        
        self._rich_logger.setLevel(level_map.get(log_level, logging.INFO))
        
        # Add Rich handler if not already present
        if not any(isinstance(h, RichHandler) for h in self._rich_logger.handlers):
            console = Console()
            
            # Create a custom highlighter for semantic coloring
            from rich.highlighter import RegexHighlighter
            
            class SemanticHighlighter(RegexHighlighter):
                """Highlighter that colors specific patterns in log messages"""
                highlights = [
                    # Specific counts first (before general count pattern)
                    # Successful count in green - match until next key= or end bracket
                    r"successful_count=(?P<green>.*?)(?=\s*,\s*\w+=|\s*\])",
                    # Failed count in red - match until next key= or end bracket
                    r"failed_count=(?P<red>.*?)(?=\s*,\s*\w+=|\s*\])",
                    
                    # Channel names in red - match until next key= or end bracket
                    r"channel_name=(?P<red>.*?)(?=\s*,\s*\w+=|\])",
                    # Video titles in green - match until next key= or end bracket  
                    r"video_title=(?P<green>.*?)(?=\s*,\s*\w+=|\])",
                    # Video IDs in blue - match until next key= or end bracket
                    r"video_id=(?P<blue>.*?)(?=\s*,\s*\w+=|\])",
                    # Errors in bright red - match until next key= or end bracket
                    r"error=(?P<bright_red>.*?)(?=\s*,\s*\w+=|\])",
                    
                    # General counts in yellow (match specific count fields but not successful_count or failed_count)
                    r"(?:^|\s)(count|processed_count|max_videos|attempt|total_attempts)=(?P<yellow>.*?)(?=\s*,\s*\w+=|\s*\])",
                ]
            
            rich_handler = RichHandler(
                console=console,
                show_time=True,
                show_path=False,
                markup=False,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                highlighter=SemanticHighlighter()
            )
            rich_handler.setFormatter(logging.Formatter(
                fmt="%(message)s"
            ))
            self._rich_logger.addHandler(rich_handler)
            self._rich_logger.propagate = False
        
        # Add file handler (only once per logger)
        if not any(isinstance(h, logging.FileHandler) for h in self._rich_logger.handlers):
            file_handler = self._get_or_create_file_handler(log_level)
            self._rich_logger.addHandler(file_handler)
    
    def _setup_fallback_logging(self):
        """Setup fallback standard logging"""
        self._fallback_logger = logging.getLogger(self.component)
        
        # Convert string level to logging constant
        level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'warn': logging.WARNING,
            'error': logging.ERROR
        }
        
        log_level = os.getenv('LOG_LEVEL', self.level).lower()
        self._fallback_logger.setLevel(level_map.get(log_level, logging.INFO))
        
        # Add file handler for fallback logging too
        if not any(isinstance(h, logging.FileHandler) for h in self._fallback_logger.handlers):
            file_handler = self._get_or_create_file_handler(log_level.upper())
            self._fallback_logger.addHandler(file_handler)
    

    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context and additional fields"""
        context_parts = []
        
        # Add component context
        if self.component:
            context_parts.append(f"component={self.component}")
        
        # Add stored context
        for key, value in self._context.items():
            context_parts.append(f"{key}={value}")
        
        # Add kwargs
        for key, value in kwargs.items():
            context_parts.append(f"{key}={value}")
        
        if context_parts:
            context_str = " ".join(context_parts)
            return f"{message} [{context_str}]"
        
        return message
    

    def _format_rich_message(self, message: str, **kwargs) -> str:
        """Format message with structured data and semantic colors for Rich logging"""
        if not kwargs and not self._context:
            return message
        
        # Combine context and kwargs
        all_fields = {**self._context, **kwargs}
        
        # Disable Rich markup entirely and use simple formatting
        # Rich will still provide colors through its console, but won't break on spaces
        field_parts = []
        for key, value in all_fields.items():
            # Simple key=value format without any markup
            field_parts.append(f"{key}={value}")
        
        if field_parts:
            return f"{message} [{', '.join(field_parts)}]"
        
        return message
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        if RICH_AVAILABLE:
            formatted_msg = self._format_rich_message(message, **kwargs)
            self._rich_logger.debug(formatted_msg)
        else:
            formatted_msg = self._format_message(message, **kwargs)
            self._fallback_logger.debug(formatted_msg)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        if RICH_AVAILABLE:
            formatted_msg = self._format_rich_message(message, **kwargs)
            self._rich_logger.info(formatted_msg)
        else:
            formatted_msg = self._format_message(message, **kwargs)
            self._fallback_logger.info(formatted_msg)
    
    def warn(self, message: str, **kwargs):
        """Log warning message"""
        if RICH_AVAILABLE:
            formatted_msg = self._format_rich_message(message, **kwargs)
            self._rich_logger.warning(formatted_msg)
        else:
            formatted_msg = self._format_message(message, **kwargs)
            self._fallback_logger.warning(formatted_msg)
    
    def warning(self, message: str, **kwargs):
        """Alias for warn to maintain compatibility"""
        self.warn(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        if RICH_AVAILABLE:
            formatted_msg = self._format_rich_message(message, **kwargs)
            self._rich_logger.error(formatted_msg)
        else:
            formatted_msg = self._format_message(message, **kwargs)
            self._fallback_logger.error(formatted_msg)
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Create a new logger instance with additional context"""
        new_logger = StructuredLogger(self.component, self.level)
        new_logger._context = {**self._context, **kwargs}
        return new_logger


class LoggerFactory:
    """Factory for creating configured loggers"""
    
    _global_config: Optional[LogConfig] = None
    _loggers: Dict[str, StructuredLogger] = {}
    
    @classmethod
    def configure_global_logger(cls, config: LogConfig):
        """Configure global logger settings"""
        cls._global_config = config
        
        # Apply configuration to existing loggers
        for logger in cls._loggers.values():
            logger.level = config.level
            if RICH_AVAILABLE:
                logger._setup_rich_logging()
            else:
                logger._setup_fallback_logging()
    
    @classmethod
    def create_logger(cls, component: str, level: str = None) -> StructuredLogger:
        """Create or retrieve a logger for the given component"""
        # Use global config level if no specific level provided
        if level is None and cls._global_config:
            level = cls._global_config.level
        elif level is None:
            level = "info"
        
        # Return existing logger if already created
        logger_key = f"{component}:{level}"
        if logger_key in cls._loggers:
            return cls._loggers[logger_key]
        
        # Create new logger
        logger = StructuredLogger(component, level)
        cls._loggers[logger_key] = logger
        
        return logger


def setup_logging(level=None):
    """Setup logging configuration - maintains backward compatibility"""
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Convert logging constants to string if needed
    if isinstance(level, int):
        level_map = {
            logging.DEBUG: 'debug',
            logging.INFO: 'info',
            logging.WARNING: 'warning',
            logging.ERROR: 'error'
        }
        level = level_map.get(level, 'info')
    elif isinstance(level, str):
        level = level.lower()
    
    # Configure global logger
    config = LogConfig(level=level)
    LoggerFactory.configure_global_logger(config)
    
    # Reduce noise from external libraries if using fallback logging
    if not RICH_AVAILABLE:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('telegram').setLevel(logging.WARNING)
    
    # Return a logger for backward compatibility
    return LoggerFactory.create_logger(__name__, level)
