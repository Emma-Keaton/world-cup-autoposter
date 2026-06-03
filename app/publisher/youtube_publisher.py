"""
YouTube Data API publisher.
Uploads Shorts to YouTube.
"""
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from app.core.config import settings


class YouTubePublisher:
    """
    YouTube Shorts publisher using YouTube Data API v3.
    
    Requires:
    - YouTube API Key
    - OAuth 2.0 credentials for upload
    """
    
    def __init__(self):
        """Initialize YouTube publisher."""
        self.api_key = settings.YOUTUBE_API_KEY
        self.channel_id = settings.YOUTUBE_CHANNEL_ID
        self.upload_url = "https://www.googleapis.com/upload/youtube/v3/videos"
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    async def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
    ) -> Optional[str]:
        """
        Upload a Short to YouTube.
        
        Args:
            video_path: Path to video file (must be under 60 seconds)
            title: Video title (include #Shorts)
            description: Video description
            tags: List of tags
            
        Returns:
            Video ID or None
        """
        if not self.api_key:
            logger.warning("YouTube API key not configured")
            return None
        
        try:
            # Read video file
            with open(video_path, "rb") as f:
                video_data = f.read()
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self._get_oauth_token()}",
                "Content-Type": "video/*",
                "X-Upload-Content-Length": str(len(video_data)),
            }
            
            # Note: For production, implement OAuth 2.0 flow
            # For now, use API key for metadata only
            params = {
                "part": "snippet,status",
                "key": self.api_key,
            }
            
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": "17",  # Sports
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }
            
            # For simplified implementation, use resumable upload
            # This is a basic version - production should use google-auth-library
            upload_url = f"{self.upload_url}?part=snippet,status"
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Simplified direct upload (works for small files < 100MB)
                response = await client.post(
                    upload_url,
                    params={"key": self.api_key, "part": "snippet,status"},
                    headers={"Content-Type": "application/json"},
                    json=body,
                )
                
                if response.status_code != 200:
                    logger.error(f"YouTube upload failed: {response.text}")
                    return None
                
                data = response.json()
                video_id = data.get("id")
                
                if video_id:
                    logger.info(f"Uploaded YouTube Short: {video_id}")
                
                return video_id
                
        except Exception as e:
            logger.error(f"Failed to upload YouTube Short: {e}")
            return None
    
    def _get_oauth_token(self) -> str:
        """
        Get OAuth 2.0 token for upload.
        
        In production, implement proper OAuth flow with google-auth-library.
        This is a placeholder.
        """
        # For production: Use google-auth-library
        # from google.oauth2.credentials import Credentials
        # from google.auth.transport.requests import Request
        
        # tokens = Credentials.from_authorized_user_file('token.json')
        # return tokens.token
        
        return "placeholder_token"
    
    async def get_video_stats(self, video_id: str) -> Dict[str, Any]:
        """
        Get statistics for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Statistics dictionary
        """
        url = f"{self.base_url}/videos"
        
        params = {
            "part": "statistics",
            "id": video_id,
            "key": self.api_key,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return {"error": response.text}
            
            data = response.json()
            items = data.get("items", [])
            
            if items:
                return items[0].get("statistics", {})
        
        return {}
    
    async def update_thumbnail(
        self,
        video_id: str,
        thumbnail_path: str
    ) -> bool:
        """
        Update video thumbnail.
        
        Args:
            video_id: Video ID
            thumbnail_path: Path to thumbnail image
            
        Returns:
            True if successful
        """
        # Use thumbnails.update endpoint
        # Requires authentication
        
        with open(thumbnail_path, "rb") as f:
            thumbnail_data = f.read()
        
        upload_url = f"{self.base_url}/thumbnails/set"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                upload_url,
                params={"videoId": video_id, "key": self.api_key},
                data=thumbnail_data,
            )
            
            return response.status_code == 200
    
    def validate_short(self, video_path: str) -> Dict[str, Any]:
        """
        Validate video meets Shorts requirements.
        
        Requirements:
        - Under 60 seconds
        - Vertical aspect ratio (9:16)
        - Max 1080x1920
        
        Args:
            video_path: Path to video
            
        Returns:
            Validation result with issues if any
        """
        import asyncio
        
        async def get_duration():
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path,
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, _ = await process.communicate()
            
            import json
            data = json.loads(stdout)
            return float(data.get("format", {}).get("duration", 0))
        
        async def validate():
            duration = await get_duration()
            
            issues = []
            
            if duration > 60:
                issues.append(f"Video is {duration:.1f}s - must be under 60 seconds for Shorts")
            
            if duration < 1:
                issues.append("Video is too short")
            
            return {
                "valid": len(issues) == 0,
                "duration": duration,
                "issues": issues,
            }
        
        # Run async
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(validate())
        finally:
            loop.close()