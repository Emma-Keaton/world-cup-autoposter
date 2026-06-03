"""
Buffer API Publisher for real social media posting.
Supports Instagram, YouTube, Twitter, LinkedIn, and Facebook.
"""
import aiohttp
from typing import Dict, Optional, List
from datetime import datetime
from loguru import logger

from app.core.config import settings
from app.services.error_notifier import notify_error, ErrorSeverity
from app.core.rate_limiter import check_rate_limit, RateLimitExceeded
from app.core.retry import with_retry


class BufferPublisher:
    """
    Real publisher using Buffer API.
    
    Buffer (https://buffer.com) provides a simpler API than direct
    platform APIs and supports multiple social networks.
    
    Features:
    - Multi-platform posting
    - Scheduling support
    - Media upload
    - Analytics integration
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'BUFFER_API_KEY', '')
        self.api_base = "https://api.buffer.com/1"
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("Buffer API not configured - publisher will be disabled")
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @with_retry(max_attempts=3, delay=2, backoff=2, alert_on_final_failure=True)
    async def create_update(
        self,
        text: str,
        profile_ids: List[str],
        media_urls: Optional[List[str]] = None,
        scheduled_at: Optional[datetime] = None,
        now: bool = True
    ) -> Dict:
        """
        Create an update (post) on Buffer.
        
        Args:
            text: Post text/caption
            profile_ids: List of Buffer profile IDs to post to
            media_urls: Optional media URLs (images/videos)
            scheduled_at: Optional datetime to schedule (if not now)
            now: Whether to post immediately
        
        Returns:
            Response from Buffer API
        """
        if not self.enabled:
            return {"success": False, "error": "Buffer API not configured"}
        
        # Rate limiting
        try:
            check_rate_limit("publishing")
        except RateLimitExceeded as e:
            logger.warning(f"Rate limited: {e}")
            return {"success": False, "error": str(e)}
        
        session = await self._get_session()
        
        payload = {
            "text": text,
            "profile_ids": profile_ids,
            "now": now,
        }
        
        if media_urls:
            payload["media"] = [{"url": url} for url in media_urls]
        
        if scheduled_at and not now:
            payload["scheduled_at"] = int(scheduled_at.timestamp())
        
        try:
            async with session.post(
                f"{self.api_base}/updates/create.json",
                json=payload
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    logger.info(f"Buffer update created: {result.get('id')}")
                    return {"success": True, "data": result}
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Buffer API error: {error_msg}")
                    
                    # Send WhatsApp alert for API errors
                    await notify_error(
                        error=Exception(f"Buffer API: {error_msg}"),
                        severity=ErrorSeverity.HIGH,
                        context="buffer_publish",
                        extra_info={"status": response.status, "text": text[:50]}
                    )
                    
                    return {"success": False, "error": error_msg}
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            raise  # Will trigger retry
    
    async def get_profiles(self) -> List[Dict]:
        """Get connected social media profiles."""
        if not self.enabled:
            return []
        
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.api_base}/profiles.json") as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("profiles", [])
        except Exception as e:
            logger.error(f"Failed to get profiles: {e}")
        
        return []
    
    async def schedule_post(
        self,
        text: str,
        platform: str,
        media_url: Optional[str] = None,
        publish_time: Optional[datetime] = None
    ) -> Dict:
        """
        Schedule a post for a specific time.
        
        Args:
            text: Post content
            platform: Target platform (instagram, youtube, twitter, etc.)
            media_url: Optional media URL
            publish_time: When to publish
        
        Returns:
            Result with scheduled time
        """
        # Get profile ID for platform
        profiles = await self.get_profiles()
        profile = next((p for p in profiles if p.get("service") == platform), None)
        
        if not profile:
            return {
                "success": False,
                "error": f"No {platform} profile connected to Buffer"
            }
        
        # Create scheduled update
        result = await self.create_update(
            text=text,
            profile_ids=[profile["id"]],
            media_urls=[media_url] if media_url else None,
            scheduled_at=publish_time,
            now=False
        )
        
        if result["success"]:
            logger.info(f"Scheduled {platform} post for {publish_time}")
        
        return result
    
    async def publish_now(
        self,
        text: str,
        platforms: List[str],
        media_url: Optional[str] = None
    ) -> Dict:
        """
        Publish immediately to multiple platforms.
        
        Args:
            text: Post content
            platforms: List of platforms to post to
            media_url: Optional media URL
        
        Returns:
            Publish result
        """
        profiles = await self.get_profiles()
        profile_ids = [
            p["id"] for p in profiles
            if p.get("service") in platforms
        ]
        
        if not profile_ids:
            return {
                "success": False,
                "error": "No connected profiles for requested platforms"
            }
        
        return await self.create_update(
            text=text,
            profile_ids=profile_ids,
            media_urls=[media_url] if media_url else None,
            now=True
        )
    
    async def get_scheduled_posts(self) -> List[Dict]:
        """Get list of scheduled posts."""
        if not self.enabled:
            return []
        
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.api_base}/updates/scheduled.json") as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("updates", [])
        except Exception as e:
            logger.error(f"Failed to get scheduled posts: {e}")
        
        return []
    
    async def get_analytics(self, update_id: str) -> Dict:
        """Get analytics for a specific update."""
        if not self.enabled:
            return {}
        
        session = await self._get_session()
        
        try:
            async with session.get(
                f"{self.api_base}/updates/{update_id}/shares.json"
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
        
        return {}


# Global instance
_buffer_publisher: Optional[BufferPublisher] = None


def get_buffer_publisher() -> BufferPublisher:
    """Get the global Buffer publisher instance."""
    global _buffer_publisher
    if _buffer_publisher is None:
        _buffer_publisher = BufferPublisher()
    return _buffer_publisher