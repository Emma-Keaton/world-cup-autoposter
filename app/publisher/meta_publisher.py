"""
Meta (Instagram/Facebook) Graph API publisher.
Posts Reels to Instagram Business accounts.
"""
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from app.core.config import settings


class MetaPublisher:
    """
    Instagram Reels publisher using Meta Graph API.
    
    Requires:
    - Meta Access Token with pages_manage_posts, pages_read_engagement
    - Instagram Business Account ID
    """
    
    def __init__(self):
        """Initialize Meta publisher."""
        self.access_token = settings.META_ACCESS_TOKEN
        self.account_id = settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
        self.base_url = "https://graph.facebook.com/v19.0"
    
    async def publish_reel(
        self,
        video_path: str,
        caption: str,
        share_to_feed: bool = True,
    ) -> Optional[str]:
        """
        Publish a Reel to Instagram.
        
        Args:
            video_path: Path to video file
            caption: Caption text
            share_to_feed: Also share to main feed
            
        Returns:
            Published media ID or None
        """
        if not self.access_token or not self.account_id:
            logger.warning("Meta API credentials not configured")
            return None
        
        try:
            # Step 1: Create media container
            container_id = await self._create_media_container(
                video_path=video_path,
                caption=caption,
                share_to_feed=share_to_feed,
            )
            
            if not container_id:
                return None
            
            # Step 2: Publish the container
            media_id = await self._publish_container(container_id)
            
            if media_id:
                logger.info(f"Published Instagram Reel: {media_id}")
            
            return media_id
            
        except Exception as e:
            logger.error(f"Failed to publish Instagram Reel: {e}")
            return None
    
    async def _create_media_container(
        self,
        video_path: str,
        caption: str,
        share_to_feed: bool
    ) -> Optional[str]:
        """Create media container for upload."""
        
        # Upload video to get video ID
        video_id = await self._upload_video(video_path)
        
        if not video_id:
            return None
        
        # Create reel container
        url = f"{self.base_url}/{self.account_id}/media"
        
        params = {
            "access_token": self.access_token,
            "media_type": "REELS",
            "video_id": video_id,
            "caption": caption,
            "share_to_feed": share_to_feed,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Failed to create container: {response.text}")
                return None
            
            data = response.json()
            return data.get("id")
    
    async def _upload_video(self, video_path: str) -> Optional[str]:
        """Upload video to Facebook and get video ID."""
        
        # Use chunked upload for large videos
        url = f"{self.base_url}/{self.account_id}/videos"
        
        params = {
            "access_token": self.access_token,
            "upload_phase": "start",
            "file_size": Path(video_path).stat().st_size,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Start upload session
            response = await client.post(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Failed to start upload: {response.text}")
                return None
            
            session_data = response.json()
            upload_id = session_data.get("upload_id")
            upload_url = session_data.get("upload_url")
        
        # Upload video data
        with open(video_path, "rb") as f:
            video_data = f.read()
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                upload_url,
                data=video_data,
                headers={"Content-Type": "video/mp4"},
            )
        
        # Finish upload
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/{self.account_id}/videos",
                params={
                    "access_token": self.access_token,
                    "upload_phase": "finish",
                    "upload_id": upload_id,
                },
            )
        
        if response.status_code != 200:
            logger.error(f"Failed to finish upload: {response.text}")
            return None
        
        data = response.json()
        return data.get("id")
    
    async def _publish_container(self, container_id: str) -> Optional[str]:
        """Publish the media container."""
        url = f"{self.base_url}/{self.account_id}/media_publish"
        
        params = {
            "access_token": self.access_token,
            "creation_id": container_id,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Failed to publish: {response.text}")
                return None
            
            data = response.json()
            return data.get("id")
    
    async def get_media_status(self, media_id: str) -> Dict[str, Any]:
        """
        Get publishing status for a media item.
        
        Args:
            media_id: Media ID from publish_reel
            
        Returns:
            Status dictionary with processing status and metrics
        """
        url = f"{self.base_url}/{media_id}"
        
        params = {
            "access_token": self.access_token,
            "fields": "status_code,like_count,comments_count,timestamp",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return {"error": response.text}
            
            return response.json()
    
    async def get_insights(
        self,
        media_id: str,
        metric: str = "plays"
    ) -> Optional[int]:
        """
        Get insight metric for a media item.
        
        Args:
            media_id: Media ID
            metric: Metric name (plays, likes, comments, shares, saves)
            
        Returns:
            Metric value or None
        """
        url = f"{self.base_url}/{media_id}/insights"
        
        params = {
            "access_token": self.access_token,
            "metric": metric,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            values = data.get("data", [])
            
            if values:
                return values[0].get("values", [{}])[0].get("value")
        
        return None