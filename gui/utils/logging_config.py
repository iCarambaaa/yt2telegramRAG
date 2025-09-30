"""
Logging configuration for the Unified GUI Platform.

Uses Rich for enhanced terminal output with structured logging.
"""

import logging
import sys
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install

# Install rich traceback handler
install(show_locals=True)

# Create console for rich output
console = Console()

# Configure logging levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


def setup_logging(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up structured logging with Rich formatting.
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Get log level from environment or default to INFO
    import os
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(LOG_LEVELS.get(log_level, logging.INFO))
    
    # Create Rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True
    )
    
    # Set formatter
    formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt="[%X]"
    )
    rich_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(rich_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get existing logger or create new one."""
    return logging.getLogger(name)


# Configure root logger for the application
def configure_app_logging():
    """Configure application-wide logging settings."""
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add Rich handler to root
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True
    )
    
    formatter = logging.Formatter(
        fmt="%(name)s: %(message)s",
        datefmt="[%X]"
    )
    rich_handler.setFormatter(formatter)
    
    root_logger.addHandler(rich_handler)
    
    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("websockets").setLevel(logging.WARNING)


# Initialize app logging when module is imported
configure_app_logging()