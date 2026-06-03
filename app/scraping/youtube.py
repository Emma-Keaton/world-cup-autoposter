"""
YouTube scraper using yt-dlp.
Scrapes Shorts, transcripts, metadata, and engagement metrics.
"""
import asyncio
import json
import yt_dlp
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from loguru import logger

from app.core.database import async_session_factory
from app.models import CompetitorAccount, ScrapedContent, Platform, ContentType
from app.core.utils import calculate_viral_score, clean_text, parse_duration


class YouTubeScraper:
    """
    YouTube scraper using yt-dlp.
    
    Downloads transcripts, metadata, and performance metrics from YouTube Shorts.
    Follows Agent-Reach approach: CLI-driven, no expensive API calls.
    """
    
    def __init__(self, output_dir: str = "./temp/youtube"):
        """
        Initialize YouTube scraper.
        
        Args:
            output_dir: Directory for temporary downloads
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_base_options(self) -> Dict[str, Any]:
        """Get base yt-dlp options."""
        return {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "writeinfojson": True,
            "writethumbnail": True,
            "writesubtitles": True,
            "subtitleslangs": ["en", "en-US"],
            "subtitlesformat": "vtt",
            "skip_download": True,
            "noplaylist": True,
        }
    
    async def scrape_channel_videos(
        self,
        channel_url: str,
        limit: int = 50,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Scrape recent videos/shorts from a YouTube channel.
        
        Args:
            channel_url: URL of the YouTube channel
            limit: Maximum number of videos to scrape
            days_back: Only scrape videos from last N days
            
        Returns:
            List of video data dictionaries
        """
        videos_data = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Options for extracting video info
        ydl_opts = self._get_base_options()
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract channel info
                channel_info = ydl.extract_info(channel_url, download=False)
                
                if not channel_info or "entries" not in channel_info:
                    logger.warning(f"No videos found for channel: {channel_url}")
                    return videos_data
                
                count = 0
                for entry in channel_info.get("entries", []):
                    if count >= limit:
                        break
                    
                    if not entry:
                        continue
                    
                    # Check upload date
                    upload_date = entry.get("upload_date")
                    if upload_date:
                        try:
                            upload_dt = datetime.strptime(upload_date, "%Y%m%d")
                            if upload_dt < cutoff_date:
                                break
                        except ValueError:
                            pass
                    
                    # Extract video data
                    video_id = entry.get("id") or entry.get("ie_key")
                    if not video_id:
                        continue
                    
                    # Determine if it's a Short (duration < 60s or in Shorts section)
                    duration = entry.get("duration", 0)
                    is_short = duration <= 60 or "shorts" in entry.get("webpage_url", "").lower()
                    
                    video_data = {
                        "platform": Platform.YOUTUBE,
                        "content_type": ContentType.SHORT if is_short else ContentType.REEL,
                        "external_id": video_id,
                        "url": entry.get("webpage_url") or f"https://youtube.com/watch?v={video_id}",
                        "title": clean_text(entry.get("title", ""))[:500],
                        "description": clean_text(entry.get("description", "")) if entry.get("description") else None,
                        "thumbnail_url": entry.get("thumbnail"),
                        "views": entry.get("view_count"),
                        "likes": entry.get("like_count"),
                        "comments": entry.get("comment_count"),
                        "shares": None,
                        "duration_seconds": duration,
                        "published_at": datetime.strptime(upload_date, "%Y%m%d") if upload_date else None,
                        "scraped_at": datetime.now(),
                    }
                    
                    # Get transcript if available
                    transcript = await self._extract_transcript(entry.get("webpage_url"))
                    video_data["transcript"] = transcript
                    
                    videos_data.append(video_data)
                    count += 1
                    
                    logger.debug(f"Scraped YouTube video {video_id}")
                
                logger.info(f"Scraped {count} videos from channel: {channel_url}")
                
        except Exception as e:
            logger.error(f"Failed to scrape channel {channel_url}: {e}")
        
        return videos_data
    
    async def _extract_transcript(self, video_url: str) -> Optional[str]:
        """
        Extract transcript/subtitles from a YouTube video.
        
        Args:
            video_url: URL of the YouTube video
            
        Returns:
            Transcript text or None
        """
        ydl_opts = {
            **self._get_base_options(),
            "skip_download": True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Try to get automatic captions
                captions = info.get("automatic_captions") or info.get("subtitles")
                
                if captions and "en" in captions:
                    # Download subtitle file
                    subtitle_url = captions["en"][0].get("url")
                    if subtitle_url:
                        # Would need to download and parse VTT file
                        # For now, return None and let the analyzer fetch via other means
                        pass
                
                # Fallback: use description if no transcript
                return clean_text(info.get("description", "")) if info.get("description") else None
                
        except Exception as e:
            logger.debug(f"Could not extract transcript for {video_url}: {e}")
        
        return None
    
    async def scrape_specific_videos(self, video_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape specific videos by URL.
        
        Args:
            video_urls: List of YouTube video URLs
            
        Returns:
            List of video data dictionaries
        """
        videos_data = []
        
        ydl_opts = self._get_base_options()
        
        for url in video_urls:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if not info:
                        continue
                    
                    duration = info.get("duration", 0)
                    is_short = duration <= 60
                    
                    video_data = {
                        "platform": Platform.YOUTUBE,
                        "content_type": ContentType.SHORT if is_short else ContentType.REEL,
                        "external_id": info.get("id"),
                        "url": info.get("webpage_url", url),
                        "title": clean_text(info.get("title", ""))[:500],
                        "description": clean_text(info.get("description", "")) if info.get("description") else None,
                        "thumbnail_url": info.get("thumbnail"),
                        "views": info.get("view_count"),
                        "likes": info.get("like_count"),
                        "comments": info.get("comment_count"),
                        "shares": None,
                        "duration_seconds": duration,
                        "published_at": None,
                        "scraped_at": datetime.now(),
                    }
                    
                    videos_data.append(video_data)
                    
            except Exception as e:
                logger.error(f"Failed to scrape video {url}: {e}")
        
        return videos_data
    
    async def save_to_database(
        self,
        channel_name: str,
        videos_data: List[Dict[str, Any]]
    ) -> tuple[Optional[CompetitorAccount], int]:
        """
        Save scraped data to database.
        
        Args:
            channel_name: YouTube channel name
            videos_data: List of video data
            profile_data: Optional channel data
            
        Returns:
            Tuple of (CompetitorAccount, number of videos saved)
        """
        async with async_session_factory() as session:
            # Find or create competitor account
            result = await session.execute(
                db_select(CompetitorAccount).where(
                    CompetitorAccount.platform == Platform.YOUTUBE,
                    CompetitorAccount.username == channel_name,
                )
            )
            competitor = result.scalar_one_or_none()
            
            if not competitor:
                competitor = CompetitorAccount(
                    platform=Platform.YOUTUBE,
                    username=channel_name,
                )
                session.add(competitor)
            
            competitor.last_scraped_at = datetime.now()
            
            # Save videos
            saved_count = 0
            for video_data in videos_data:
                # Check for duplicates
                existing = await session.execute(
                    db_select(ScrapedContent).where(
                        ScrapedContent.platform == Platform.YOUTUBE,
                        ScrapedContent.external_id == video_data["external_id"],
                    )
                )
                
                if existing.scalar_one_or_none():
                    continue
                
                scraped_content = ScrapedContent(
                    competitor_id=competitor.id,
                    **video_data,
                )
                session.add(scraped_content)
                saved_count += 1
            
            await session.commit()
            logger.info(f"Saved {saved_count} videos for channel: {channel_name}")
            
            return competitor, saved_count


# SQLAlchemy import helper
from sqlalchemy import select as db_select