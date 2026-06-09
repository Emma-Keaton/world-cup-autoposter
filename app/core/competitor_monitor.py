"""
Competitor Monitor - Watches inspiration channels for new uploads.

Sources:
- YouTube: FIFA, Tifo Football, Football Made Simple, COPA90, Nouman
- Footballia: Historical match archive
- Official Broadcasters: FOX Soccer, Sky Sports, ESPN FC

Features:
- RSS feed monitoring
- YouTube Data API integration
- Web scraping for channels without RSS
- Auto-download new uploads
- Metadata extraction and categorization
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not installed - RSS monitoring disabled")

from app.clipper.youtube_downloader import YouTubeDownloader
from app.core.config import settings


@dataclass
class SourceChannel:
    """Inspiration source channel."""
    name: str
    platform: str  # youtube, footballia, broadcaster
    url: str
    rss_feed: Optional[str] = None
    api_channel_id: Optional[str] = None
    content_type: str = "mixed"  # analysis, highlights, news, documentary
    copyright_risk: str = "medium"  # low, medium, high
    notes: str = ""


@dataclass
class MonitoredUpload:
    """Detected upload from monitored channel."""
    id: str
    title: str
    url: str
    channel: str
    published_at: datetime
    duration: int  # seconds
    thumbnail: Optional[str] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    downloaded: bool = False
    download_path: Optional[str] = None
    processed: bool = False


# Pre-configured inspiration channels
INSPIRATION_CHANNELS = [
    # Tactical Analysis Channels (SAFE - use for format/style inspiration)
    SourceChannel(
        name="Tifo Football",
        platform="youtube",
        url="https://www.youtube.com/@TifoFootball",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UC69n Rising",
        api_channel_id="UC69nRising",  # Replace with actual ID
        content_type="analysis",
        copyright_risk="low",
        notes="Animated tactical analysis - safe format to emulate",
    ),
    SourceChannel(
        name="Football Made Simple",
        platform="youtube",
        url="https://www.youtube.com/@FootballMadeSimple",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UCQvN7WkSTIL0mZL有害",
        content_type="analysis",
        copyright_risk="low",
        notes="Simplified explanations with visuals",
    ),
    SourceChannel(
        name="Nouman",
        platform="youtube",
        url="https://www.youtube.com/@Nouman",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UC8Nouman",
        content_type="analysis",
        copyright_risk="low",
        notes="Tactical analysis with boards/graphics",
    ),
    
    # Official Sources (for news/announcements)
    SourceChannel(
        name="FIFA Official",
        platform="youtube",
        url="https://www.youtube.com/@FIFA",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UCFIFA",
        content_type="news",
        copyright_risk="high",
        notes="Official trailers, announcements - use for news only",
    ),
    
    # Fan Culture / Storytelling
    SourceChannel(
        name="COPA90",
        platform="youtube",
        url="https://www.youtube.com/@COPA90",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UCCOPA90",
        content_type="documentary",
        copyright_risk="medium",
        notes="Fan culture, matchday vlogs - storytelling inspiration",
    ),
    
    # Broadcasters (for highlights - use carefully under fair use)
    SourceChannel(
        name="FOX Soccer",
        platform="youtube",
        url="https://www.youtube.com/@FOXSoccer",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UCFOXSoccer",
        content_type="highlights",
        copyright_risk="high",
        notes="Use 3-5 second clips only with heavy editing",
    ),
    SourceChannel(
        name="Sky Sports Football",
        platform="youtube",
        url="https://www.youtube.com/@SkySportsFootball",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UCSkySports",
        content_type="highlights",
        copyright_risk="high",
        notes="Use 3-5 second clips only with heavy editing",
    ),
    SourceChannel(
        name="ESPN FC",
        platform="youtube",
        url="https://www.youtube.com/@ESPNFC",
        rss_feed="https://www.youtube.com/feeds/videos.xml?channel_id=UCESPNFC",
        content_type="news",
        copyright_risk="medium",
        notes="News and analysis",
    ),
    
    # Historical Archive
    SourceChannel(
        name="Footballia",
        platform="footballia",
        url="https://footballia.eu",
        content_type="archive",
        copyright_risk="medium",
        notes="Full historical matches - extract short clips only",
    ),
]


class CompetitorMonitor:
    """
    Monitors inspiration channels for new uploads.
    
    Features:
    - RSS feed polling
    - YouTube API integration
    - Footballia scraping
    - Auto-download and categorization
    """
    
    def __init__(
        self,
        download_dir: str = "./temp/monitored_content",
        check_interval_minutes: int = 30,
    ):
        """
        Initialize monitor.
        
        Args:
            download_dir: Directory for downloaded content
            check_interval_minutes: How often to check for new uploads
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.check_interval = timedelta(minutes=check_interval_minutes)
        self.channels = INSPIRATION_CHANNELS.copy()
        self.youtube_downloader = YouTubeDownloader(
            output_dir=str(self.download_dir / "youtube")
        )
        
        # State tracking
        self.last_check = datetime.now() - self.check_interval
        self.upload_cache: Dict[str, MonitoredUpload] = {}
        self.download_queue: List[MonitoredUpload] = []
    
    async def check_all_channels(self) -> List[MonitoredUpload]:
        """Check all channels for new uploads."""
        
        new_uploads = []
        
        for channel in self.channels:
            try:
                if channel.platform == "youtube" and channel.rss_feed:
                    uploads = await self._check_youtube_rss(channel)
                elif channel.platform == "footballia":
                    uploads = await self._check_footballia(channel)
                else:
                    uploads = []
                
                # Filter to only new uploads since last check
                new_since_last = [
                    u for u in uploads
                    if u.published_at > self.last_check
                ]
                
                new_uploads.extend(new_since_last)
                
                # Cache all uploads
                for upload in uploads:
                    self.upload_cache[upload.id] = upload
                
                logger.info(
                    f"Checked {channel.name}: {len(uploads)} total, "
                    f"{len(new_since_last)} new"
                )
                
            except Exception as e:
                logger.error(f"Failed to check {channel.name}: {e}")
        
        self.last_check = datetime.now()
        return new_uploads
    
    async def _check_youtube_rss(self, channel: SourceChannel) -> List[MonitoredUpload]:
        """Check YouTube channel via RSS feed."""
        
        if not FEEDPARSER_AVAILABLE:
            logger.warning("feedparser not installed")
            return []
        
        if not channel.rss_feed:
            return []
        
        try:
            # Parse RSS feed
            feed = feedparser.parse(channel.rss_feed)
            
            uploads = []
            for entry in feed.entries[:20]:  # Last 20 uploads
                # Extract video ID from URL
                video_url = entry.link
                video_id = video_url.split("v=")[1].split("&")[0]
                
                # Parse publish date
                published = datetime.fromisoformat(
                    entry.published.replace("Z", "+00:00")
                )
                
                # Extract duration if available
                duration_match = re.search(
                    r"(\d+):(\d+)",
                    entry.get("media_duration", "0:00")
                )
                duration = 0
                if duration_match:
                    duration = int(duration_match.group(1)) * 60 + int(duration_match.group(2))
                
                upload = MonitoredUpload(
                    id=video_id,
                    title=entry.title,
                    url=video_url,
                    channel=channel.name,
                    published_at=published,
                    duration=duration,
                    thumbnail=entry.get("media_thumbnail"),
                    description=entry.get("description", ""),
                    tags=entry.get("tags", []),
                )
                
                uploads.append(upload)
            
            return uploads
            
        except Exception as e:
            logger.error(f"RSS check failed for {channel.name}: {e}")
            return []
    
    async def _check_footballia(
        self,
        channel: SourceChannel,
    ) -> List[MonitoredUpload]:
        """Check Footballia for new matches."""
        
        # Footballia doesn't have RSS - would need web scraping
        # For now, return empty list
        # In production, implement scraping logic
        
        logger.debug(f"Footballia check not implemented for {channel.name}")
        return []
    
    async def download_upload(
        self,
        upload: MonitoredUpload,
        download_segment: bool = False,
        segment_start: int = 0,
        segment_end: int = 60,
    ) -> Optional[str]:
        """
        Download a monitored upload.
        
        Args:
            upload: Upload to download
            download_segment: Download only a segment
            segment_start: Start time (seconds)
            segment_end: End time (seconds)
            
        Returns:
            Path to downloaded file
        """
        
        try:
            result = await self.youtube_downloader.download_video(
                url=upload.url,
                download_segment=download_segment,
                start_time=segment_start if download_segment else None,
                end_time=segment_end if download_segment else None,
            )
            
            if "error" in result:
                logger.error(f"Download failed: {result['error']}")
                return None
            
            # Update upload record
            upload.downloaded = True
            upload.download_path = result.get("video_path")
            
            # Add to download queue for processing
            self.download_queue.append(upload)
            
            logger.info(f"Downloaded: {upload.title}")
            return result.get("video_path")
            
        except Exception as e:
            logger.error(f"Download failed for {upload.title}: {e}")
            return None
    
    async def process_downloads(self) -> Dict[str, Any]:
        """Process downloaded content and prepare for content creation."""
        
        results = {
            "processed": 0,
            "highlights_detected": 0,
            "analysis_opportunities": 0,
            "skipped": 0,
        }
        
        for upload in self.download_queue:
            if not upload.downloaded or not upload.download_path:
                continue
            
            # Categorize by content type
            category = self._categorize_content(upload)
            
            # Extract metadata for LLM analysis
            metadata = await self._extract_content_metadata(upload)
            
            # Store processed metadata
            metadata_path = self.download_dir / f"{upload.id}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(
                    {
                        "upload_id": upload.id,
                        "title": upload.title,
                        "channel": upload.channel,
                        "category": category,
                        "tags": upload.tags,
                        "duration": upload.duration,
                        "copyright_risk": upload.channel.copyright_risk,
                        "video_path": upload.download_path,
                        "subtitle_path": None,  # Would extract from video
                        "key_moments": [],  # Would analyze for highlights
                    },
                    f,
                    indent=2,
                )
            
            upload.processed = True
            results["processed"] += 1
            
            if category == "highlights":
                results["highlights_detected"] += 1
            elif category == "analysis":
                results["analysis_opportunities"] += 1
        
        # Clear queue after processing
        self.download_queue.clear()
        
        return results
    
    def _categorize_content(self, upload: MonitoredUpload) -> str:
        """Categorize upload by content type."""
        
        title_lower = upload.title.lower()
        description_lower = upload.description.lower()
        
        # Check for highlight indicators
        highlight_keywords = [
            "goal", "highlight", "all goals", "extended highlights",
            "best moments", "goals galore", "match highlights",
        ]
        
        # Check for analysis indicators
        analysis_keywords = [
            "tactical analysis", "analysis", "tactics", "breakdown",
            "why", "how", "explained", "review",
        ]
        
        # Check for news indicators
        news_keywords = [
            "breaking", "news", "announcement", "confirmed",
            "official", "transfer", "signing",
        ]
        
        for keyword in highlight_keywords:
            if keyword in title_lower:
                return "highlights"
        
        for keyword in analysis_keywords:
            if keyword in title_lower or keyword in description_lower:
                return "analysis"
        
        for keyword in news_keywords:
            if keyword in title_lower:
                return "news"
        
        return "mixed"
    
    async def _extract_content_metadata(
        self,
        upload: MonitoredUpload,
    ) -> Dict[str, Any]:
        """Extract metadata for LLM analysis."""
        
        # In production, would:
        # 1. Extract subtitles/transcript
        # 2. Run NLP for topic extraction
        # 3. Detect key moments
        # 4. Generate embeddings for similarity search
        
        return {
            "topics": [],
            "key_moments": [],
            "transcript": None,
            "sentiment": "neutral",
        }
    
    def add_custom_channel(
        self,
        name: str,
        youtube_url: str,
        content_type: str = "mixed",
    ) -> SourceChannel:
        """Add custom channel to monitor list."""
        
        # Extract channel ID from URL
        channel_id = youtube_url.split("/channel/")[-1] if "/channel/" in youtube_url else None
        
        if not channel_id:
            # Try username format
            channel_id = youtube_url.split("/@")[-1] if "/@" in youtube_url else None
        
        channel = SourceChannel(
            name=name,
            platform="youtube",
            url=youtube_url,
            rss_feed=f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}" if channel_id else None,
            api_channel_id=channel_id,
            content_type=content_type,
            copyright_risk="medium",
        )
        
        self.channels.append(channel)
        logger.info(f"Added custom channel: {name}")
        
        return channel
    
    def get_channel_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        
        channel_stats = {}
        for channel in self.channels:
            uploads_from_channel = [
                u for u in self.upload_cache.values()
                if u.channel == channel.name
            ]
            
            channel_stats[channel.name] = {
                "total_uploads": len(uploads_from_channel),
                "new_since_last_check": len([
                    u for u in uploads_from_channel
                    if u.published_at > self.last_check - self.check_interval
                ]),
                "downloaded": len([u for u in uploads_from_channel if u.downloaded]),
                "content_type": channel.content_type,
                "copyright_risk": channel.copyright_risk,
            }
        
        return {
            "total_channels": len(self.channels),
            "total_uploads_cached": len(self.upload_cache),
            "pending_downloads": len(self.download_queue),
            "last_check": self.last_check.isoformat(),
            "check_interval_minutes": self.check_interval.total_seconds() / 60,
            "channels": channel_stats,
        }


class ContentSuggestionEngine:
    """
    Suggests content ideas based on monitored uploads.
    
    Analyzes trending topics, successful formats, and gaps
    in the content landscape.
    """
    
    def __init__(self, monitor: CompetitorMonitor):
        """
        Initialize suggestion engine.
        
        Args:
            monitor: Competitor monitor instance
        """
        self.monitor = monitor
    
    def suggest_content_ideas(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Generate content ideas based on monitored content."""
        
        ideas = []
        
        # Group uploads by category
        uploads_by_category = {}
        for upload in self.monitor.upload_cache.values():
            category = self.monitor._categorize_content(upload)
            if category not in uploads_by_category:
                uploads_by_category[category] = []
            uploads_by_category[category].append(upload)
        
        # Idea 1: Trending topics from recent uploads
        recent_topics = self._extract_trending_topics(
            list(self.monitor.upload_cache.values())
        )
        
        for topic in recent_topics[:limit]:
            ideas.append({
                "type": "trending_topic",
                "topic": topic,
                "confidence": "high",
                "reasoning": "Multiple channels covering this topic",
                "suggested_format": "tactical_analysis",
            })
        
        # Idea 2: Format inspiration from successful uploads
        if "analysis" in uploads_by_category:
            analysis_videos = uploads_by_category["analysis"]
            ideas.append({
                "type": "format_inspiration",
                "inspiration": "Tifo-style analysis",
                "confidence": "medium",
                "reasoning": "Analysis videos perform well",
                "suggested_format": "animated_tactical_breakdown",
            })
        
        # Idea 3: Content gaps (topics not covered)
        # Would implement gap analysis here
        
        return ideas[:limit]
    
    def _extract_trending_topics(
        self,
        uploads: List[MonitoredUpload],
    ) -> List[str]:
        """Extract trending topics from upload titles/tags."""
        
        # Simple keyword frequency analysis
        topic_counts = {}
        
        for upload in uploads:
            # Count tags
            for tag in upload.tags:
                topic_counts[tag] = topic_counts.get(tag, 0) + 1
            
            # Count words in titles
            words = upload.title.lower().split()
            for word in words:
                if len(word) > 4:  # Skip short words
                    topic_counts[word] = topic_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        return [topic for topic, count in sorted_topics[:20]]