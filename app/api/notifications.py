"""
Notifications API endpoints.
Test and manage WhatsApp error notifications.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.error_notifier import ErrorSeverity, notify_error, get_error_notifier
from app.services.whatsapp_notifier import MessagePriority

router = APIRouter()


class TestNotificationRequest(BaseModel):
    """Request model for testing notifications."""
    message: str = "Test notification from World Cup Autoposter"
    severity: ErrorSeverity = ErrorSeverity.LOW
    context: Optional[str] = "test_notification"


class NotificationResponse(BaseModel):
    """Response model for notification tests."""
    success: bool
    message: str
    details: Optional[str] = None


@router.post("/test", response_model=NotificationResponse)
async def test_notification(request: TestNotificationRequest) -> NotificationResponse:
    """
    Send a test notification via WhatsApp.
    
    This endpoint allows you to verify that WhatsApp notifications are working correctly.
    Set severity to LOW by default to avoid spamming yourself with alerts.
    """
    try:
        # Create a test exception
        test_error = Exception(f"TEST: {request.message}")
        
        # Send notification
        success = await notify_error(
            error=test_error,
            severity=request.severity,
            context=request.context or "test_notification"
        )
        
        return NotificationResponse(
            success=success,
            message="Test notification sent!" if success else "Notification failed",
            details=f"Severity: {request.severity.value}, Context: {request.context}"
        )
        
    except Exception as e:
        return NotificationResponse(
            success=False,
            message=f"Error sending notification: {str(e)}",
        )


@router.post("/test/whatsapp", response_model=NotificationResponse)
async def test_whatsapp_direct() -> NotificationResponse:
    """
    Send a test WhatsApp message directly (bypasses error formatting).
    
    This sends a simple "Hello World" style message to verify WhatsApp connectivity.
    """
    try:
        notifier = get_error_notifier()._whatsapp_notifier
        
        # Check if enabled
        if not notifier.enabled:
            return NotificationResponse(
                success=False,
                message="WhatsApp notifications are disabled",
                details="Enable with WHATSAPP_ENABLED=true in your .env file"
            )
        
        # Send test message
        success = await notifier.send_test_message()
        
        return NotificationResponse(
            success=success,
            message="Test message sent!" if success else "Failed to send message",
            details="Check your WhatsApp for the test message" if success else "Ensure WhatsApp is authenticated"
        )
        
    except Exception as e:
        return NotificationResponse(
            success=False,
            message=f"Error: {str(e)}",
        )


@router.get("/status", response_model=NotificationResponse)
async def notification_status() -> NotificationResponse:
    """
    Check the status of the notification service.
    """
    try:
        notifier = get_error_notifier()._whatsapp_notifier
        
        status_info = {
            "enabled": notifier.enabled,
            "authenticated": notifier._is_authenticated,
            "phone_configured": bool(notifier.phone_number),
            "session_file": notifier.session_file,
        }
        
        # Convert to string for response
        details = ", ".join(f"{k}: {v}" for k, v in status_info.items())
        
        return NotificationResponse(
            success=True,
            message="Notification service is running",
            details=details
        )
        
    except Exception as e:
        return NotificationResponse(
            success=False,
            message=f"Service error: {str(e)}",
        )


@router.post("/trigger/error/{error_type}")
async def trigger_test_error(error_type: str) -> dict:
    """
    Trigger a test error to verify error notifications work.
    
    This endpoint raises an exception intentionally to test the error
    notification system. Useful for verifying that global exception
    handlers are sending WhatsApp alerts correctly.
    
    Error types:
    - value_error: Raises ValueError
    - runtime_error: Raises RuntimeError
    - connection_error: Raises ConnectionError (HIGH severity)
    - general: Raises generic Exception
    """
    errors = {
        "value_error": ValueError("Test ValueError from /api/notifications/trigger/error/value_error"),
        "runtime_error": RuntimeError("Test RuntimeError from /api/notifications/trigger/error/runtime_error"),
        "connection_error": ConnectionError("Test ConnectionError from /api/notifications/trigger/error/connection_error"),
        "timeout_error": TimeoutError("Test TimeoutError from /api/notifications/trigger/error/timeout_error"),
        "general": Exception("Test generic Exception from /api/notifications/trigger/error/general"),
    }
    
    if error_type not in errors:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown error type: {error_type}. Available: {list(errors.keys())}"
        )
    
    # Raise the test error
    raise errors[error_type]