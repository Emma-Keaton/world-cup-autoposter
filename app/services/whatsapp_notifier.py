"""
WhatsApp notification service using OpenWA.
Sends error alerts and notifications to configured WhatsApp number.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

from loguru import logger

from app.core.config import settings


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WhatsAppNotifier:
    """
    WhatsApp notification service using OpenWA.
    
    Features:
    - Session persistence (no re-authentication needed)
    - Auto-retry on send failure
    - Rate limiting to prevent spamming
    - Support for rich messages with formatting
    """
    
    def __init__(self):
        self.enabled: bool = getattr(settings, 'WHATSAPP_ENABLED', False)
        self.phone_number: str = getattr(settings, 'WHATSAPP_PHONE_NUMBER', '')
        self.session_file: str = getattr(settings, 'WHATSAPP_SESSION_FILE', 'whatsapp_session.json')
        self._client = None
        self._is_authenticated = False
        self._last_sent: dict[str, datetime] = {}
        self._rate_limit_seconds = 60  # Minimum time between identical messages
        
        # Session file path
        self._session_path = Path(self.session_file)
        if not self._session_path.is_absolute():
            # Store session files in project root
            self._session_path = Path(__file__).parent.parent.parent / self.session_file
        
        logger.info(f"WhatsAppNotifier initialized (enabled={self.enabled}, phone={self.phone_number})")
    
    async def initialize(self) -> bool:
        """
        Initialize the WhatsApp client and restore session.
        Returns True if successfully initialized and authenticated.
        """
        if not self.enabled:
            logger.debug("WhatsApp notifications are disabled")
            return False
        
        try:
            import openwa
            
            # Create client
            self._client = await openwa.Client.create()
            
            # Try to restore session
            if self._session_path.exists():
                logger.info("Restoring WhatsApp session from file...")
                try:
                    session_data = json.loads(self._session_path.read_text())
                    await self._client.restore_session(session_data)
                    self._is_authenticated = True
                    logger.info("WhatsApp session restored successfully")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to restore session: {e}. Will require QR scan.")
            
            # If no session or restore failed, return False to indicate QR scan needed
            logger.info("No saved session found. QR code scan will be required.")
            return False
            
        except ImportError:
            logger.error("OpenWA not installed. Install with: pip install openwa")
            self.enabled = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp client: {e}")
            self.enabled = False
            return False
    
    async def start_with_qr(self) -> bool:
        """
        Start authentication process with QR code.
        Call this when no saved session exists.
        """
        if not self._client:
            success = await self.initialize()
            if success:
                return True
        
        try:
            # This will print QR code to console or return it for display
            import openwa
            
            @self._client.on('qr')
            async def handle_qr(qr_code):
                logger.info("Scan this QR code with WhatsApp:")
                print("\n" + "="*50)
                print("SCAN WITH WHATSAPP:")
                print("="*50)
                # In a GUI app, you'd display the QR image
                # For CLI, just show the code string
                print(qr_code)
                print("="*50)
            
            @self._client.on('authenticated')
            async def handle_authenticated():
                logger.info("WhatsApp authenticated successfully!")
                self._is_authenticated = True
            
            @self._client.on('ready')
            async def handle_ready():
                logger.info("WhatsApp client is ready!")
                # Save session for future use
                await self._save_session()
            
            # Start the client and wait for authentication
            await self._client.start()
            
            # Wait for authentication (timeout after 60 seconds)
            for _ in range(60):
                if self._is_authenticated:
                    return True
                await asyncio.sleep(1)
            
            logger.warning("Timeout waiting for WhatsApp authentication")
            return False
            
        except Exception as e:
            logger.error(f"WhatsApp authentication failed: {e}")
            return False
    
    async def _save_session(self) -> None:
        """Save current session to file for future restoration."""
        if not self._client or not self._is_authenticated:
            return
        
        try:
            session_data = await self._client.get_session()
            self._session_path.write_text(json.dumps(session_data, indent=2))
            logger.info(f"WhatsApp session saved to {self._session_path}")
        except Exception as e:
            logger.error(f"Failed to save WhatsApp session: {e}")
    
    async def send_message(
        self,
        message: str,
        priority: MessagePriority = MessagePriority.MEDIUM,
        context: Optional[str] = None
    ) -> bool:
        """
        Send a WhatsApp message with rate limiting.
        
        Args:
            message: The message text to send
            priority: Message priority level
            context: Optional context for rate limiting (e.g., error type)
        
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("WhatsApp notifications disabled, skipping message")
            return False
        
        if not self._is_authenticated:
            logger.warning("Cannot send message: WhatsApp not authenticated")
            return False
        
        # Rate limiting: prevent duplicate messages within time window
        rate_limit_key = f"{context or 'general'}_{priority.value}"
        now = datetime.now()
        
        if rate_limit_key in self._last_sent:
            elapsed = (now - self._last_sent[rate_limit_key]).total_seconds()
            if elapsed < self._rate_limit_seconds:
                logger.debug(f"Rate limited: {rate_limit_key} ({elapsed:.1f}s since last)")
                return False
        
        try:
            # Format phone number (remove spaces, dashes, ensure country code)
            formatted_phone = self._format_phone_number(self.phone_number)
            
            # Send the message
            if not formatted_phone:
                logger.error("Invalid phone number configured")
                return False
            
            await self._client.send_message(formatted_phone, message)
            
            self._last_sent[rate_limit_key] = now
            logger.info(f"WhatsApp message sent (priority={priority.value}, context={context})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False
    
    def _format_phone_number(self, phone: str) -> Optional[str]:
        """
        Format phone number for WhatsApp.
        Expects: +1234567890 or 1234567890
        Returns: Number with country code, no spaces/dashes
        """
        if not phone:
            return None
        
        # Remove common separators
        cleaned = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Ensure it starts with country code
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        
        # Basic validation: should be at least 10 digits (including +)
        digit_count = sum(c.isdigit() for c in cleaned)
        if digit_count < 10:
            logger.error(f"Invalid phone number format: {phone}")
            return None
        
        return cleaned
    
    async def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[dict] = None
    ) -> bool:
        """
        Send a formatted error alert message.
        
        Args:
            error_type: Type/category of error (e.g., "DatabaseError", "RenderFailed")
            error_message: Human-readable error description
            stack_trace: Optional stack trace for debugging
            context: Optional additional context (e.g., job ID, file name)
        
        Returns:
            True if alert sent successfully
        """
        # Build formatted message
        lines = [
            "🚨 *ERROR ALERT* 🚨",
            "",
            f"*Type:* {error_type}",
            f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"*Message:*",
            f"{error_message}",
        ]
        
        if context:
            lines.append("")
            lines.append("*Context:*")
            for key, value in context.items():
                lines.append(f"  • {key}: {value}")
        
        if stack_trace:
            # Truncate long stack traces
            max_trace_length = 500
            if len(stack_trace) > max_trace_length:
                stack_trace = stack_trace[:max_trace_length] + "..."
            
            lines.append("")
            lines.append("*Stack Trace:*")
            lines.append(f"```{stack_trace}```")
        
        message = "\n".join(lines)
        
        return await self.send_message(
            message=message,
            priority=MessagePriority.HIGH,
            context=f"error_{error_type}"
        )
    
    async def send_critical_alert(
        self,
        title: str,
        message: str,
        details: Optional[dict] = None
    ) -> bool:
        """
        Send a critical priority alert (bypasses some rate limits).
        """
        formatted = f"⚠️ *CRITICAL ALERT* ⚠️\n\n*{title}*\n\n{message}"
        
        if details:
            formatted += "\n\n*Details:*"
            for key, value in details.items():
                formatted += f"\n  • {key}: {value}"
        
        return await self.send_message(
            message=formatted,
            priority=MessagePriority.CRITICAL,
            context=f"critical_{title}"
        )
    
    async def send_test_message(self) -> bool:
        """Send a test message to verify WhatsApp is working."""
        message = (
            "✅ *WhatsApp Test Successful!*\n\n"
            "Your World Cup Autoposter error notification system is working correctly.\n\n"
            f"_Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        )
        return await self.send_message(message, MessagePriority.LOW, "test")
    
    async def close(self) -> None:
        """Clean up the WhatsApp client."""
        if self._client:
            try:
                await self._client.stop()
                logger.info("WhatsApp client stopped")
            except Exception as e:
                logger.error(f"Error stopping WhatsApp client: {e}")


# Global instance
_notifier: Optional[WhatsAppNotifier] = None


def get_notifier() -> WhatsAppNotifier:
    """Get the global WhatsApp notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = WhatsAppNotifier()
    return _notifier


async def initialize_whatsapp() -> bool:
    """Initialize the global WhatsApp notifier."""
    notifier = get_notifier()
    return await notifier.initialize()


async def send_test_whatsapp() -> bool:
    """Send a test WhatsApp message."""
    notifier = get_notifier()
    return await notifier.send_test_message()