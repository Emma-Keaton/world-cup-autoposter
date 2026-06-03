"""
Error notification service.
Orchestrates error alerts via WhatsApp (and other channels in future).
"""
import traceback
from typing import Optional, Callable, Any
from functools import wraps
from enum import Enum
import asyncio

from loguru import logger

from app.services.whatsapp_notifier import get_notifier, MessagePriority


class ErrorSeverity(Enum):
    """Error severity levels for notification routing."""
    LOW = "low"  # Log only
    MEDIUM = "medium"  # Log + daily summary
    HIGH = "high"  # Immediate WhatsApp alert
    CRITICAL = "critical"  # Immediate WhatsApp alert + retry


class ErrorNotifier:
    """
    Centralized error notification service.
    
    Routes errors to appropriate channels based on severity:
    - LOW: Log only
    - MEDIUM: Log + daily digest
    - HIGH: Immediate WhatsApp alert
    - CRITICAL: Immediate WhatsApp alert + auto-retry logic
    """
    
    def __init__(self):
        self._whatsapp_notifier = get_notifier()
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the notification service."""
        if self._initialized:
            return True
        
        try:
            success = await self._whatsapp_notifier.initialize()
            self._initialized = True
            return success
        except Exception as e:
            logger.error(f"Failed to initialize error notifier: {e}")
            return False
    
    async def notify(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[str] = None,
        extra_info: Optional[dict] = None
    ) -> bool:
        """
        Send error notification based on severity level.
        
        Args:
            error: The exception that occurred
            severity: Error severity level
            context: Optional context (e.g., "video_render", "instagram_publish")
            extra_info: Additional context information
        
        Returns:
            True if notification was sent successfully
        """
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        # Build context dict
        context_dict = extra_info.copy() if extra_info else {}
        if context:
            context_dict['context'] = context
        
        # Route based on severity
        if severity == ErrorSeverity.LOW:
            logger.debug(f"[{error_type}] {error_message}")
            return True
        
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"[{error_type}] {error_message}")
            # TODO: Add daily digest accumulation
            return True
        
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"[{error_type}] {error_message}")
            return await self._whatsapp_notifier.send_error_alert(
                error_type=error_type,
                error_message=error_message,
                stack_trace=stack_trace,
                context=context_dict
            )
        
        elif severity == ErrorSeverity.CRITICAL:
            logger.critical(f"[{error_type}] {error_message}")
            
            # Send critical alert
            sent = await self._whatsapp_notifier.send_critical_alert(
                title=error_type,
                message=error_message,
                details=context_dict
            )
            
            # TODO: Implement auto-retry logic for critical errors
            # For now, just log
            logger.info("Critical error flagged for retry (retry logic TBD)")
            
            return sent
        
        return False
    
    def decorate(
        self,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        context: Optional[str] = None,
        extra_info: Optional[dict] = None
    ) -> Callable:
        """
        Decorator for automatic error notifications.
        
        Usage:
            @error_notifier.decorate(severity=ErrorSeverity.HIGH, context="video_render")
            async def render_video(...):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    await self.notify(
                        error=e,
                        severity=severity,
                        context=context or func.__name__,
                        extra_info=extra_info
                    )
                    raise  # Re-raise the exception
            return wrapper
            
            # For sync functions (not used in this codebase, but good to have)
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Run async notify in event loop
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(self.notify(
                        error=e,
                        severity=severity,
                        context=context or func.__name__,
                        extra_info=extra_info
                    ))
                    raise
            return sync_wrapper
        
        return decorator


# Global instance
_error_notifier: Optional[ErrorNotifier] = None


def get_error_notifier() -> ErrorNotifier:
    """Get the global error notifier instance."""
    global _error_notifier
    if _error_notifier is None:
        _error_notifier = ErrorNotifier()
    return _error_notifier


async def notify_error(
    error: Exception,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[str] = None,
    extra_info: Optional[dict] = None
) -> bool:
    """
    Convenience function to send error notification.
    
    Usage:
        try:
            some_operation()
        except Exception as e:
            await notify_error(e, severity=ErrorSeverity.HIGH, context="my_operation")
            raise
    """
    notifier = get_error_notifier()
    return await notifier.notify(error, severity, context, extra_info)


def with_error_notification(
    severity: ErrorSeverity = ErrorSeverity.HIGH,
    context: Optional[str] = None,
    extra_info: Optional[dict] = None
) -> Callable:
    """
    Decorator for automatic error notifications.
    
    Usage:
        @with_error_notification(severity=ErrorSeverity.HIGH, context="video_render")
        async def render_video(...):
            ...
    """
    notifier = get_error_notifier()
    return notifier.decorate(severity, context, extra_info)