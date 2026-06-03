"""
YouTube Clipper API endpoints.
Download, clip, and process YouTube videos.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.clipper.youtube_downloader import YouTubeDownloader
from app.clipper.clip_detector import ClipDetector
from app.clipper.video_clipper import VideoClipper

router = APIRouter()


class DownloadRequest(BaseModel):
    """Request to download a YouTube video."""
    url: str = Field(..., description="YouTube video URL")
    download_segment: bool = Field(False, description="Download only a segment")
    start_time: Optional[int] = Field(None, ge=0, description="Segment start (seconds)")
    end_time: Optional[int] = Field(None, ge=0, description="Segment end (seconds)")


class SearchRequest(BaseModel):
    """Request to search and download from YouTube."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, ge=1, le=20, description="Max results")
    min_duration: int = Field(0, ge=0, description="Min duration (seconds)")
    max_duration: int = Field(600, ge=0, description="Max duration (seconds)")


class ClipRequest(BaseModel):
    """Request to create clips from a video."""
    video_path: str = Field(..., description="Path to source video")
    clip_duration: int = Field(30, ge=10, le=60, description="Target clip duration")
    max_clips: int = Field(5, ge=1, le=10, description="Max clips to create")
    auto_detect: bool = Field(True, description="Auto-detect highlights")
    convert_vertical: bool = Field(True, description="Convert to 9:16")
    add_subtitles: bool = Field(True, description="Add subtitles if available")


class ClipResponse(BaseModel):
    """Response with clip information."""
    clip_id: str
    source_video: str
    start_time: float
    end_time: float
    duration: float
    clip_path: str
    confidence: Optional[float]
    keywords: List[str]


@router.post("/download")
async def download_video(request: DownloadRequest):
    """
    Download a YouTube video.
    
    Can download full video or specific segment.
    """
    downloader = YouTubeDownloader()
    
    try:
        result = await downloader.download_video(
            url=request.url,
            download_segment=request.download_segment,
            start_time=request.start_time,
            end_time=request.end_time,
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"],
            )
        
        return {
            "success": True,
            "video_id": result["video_id"],
            "title": result["title"],
            "duration": result["duration"],
            "video_path": result["video_path"],
            "subtitle_path": result.get("subtitle_path"),
            "thumbnail_path": result.get("thumbnail_path"),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/search")
async def search_and_download(request: SearchRequest):
    """
    Search YouTube and download matching videos.
    
    Useful for finding highlights, compilations, etc.
    """
    downloader = YouTubeDownloader()
    
    try:
        results = await downloader.search_and_download(
            query=request.query,
            max_results=request.max_results,
            duration_range=(request.min_duration, request.max_duration),
        )
        
        return {
            "success": True,
            "downloaded_count": len(results),
            "videos": [
                {
                    "video_id": r.get("video_id"),
                    "title": r.get("title"),
                    "duration": r.get("duration"),
                    "video_path": r.get("video_path"),
                }
                for r in results if "error" not in r
            ],
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/detect-clips")
async def detect_clips(request: ClipRequest):
    """
    Auto-detect highlight clips from a video.
    
    Uses subtitle keywords and audio peaks to find best moments.
    """
    detector = ClipDetector()
    video_path = request.video_path
    
    # Try to find subtitles
    subtitle_path = None
    possible_subs = [
        video_path.replace(".mp4", ".en.vtt"),
        video_path.replace(".mp4", ".en.srt"),
        video_path + ".vtt",
    ]
    
    for path in possible_subs:
        if Path(path).exists():
            subtitle_path = path
            break
    
    # Detect clips from subtitles
    clips = []
    
    if subtitle_path and request.auto_detect:
        clips = detector.detect_from_subtitles(
            subtitle_path=subtitle_path,
            clip_duration=request.clip_duration,
            max_clips=request.max_clips,
        )
    
    # If no subtitle clips, try audio peaks
    if not clips and request.auto_detect:
        clips = detector.detect_from_audio_peaks(
            audio_path=video_path,
            clip_duration=request.clip_duration,
            max_clips=request.max_clips,
        )
    
    # If still no clips, create default clips from beginning
    if not clips:
        # Get video duration
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
            return float(data.get("format", {}).get("duration", 60))
        
        duration = await get_duration()
        
        # Create clips at regular intervals
        interval = duration / request.max_clips
        for i in range(request.max_clips):
            start = i * interval
            clips.append({
                "start": start,
                "end": min(start + request.clip_duration, duration),
                "duration": request.clip_duration,
                "confidence": 1.0,
                "keywords": ["auto_generated"],
            })
    
    return {
        "success": True,
        "clips": clips,
        "source_video": video_path,
        "subtitle_path": subtitle_path,
    }


@router.post("/create-clip")
async def create_clip(
    request: ClipRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create processed clips from source video.
    
    Pipeline:
    1. Extract clip
    2. Convert to vertical (9:16)
    3. Add subtitles
    4. Add watermark (optional)
    
    Returns clip paths when ready.
    """
    clipper = VideoClipper()
    detector = ClipDetector()
    
    # Detect clips if auto-detect enabled
    clips = []
    
    if request.auto_detect:
        # Quick detection - just get timestamps
        subtitle_path = None
        possible_subs = [
            request.video_path.replace(".mp4", ".vtt"),
            request.video_path + ".vtt",
        ]
        
        for path in possible_subs:
            if Path(path).exists():
                subtitle_path = path
                break
        
        if subtitle_path:
            clips = detector.detect_from_subtitles(
                subtitle_path=subtitle_path,
                clip_duration=request.clip_duration,
                max_clips=request.max_clips,
            )
    
    # If no clips detected, create one from start
    if not clips:
        clips = [{
            "start": 0,
            "end": request.clip_duration,
            "duration": request.clip_duration,
            "confidence": 1.0,
            "keywords": ["manual"],
        }]
    
    # Create clips
    created_clips = []
    
    for i, clip_def in enumerate(clips):
        try:
            # Find subtitle file
            subtitle_path = None
            possible_subs = [
                request.video_path.replace(".mp4", ".en.vtt"),
                request.video_path.replace(".mp4", ".vtt"),
                request.video_path + ".vtt",
            ]
            
            for path in possible_subs:
                if Path(path).exists():
                    subtitle_path = path
                    break
            
            # Create clip
            output_filename = f"clip_{uuid.uuid4()}.mp4"
            
            clip_path = await clipper.create_complete_clip(
                video_path=request.video_path,
                clip_definition=clip_def,
                add_subtitles=request.add_subtitles and subtitle_path is not None,
                subtitle_path=subtitle_path,
                convert_vertical=request.convert_vertical,
                watermark_path=None,  # Add watermark path if you have one
                output_filename=output_filename,
            )
            
            created_clips.append({
                "clip_id": str(uuid.uuid4()),
                "source_video": request.video_path,
                "start_time": clip_def["start"],
                "end_time": clip_def["end"],
                "duration": clip_def["duration"],
                "clip_path": clip_path,
                "confidence": clip_def.get("confidence"),
                "keywords": clip_def.get("keywords", []),
            })
            
        except Exception as e:
            logger.error(f"Failed to create clip: {e}")
            continue
    
    return {
        "success": True,
        "clips_created": len(created_clips),
        "clips": created_clips,
    }


@router.get("/video-info")
async def get_video_info(url: str = Query(..., description="YouTube video URL")):
    """Get video metadata without downloading."""
    downloader = YouTubeDownloader()
    
    try:
        info = await downloader.get_video_info(url)
        
        return {
            "success": True,
            "info": info,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Need to import Path for type hints
from pathlib import Path
from loguru import logger