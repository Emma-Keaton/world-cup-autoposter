"""
Video rendering endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid

from app.core.database import get_db
from app.models import ContentBrief, ContentStatus, GeneratedVideo
from app.renderer.tts_engine import TTSEngine
from app.renderer.subtitle_generator import SubtitleGenerator
from app.renderer.asset_downloader import AssetDownloader
from app.renderer.video_renderer import VideoRenderer

router = APIRouter()


class RenderVideoRequest(BaseModel):
    """Request to render a video from a content brief."""
    brief_id: str = Field(..., description="ContentBrief ID")
    voice: str = Field("male_1", description="TTS voice preset")
    include_music: bool = Field(True, description="Include background music")
    visual_style: Optional[dict] = None


class RenderResponse(BaseModel):
    """Response with render job details."""
    job_id: str
    brief_id: str
    status: str
    estimated_time_seconds: int


@router.post("/render", response_model=RenderResponse)
async def render_video(
    request: RenderVideoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Render a video from a content brief.
    
    Pipeline:
    1. Generate TTS from reel script
    2. Generate subtitles with timing
    3. Download stock footage based on visual direction
    4. Composite everything into final video
    """
    # Verify brief exists
    result = await db.execute(
        select(ContentBrief).where(ContentBrief.id == request.brief_id)
    )
    brief = result.scalar_one_or_none()
    
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content brief not found",
        )
    
    if not brief.reel_script:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brief has no reel script",
        )
    
    # Create render job
    job_id = str(uuid.uuid4())
    
    video_record = GeneratedVideo(
        content_brief_id=request.brief_id,
        title=brief.topic[:100],
        status=ContentStatus.DRAFT,
        tts_voice=request.voice,
    )
    
    db.add(video_record)
    await db.commit()
    await db.refresh(video_record)
    
    # Schedule render task
    background_tasks.add_task(
        _render_video_task,
        job_id=job_id,
        video_id=video_record.id,
        brief_id=request.brief_id,
        voice=request.voice,
        include_music=request.include_music,
        visual_style=request.visual_style or brief.visual_direction,
    )
    
    return RenderResponse(
        job_id=job_id,
        brief_id=request.brief_id,
        status="queued",
        estimated_time_seconds=120,
    )


async def _render_video_task(
    job_id: str,
    video_id: str,
    brief_id: str,
    voice: str,
    include_music: bool,
    visual_style: Optional[dict],
):
    """Background task to render video."""
    from app.core.database import async_session_factory
    from datetime import datetime
    
    try:
        async with async_session_factory() as session:
            # Get brief
            result = await session.execute(
                select(ContentBrief).where(ContentBrief.id == brief_id)
            )
            brief = result.scalar_one()
            
            if not brief.reel_script:
                raise ValueError("No reel script found")
            
            # Step 1: Generate TTS
            tts = TTSEngine()
            audio_path = await tts.generate_speech(
                text=brief.reel_script,
                voice=voice,
                output_filename=f"{job_id}_audio.mp3",
            )
            
            # Step 2: Generate subtitles
            subtitle_gen = SubtitleGenerator()
            subtitle_segments = await subtitle_gen.generate_from_audio(
                audio_path=audio_path,
                output_filename=f"{job_id}_segments.json",
            )
            
            # Create ASS subtitle file for styling
            subtitle_path = subtitle_gen.create_ass_subtitle(
                segments=subtitle_segments,
                output_filename=f"{job_id}.ass",
                style="dynamic",
            )
            
            # Step 3: Download background assets
            downloader = AssetDownloader()
            assets = await downloader.search_football_assets(
                context=brief.topic,
                limit=5,
            )
            
            asset_paths = []
            for asset in assets[:3]:
                path = await downloader.download_asset(asset)
                if path:
                    asset_paths.append(path)
            
            # Step 4: Render video
            renderer = VideoRenderer()
            output_filename = f"{job_id}.mp4"
            
            video_path = await renderer.render_video(
                audio_path=audio_path,
                subtitle_path=subtitle_path,
                background_assets=asset_paths,
                music_path=None,  # Could add royalty-free music here
                output_filename=output_filename,
                visual_style=visual_style,
            )
            
            # Create thumbnail
            thumbnail_path = await renderer.create_thumbnail(
                video_path=video_path,
                output_path=str(renderer.output_dir / f"{job_id}_thumb.jpg"),
            )
            
            # Update video record
            result = await session.execute(
                select(GeneratedVideo).where(GeneratedVideo.id == video_id)
            )
            video = result.scalar_one()
            
            video.file_path = video_path
            video.thumbnail_path = thumbnail_path
            video.subtitle_path = subtitle_path
            video.audio_path = audio_path
            video.status = ContentStatus.GENERATED
            
            await session.commit()
    
    except Exception as e:
        # Update status to failed
        async with async_session_factory() as session:
            result = await session.execute(
                select(GeneratedVideo).where(GeneratedVideo.id == video_id)
            )
            video = result.scalar_one()
            video.status = ContentStatus.FAILED
            await session.commit()
        
        import logging
        logging.error(f"Render task failed: {e}")


@router.get("/jobs/{job_id}")
async def get_render_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get status of a render job."""
    # Since job_id is UUID, we need to find the video by scanning
    # In production, we'd store the job_id mapping
    result = await db.execute(
        select(GeneratedVideo).order_by(GeneratedVideo.created_at.desc())
    )
    videos = result.scalars().all()
    
    # Find matching video (simplified - in production use proper job tracking)
    for video in videos:
        if job_id == video.id:  # Using video ID as job ID for simplicity
            return {
                "job_id": job_id,
                "video_id": video.id,
                "brief_id": video.content_brief_id,
                "status": video.status.value,
                "file_path": video.file_path,
                "thumbnail_path": video.thumbnail_path,
                "created_at": video.created_at.isoformat(),
            }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Render job not found",
    )


@router.get("/videos")
async def list_videos(
    brief_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List generated videos."""
    query = select(GeneratedVideo).order_by(GeneratedVideo.created_at.desc()).limit(limit)
    
    if brief_id:
        query = query.where(GeneratedVideo.content_brief_id == brief_id)
    
    if status:
        query = query.where(GeneratedVideo.status == ContentStatus(status))
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    return {
        "videos": [
            {
                "id": v.id,
                "title": v.title,
                "brief_id": v.content_brief_id,
                "status": v.status.value,
                "file_path": v.file_path,
                "thumbnail_path": v.thumbnail_path,
                "duration_seconds": v.duration_seconds,
                "created_at": v.created_at.isoformat(),
            }
            for v in videos
        ],
        "total": len(videos),
    }


@router.get("/videos/{video_id}")
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get video details."""
    result = await db.execute(
        select(GeneratedVideo).where(GeneratedVideo.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    
    return {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "content_brief_id": video.content_brief_id,
        "file_path": video.file_path,
        "thumbnail_path": video.thumbnail_path,
        "subtitle_path": video.subtitle_path,
        "audio_path": video.audio_path,
        "duration_seconds": video.duration_seconds,
        "width": video.width,
        "height": video.height,
        "fps": video.fps,
        "status": video.status.value,
        "created_at": video.created_at.isoformat(),
    }


@router.post("/videos/{video_id}/publish")
async def publish_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Mark video as ready for publishing."""
    result = await db.execute(
        select(GeneratedVideo).where(GeneratedVideo.id == video_id)
    )
    video = result.scalar_one()
    
    if not video.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video not rendered yet",
        )
    
    video.status = ContentStatus.SCHEDULED
    await db.commit()
    
    return {
        "id": video.id,
        "status": "scheduled",
        "message": "Video ready for publishing",
    }


@router.get("/voices")
async def list_voices():
    """Get available TTS voices."""
    tts = TTSEngine()
    voices = await tts.get_available_voices()
    
    return {"voices": voices}