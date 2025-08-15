import time
import logging
from functools import wraps
from typing import Callable, Type, Union, Tuple

logger = logging.getLogger(__name__)

def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 1.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    logger_name: str = None
):
    """
    Retry decorator with configurable parameters
    
    Args:
        attempts: Number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Multiplier for delay after each attempt (default: 1.0 = no backoff)
        exceptions: Exception types to catch and retry (default: Exception)
        logger_name: Custom logger name (default: uses function's module logger)
    
    Example:
        @retry(attempts=3, delay=2, backoff=1.5)
        def risky_operation():
            # This will retry up to 3 times with delays: 2s, 3s, 4.5s
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use custom logger or function's module logger
            func_logger = logging.getLogger(logger_name or func.__module__)
            
            current_delay = delay
            last_exception = None
            
            for attempt in range(attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log success if this wasn't the first attempt
                    if attempt > 0:
                        func_logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    attempt_num = attempt + 1
                    
                    if attempt_num < attempts:
                        # Not the last attempt - log warning and retry
                        func_logger.warning(
                            f"{func.__name__} attempt {attempt_num}/{attempts} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # Last attempt failed - log error and re-raise
                        func_logger.error(
                            f"{func.__name__} failed after {attempts} attempts. "
                            f"Final error: {e}"
                        )
                        raise
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class RetryConfig:
    """Configuration class for common retry patterns"""
    
    # Network operations (HTTP requests, API calls)
    NETWORK = {
        'attempts': 3,
        'delay': 2.0,
        'backoff': 1.5,
        'exceptions': (ConnectionError, TimeoutError, OSError)
    }
    
    # File operations
    FILE_IO = {
        'attempts': 2,
        'delay': 0.5,
        'backoff': 1.0,
        'exceptions': (IOError, OSError, PermissionError)
    }
    
    # External service calls (YouTube, LLM APIs)
    EXTERNAL_API = {
        'attempts': 3,
        'delay': 5.0,
        'backoff': 2.0,
        'exceptions': Exception  # Catch all for external APIs
    }
    
    # Quick operations that should fail fast
    FAST_FAIL = {
        'attempts': 2,
        'delay': 0.1,
        'backoff': 1.0,
        'exceptions': Exception
    }

def network_retry(func: Callable) -> Callable:
    """Shorthand decorator for network operations"""
    return retry(**RetryConfig.NETWORK)(func)

def file_retry(func: Callable) -> Callable:
    """Shorthand decorator for file operations"""
    return retry(**RetryConfig.FILE_IO)(func)

def api_retry(func: Callable) -> Callable:
    """Shorthand decorator for external API calls"""
    return retry(**RetryConfig.EXTERNAL_API)(func)