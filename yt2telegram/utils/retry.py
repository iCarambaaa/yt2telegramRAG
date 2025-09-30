import time
from functools import wraps
from typing import Callable, Type, Union, Tuple

from .logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

# @agent:service-type infrastructure
# @agent:scalability stateless
# @agent:persistence none
# @agent:priority critical
# @agent:dependencies logging,time_delays
def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 1.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    logger_name: str = None
):
    """Advanced retry decorator with exponential backoff and comprehensive error handling.
    
    Provides robust retry functionality for unreliable operations like API calls,
    network requests, and external service integrations. Implements configurable
    exponential backoff, selective exception handling, and detailed logging
    for production debugging and monitoring.
    
    Intent: Make unreliable operations reliable through intelligent retry strategies
    Critical: Retry logic is fundamental to system resilience - used throughout codebase
    
    AI-GUIDANCE:
    - Never modify retry parameters without understanding impact on dependent services
    - Preserve exponential backoff algorithm - prevents thundering herd problems
    - Always log retry attempts for debugging and monitoring
    - Use specific exception types rather than catching all exceptions
    - Consider rate limiting implications when setting retry parameters
    
    Decision Logic:
    1. Execute function and capture any exceptions
    2. If success → return result immediately
    3. If exception matches retry criteria → wait and retry
    4. Apply exponential backoff between attempts
    5. After max attempts → raise last exception with context
    
    AI-DECISION: Retry strategy selection
    Criteria:
    - Network errors → retry with exponential backoff
    - Authentication errors → don't retry (fail fast)
    - Rate limiting → retry with longer delays
    - Permanent errors → don't retry (fail fast)
    
    Args:
        attempts (int): Maximum retry attempts including initial try (default: 3)
        delay (float): Initial delay between retries in seconds (default: 1.0)
        backoff (float): Multiplier for delay after each attempt (default: 1.0)
        exceptions (Union[Type[Exception], Tuple]): Exception types to retry on
        logger_name (str): Custom logger name for retry events
    
    Returns:
        Callable: Decorated function with retry capability
        
    Example:
        >>> @retry(attempts=3, delay=2, backoff=1.5, exceptions=(requests.RequestException,))
        ... def api_call():
        ...     return requests.get("https://api.example.com/data")
        
    Performance:
        - No overhead on successful first attempt
        - Exponential backoff prevents system overload
        - Total retry time: sum of delays (e.g., 2s + 3s + 4.5s = 9.5s max)
        
    AI-NOTE: 
        - Exponential backoff prevents thundering herd problems
        - Specific exception handling prevents infinite retries on permanent failures
        - Logging provides visibility into retry patterns for optimization
        - Backoff multiplier should typically be 1.5-2.0 for optimal spacing
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use custom logger or function's module logger
            func_logger = LoggerFactory.create_logger(logger_name or func.__module__)
            
            current_delay = delay
            last_exception = None
            
            for attempt in range(attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log success if this wasn't the first attempt
                    if attempt > 0:
                        func_logger.info("Function succeeded on retry", function=func.__name__, attempt=attempt + 1)
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    attempt_num = attempt + 1
                    
                    if attempt_num < attempts:
                        # Not the last attempt - log warning and retry
                        func_logger.warning(
                            "Function attempt failed, retrying", 
                            function=func.__name__, 
                            attempt=attempt_num, 
                            total_attempts=attempts, 
                            error=str(e), 
                            retry_delay=current_delay
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # Last attempt failed - log error and re-raise
                        func_logger.error(
                            "Function failed after all attempts", 
                            function=func.__name__, 
                            total_attempts=attempts, 
                            final_error=str(e)
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