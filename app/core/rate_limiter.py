"""
Rate Limiter service for API protection and anti-ban measures.
Prevents abuse and protects social media accounts from rate limits.
"""
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from loguru import logger

from app.services.error_notifier import notify_error, ErrorSeverity


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, limit_type: str, retry_after: float):
        self.limit_type = limit_type
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {limit_type}. Retry after {retry_after:.1f}s")


class RateLimiter:
    """
    Token bucket rate limiter with multiple bucket support.
    
    Features:
    - Multiple rate limit buckets (e.g., Instagram, YouTube, Scraping)
    - Configurable limits per bucket
    - Automatic cleanup of old entries
    - WhatsApp alerts on repeated violations
    """
    
    def __init__(self):
        # Default limits
        self.limits: Dict[str, Tuple[int, int]] = {
            "instagram": (50, 3600),      # 50 requests per hour
            "youtube": (100, 3600),       # 100 requests per hour
            "scraping": (10, 600),        # 10 requests per 10 minutes
            "publishing": (20, 3600),     # 20 posts per hour
            "api_general": (1000, 3600),  # 1000 API requests per hour
        }
        
        # Token buckets: {key: (tokens, last_update)}
        self._buckets: Dict[str, Tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))
        
        # Violation tracking
        self._violations: Dict[str, list] = defaultdict(list)
        self._max_violations_before_alert = 5
        
        logger.info("RateLimiter initialized with default limits")
    
    def configure_limit(self, limit_type: str, calls: int, period_seconds: int) -> None:
        """
        Configure a rate limit for a specific type.
        
        Args:
            limit_type: Type of limit (e.g., "instagram", "youtube")
            calls: Maximum number of calls allowed
            period_seconds: Time period in seconds
        """
        self.limits[limit_type] = (calls, period_seconds)
        logger.info(f"Rate limit configured: {limit_type} = {calls} calls / {period_seconds}s")
    
    def acquire(self, limit_type: str, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to acquire tokens from the bucket.
        
        Args:
            limit_type: Type of rate limit
            tokens: Number of tokens to acquire (default: 1)
        
        Returns:
            Tuple of (success, wait_time_if_failed)
        """
        if limit_type not in self.limits:
            logger.warning(f"Unknown rate limit type: {limit_type}")
            return True, 0.0
        
        max_tokens, period = self.limits[limit_type]
        bucket_key = f"{limit_type}"
        
        now = time.time()
        
        # Get or create bucket
        current_tokens, last_update = self._buckets.get(bucket_key, (max_tokens, now))
        
        # Calculate tokens to add based on time elapsed
        elapsed = now - last_update
        tokens_to_add = (elapsed / period) * max_tokens
        current_tokens = min(max_tokens, current_tokens + tokens_to_add)
        
        # Try to acquire tokens
        if current_tokens >= tokens:
            current_tokens -= tokens
            self._buckets[bucket_key] = (current_tokens, now)
            return True, 0.0
        else:
            # Calculate wait time
            tokens_needed = tokens - current_tokens
            wait_time = (tokens_needed / max_tokens) * period
            
            # Update bucket with current state
            self._buckets[bucket_key] = (current_tokens, now)
            
            # Track violation
            self._track_violation(limit_type)
            
            return False, wait_time
    
    def _track_violation(self, limit_type: str) -> None:
        """Track rate limit violations and alert on repeated violations."""
        now = datetime.now()
        self._violations[limit_type].append(now)
        
        # Keep only violations in the last hour
        hour_ago = now - timedelta(hours=1)
        self._violations[limit_type] = [
            v for v in self._violations[limit_type]
            if v > hour_ago
        ]
        
        # Alert on repeated violations
        if len(self._violations[limit_type]) >= self._max_violations_before_alert:
            logger.warning(f"Repeated rate limit violations for {limit_type}")
            # Send WhatsApp alert
            import asyncio
            try:
                asyncio.create_task(notify_error(
                    error=RateLimitExceeded(limit_type, 0),
                    severity=ErrorSeverity.MEDIUM,
                    context=f"rate_limit_violations:{limit_type}",
                    extra_info={
                        "violations": len(self._violations[limit_type]),
                        "limit_type": limit_type,
                        "time_window": "1 hour"
                    }
                ))
            except Exception:
                pass  # Don't fail on notification errors
    
    def get_status(self, limit_type: str) -> Dict:
        """Get current rate limit status for a type."""
        if limit_type not in self.limits:
            return {"error": "Unknown limit type"}
        
        max_tokens, period = self.limits[limit_type]
        current_tokens, last_update = self._buckets.get(limit_type, (max_tokens, time.time()))
        
        # Calculate current tokens with refill
        elapsed = time.time() - last_update
        tokens_to_add = (elapsed / period) * max_tokens
        current_tokens = min(max_tokens, current_tokens + tokens_to_add)
        
        return {
            "limit_type": limit_type,
            "tokens_available": round(current_tokens, 2),
            "max_tokens": max_tokens,
            "period_seconds": period,
            " utilization_percent": round((1 - current_tokens / max_tokens) * 100, 2),
            "violations_last_hour": len(self._violations.get(limit_type, []))
        }
    
    def reset(self, limit_type: Optional[str] = None) -> None:
        """Reset rate limit buckets."""
        if limit_type:
            self._buckets[limit_type] = (self.limits.get(limit_type, (100, 3600))[0], time.time())
            self._violations[limit_type] = []
            logger.info(f"Rate limit reset for: {limit_type}")
        else:
            self._buckets.clear()
            self._violations.clear()
            logger.info("All rate limits reset")


# Global instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_rate_limit(limit_type: str, tokens: int = 1) -> bool:
    """
    Check and acquire rate limit tokens.
    Raises RateLimitExceeded if limit exceeded.
    """
    limiter = get_rate_limiter()
    success, wait_time = limiter.acquire(limit_type, tokens)
    
    if not success:
        raise RateLimitExceeded(limit_type, wait_time)
    
    return True