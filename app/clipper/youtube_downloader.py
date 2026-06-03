"""
YouTube video downloader using yt-dlp.
Downloads full videos or specific segments for clipping.
"""
import asyncio
import yt_dlp
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger

from app.core.utils import sanitize_filename


class YouTubeDownloader:
    """
    Download YouTube videos for clipping.
    
    Supports:
    - Full video download
    - Segment download (start/end time)
    - Metadata extraction
    - Thumbnail download
    """
    
    def __init__(self, output_dir: str = "./temp/youtube_downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_base_options(self) -> Dict[str, Any]:
        """Get base yt-dlp options."""
        return {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US"],
            "subtitlesformat": "vtt",
            "writethumbnail": True,
            "thumbnail_format": "jpg",
            "writeinfojson": True,
            "quiet": True,
            "no_warnings": True,
        }
    
    async def download_video(
        self,
        url: str,
        output_filename: Optional[str] = None,
        download_segment: bool = False,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Download a YouTube video.
        
        Args:
            url: YouTube video URL
            output_filename: Custom output filename
            download_segment: Download only a segment
            start_time: Segment start time in seconds
            end_time: Segment end time in seconds
            
        Returns:
            Dictionary with download paths and metadata
        """
        video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1].split("?")[0]
        
        if not output_filename:
            output_filename = sanitize_filename(video_id)
        
        output_template = str(self.output_dir / output_filename)
        
        # Build options
        ydl_opts = self._get_base_options()
        ydl_opts["outtmpl"] = f"{output_template}.%(ext)s"
        
        # Add segment download if requested
        if download_segment and start_time is not None and end_time is not None:
            ydl_opts["download_ranges"] = [
                {
                    "start_time": start_time,
                    "end_time": end_time,
                }
            ]
            ydl_opts["force_keyframes_at_cuts"] = True
        
        try:
            loop = asyncio.get_event_loop()
            
            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return info
            
            info = await loop.run_in_executor(None, _download)
            
            # Build result paths
            result = {
                "video_id": info.get("id", video_id),
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "video_path": f"{output_template}.mp4",
                "audio_path": None,
                "subtitle_path": f"{output_template}.en.vtt" if Path(f"{output_template}.en.vtt").exists() else None,
                "thumbnail_path": f"{output_template}.jpg" if Path(f"{output_template}.jpg").exists() else None,
                "metadata_path": f"{output_template}.info.json",
                "url": url,
                "uploader": info.get("uploader", "Unknown"),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
            }
            
            # Check for subtitle files
            for lang in ["en", "en-US", "en-GB"]:
                subtitle_path = f"{output_template}.{lang}.vtt"
                if Path(subtitle_path).exists():
                    result["subtitle_path"] = subtitle_path
                    break
            
            logger.info(f"Downloaded: {result['title']} ({result['duration']}s)")
            return result
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {
                "error": str(e),
                "video_id": video_id,
                "url": url,
            }
    
    async def download_playlist(
        self,
        playlist_url: str,
        max_videos: int = 10,
        min_duration: int = 0,
        max_duration: int = 600,
    ) -> List[Dict[str, Any]]:
        """
        Download videos from a playlist.
        
        Args:
            playlist_url: YouTube playlist URL
            max_videos: Maximum number of videos to download
            min_duration: Minimum video duration (seconds)
            max_duration: Maximum video duration (seconds)
            
        Returns:
            List of download results
        """
        ydl_opts = {
            **self._get_base_options(),
            "extract_flat": True,
            "playlistend": max_videos,
        }
        
        try:
            loop = asyncio.get_event_loop()
            
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(playlist_url, download=False)
            
            playlist_info = await loop.run_in_executor(None, _extract)
            
            results = []
            entries = playlist_info.get("entries", [])
            
            for entry in entries[:max_videos]:
                if not entry:
                    continue
                
                duration = entry.get("duration", 0)
                
                # Filter by duration
                if duration < min_duration or duration > max_duration:
                    logger.info(f"Skipping {entry.get('title', 'Unknown')} - duration {duration}s")
                    continue
                
                video_url = f"https://youtube.com/watch?v={entry.get('id')}"
                result = await self.download_video(video_url)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Playlist download failed: {e}")
            return []
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video metadata without downloading.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video metadata
        """
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        
        try:
            loop = asyncio.get_event_loop()
            
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await loop.run_in_executor(None, _extract)
            
            return {
                "video_id": info.get("id"),
                "title": info.get("title"),
                "description": info.get("description"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "channel_id": info.get("channel_id"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "comment_count": info.get("comment_count"),
                "upload_date": info.get("upload_date"),
                "thumbnail": info.get("thumbnail"),
                "url": info.get("webpage_url"),
                "chapters": info.get("chapters", []),
                "tags": info.get("tags", []),
            }
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {}
    
    async def search_and_download(
        self,
        query: str,
        max_results: int = 5,
        sort_by: str = "relevance",
        duration_range: tuple = (0, 600),
    ) -> List[Dict[str, Any]]:
        """
        Search YouTube and download matching videos.
        
        Args:
            query: Search query
            max_results: Maximum results to download
            sort_by: Sort order (relevance, date, views, rating)
            duration_range: (min_seconds, max_seconds)
            
        Returns:
            List of download results
        """
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        
        ydl_opts = {
            **self._get_base_options(),
            "extract_flat": True,
            "default_search": "ytsearch",
        }
        
        try:
            loop = asyncio.get_event_loop()
            
            def _search():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            
            search_results = await loop.run_in_executor(None, _search)
            
            results = []
            entries = search_results.get("entries", [])
            
            for entry in entries:
                if not entry:
                    continue
                
                duration = entry.get("duration", 0)
                
                # Filter by duration
                if duration < duration_range[0] or duration > duration_range[1]:
                    continue
                
                video_url = f"https://youtube.com/watch?v={entry.get('id')}"
                result = await self.download_video(video_url)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Search download failed: {e}")
            return []