"""
Retry utilities with WhatsApp error notifications.
Provides automatic retry logic with exponential backoff and WhatsApp alerts on final failure.
"""
import asyncio
import functools
from typing import Optional, Callable, Any, Type, Tuple
from loguru import logger

from app.services.error_notifier import ErrorSeverity, notify_error


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, last_error: Exception, attempts: int):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    alert_on_final_failure: bool = True,
    alert_severity: ErrorSeverity = ErrorSeverity.HIGH,
    context: Optional[str] = None,
    retry_callback: Optional[Callable[[Exception, int], Any]] = None,
):
    """
    Decorator for automatic retry with exponential backoff and WhatsApp alerts.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Exponential backoff multiplier (default: 2.0)
        max_delay: Maximum delay between retries (default: None, no limit)
        exceptions: Tuple of exception types to catch and retry on
        alert_on_final_failure: Whether to send WhatsApp alert when all retries exhausted
        alert_severity: Severity level for the WhatsApp alert
        context: Context string for the alert (defaults to function name)
        retry_callback: Optional callback called after each failed attempt 
                       (receives exception and attempt number)
    
    Usage:
        @with_retry(max_attempts=3, delay=5, backoff=2)
        async def fetch_data():
            # This will retry up to 3 times with 5s, 10s, 20s delays
            ...
        
        @with_retry(
            max_attempts=5,
            delay=1,
            alert_on_final_failure=True,
            alert_severity=ErrorSeverity.CRITICAL,
            context="youtube_upload"
        )
        async def upload_to_youtube():
            # Will send WhatsApp alert after 5 failed attempts
            ...
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_error: Optional[Exception] = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                
                except exceptions as e:
                    last_error = e
                    
                    # Log the failed attempt
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}"
                    )
                    
                    # Call retry callback if provided
                    if retry_callback:
                        try:
                            retry_callback(e, attempt)
                        except Exception as cb_error:
                            logger.error(f"Retry callback error: {cb_error}")
                    
                    # If this was the last attempt, break and raise
                    if attempt == max_attempts:
                        logger.error(
                            f"All {max_attempts} attempts exhausted for {func.__name__}"
                        )
                        break
                    
                    # Wait before next attempt (with optional max_delay cap)
                    actual_delay = min(current_delay, max_delay) if max_delay else current_delay
                    logger.info(f"Retrying {func.__name__} in {actual_delay:.1f}s...")
                    await asyncio.sleep(actual_delay)
                    
                    # Exponential backoff
                    current_delay *= backoff
            
            # All retries exhausted
            error_context = context or func.__name__
            
            if alert_on_final_failure and last_error:
                # Send WhatsApp alert
                try:
                    await notify_error(
                        error=last_error,
                        severity=alert_severity,
                        context=f"retry_exhausted:{error_context}",
                        extra_info={
                            "function": func.__name__,
                            "attempts": max_attempts,
                            "total_time": f"{sum(delay * (backoff ** i) for i in range(max_attempts)):.1f}s"
                        }
                    )
                except Exception as notification_error:
                    logger.error(f"Failed to send retry failure alert: {notification_error}")
            
            # Raise the final error
            raise RetryError(
                f"Failed {func.__name__} after {max_attempts} attempts",
                last_error=last_error,
                attempts=max_attempts
            )
        
        return wrapper
    return decorator


def with_sync_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    alert_on_final_failure: bool = True,
    alert_severity: ErrorSeverity = ErrorSeverity.HIGH,
    context: Optional[str] = None,
):
    """
    Sync version of with_retry decorator.
    Use for synchronous functions that need retry logic.
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_error: Optional[Exception] = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}")
                    
                    if attempt == max_attempts:
                        logger.error(f"All {max_attempts} attempts exhausted for {func.__name__}")
                        break
                    
                    actual_delay = min(current_delay, max_delay) if max_delay else current_delay
                    logger.info(f"Retrying {func.__name__} in {actual_delay:.1f}s...")
                    asyncio.get_event_loop().run_until_complete(asyncio.sleep(actual_delay))
                    current_delay *= backoff
            
            # All retries exhausted
            error_context = context or func.__name__
            
            if alert_on_final_failure and last_error:
                # Send WhatsApp alert (run in event loop)
                try:
                    asyncio.get_event_loop().run_until_complete(notify_error(
                        error=last_error,
                        severity=alert_severity,
                        context=f"retry_exhausted:{error_context}",
                        extra_info={
                            "function": func.__name__,
                            "attempts": max_attempts,
                        }
                    ))
                except Exception as notification_error:
                    logger.error(f"Failed to send retry failure alert: {notification_error}")
            
            raise RetryError(
                f"Failed {func.__name__} after {max_attempts} attempts",
                last_error=last_error,
                attempts=max_attempts
            )
        
        return wrapper
    return decorator