"""
Services module.
Contains business logic services like notifications, error handling, etc.
"""
from app.services.whatsapp_notifier import (
    WhatsAppNotifier,
    MessagePriority,
    get_notifier,
    initialize_whatsapp,
    send_test_whatsapp,
)
from app.services.error_notifier import (
    ErrorNotifier,
    ErrorSeverity,
    get_error_notifier,
    notify_error,
    with_error_notification,
)

__all__ = [
    # WhatsApp
    "WhatsAppNotifier",
    "MessagePriority",
    "get_notifier",
    "initialize_whatsapp",
    "send_test_whatsapp",
    
    # Error Notifier
    "ErrorNotifier",
    "ErrorSeverity",
    "get_error_notifier",
    "notify_error",
    "with_error_notification",
]