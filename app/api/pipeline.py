"""
Enhanced pipeline API endpoints.

Provides endpoints for:
- Automated video creation pipeline
- Competitor monitoring
- Verification and quality checks
- Batch processing
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models import ContentBrief, ContentStatus, GeneratedVideo
from app.renderer.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineConfig,
    PipelineResult,
)
from app.core.competitor_monitor import CompetitorMonitor, ContentSuggestionEngine

router = APIRouter()


# =========== Pipeline Endpoints ===========

class CreateVideoRequest(BaseModel):
    """Request to create video via full pipeline."""
    brief_id: str = Field(..., description="ContentBrief ID")
    platform: str = Field("youtube_shorts", description="Target platform")
    edit_style: str = Field("heavy_editing", description="Editing intensity")
    source_urls: Optional[List[str]] = Field(None, description="Source video URLs")
    skip_verification: bool = Field(False, description="Skip copyright verification")


class CreateVideoResponse(BaseModel):
    """Response with pipeline job details."""
    job_id: str
    brief_id: str
    status: str
    estimated_time_seconds: int = 180
    platform: str


@router.post("/create", response_model=CreateVideoResponse)
async def create_video_pipeline(
    request: CreateVideoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create complete video using the automated pipeline.
    
    Pipeline stages:
    1. Script analysis and clip planning
    2. TTS voiceover generation
    3. Subtitle generation
    4. Source material acquisition
    5. Copyright-safe editing
    6. Final rendering with platform preset
    7. Double verification (copyright + quality)
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
    
    # Create job record
    job_id = str(uuid.uuid4())
    
    video_record = GeneratedVideo(
        content_brief_id=request.brief_id,
        title=brief.topic[:100],
        status=ContentStatus.DRAFT,
        job_id=job_id,
    )
    
    db.add(video_record)
    await db.commit()
    await db.refresh(video_record)
    
    # Schedule pipeline task
    background_tasks.add_task(
        _run_pipeline_task,
        job_id=job_id,
        video_id=video_record.id,
        brief_id=request.brief_id,
        platform=request.platform,
        edit_style=request.edit_style,
        source_urls=request.source_urls,
        skip_verification=request.skip_verification,
    )
    
    return CreateVideoResponse(
        job_id=job_id,
        brief_id=request.brief_id,
        status="queued",
        estimated_time_seconds=180,
        platform=request.platform,
    )


async def _run_pipeline_task(
    job_id: str,
    video_id: str,
    brief_id: str,
    platform: str,
    edit_style: str,
    source_urls: Optional[List[str]],
    skip_verification: bool,
):
    """Background task to run full pipeline."""
    from app.core.database import async_session_factory
    from loguru import logger
    
    try:
        # Initialize pipeline
        config = PipelineConfig(
            platform=platform,
            edit_style=edit_style,
            skip_verification=skip_verification,
        )
        
        orchestrator = PipelineOrchestrator(config=config)
        
        async with async_session_factory() as session:
            # Get brief
            result = await session.execute(
                select(ContentBrief).where(ContentBrief.id == brief_id)
            )
            brief = result.scalar_one()
            
            # Run pipeline
            pipeline_result = await orchestrator.create_video_from_brief(
                brief=brief,
                source_materials=source_urls,
            )
            
            # Update video record
            result = await session.execute(
                select(GeneratedVideo).where(GeneratedVideo.id == video_id)
            )
            video = result.scalar_one()
            
            if pipeline_result.success:
                video.file_path = pipeline_result.video_path
                video.thumbnail_path = pipeline_result.thumbnail_path
                video.duration_seconds = pipeline_result.duration
                video.status = ContentStatus.GENERATED
                video.width = 1080
                video.height = 1920
                video.fps = 30
                
                # Store verification results
                if pipeline_result.copyright_report:
                    video.metadata = {
                        "copyright_score": pipeline_result.copyright_report.overall_score,
                        "risk_level": pipeline_result.copyright_report.risk_level.value,
                        "quality_score": pipeline_result.quality_score,
                        "clips_used": pipeline_result.clips_used,
                    }
                
                logger.info(f"Pipeline succeeded: {video.file_path}")
            else:
                video.status = ContentStatus.FAILED
                video.metadata = {"errors": pipeline_result.errors}
                logger.error(f"Pipeline failed: {pipeline_result.errors}")
            
            await session.commit()
            
    except Exception as e:
        logger.error(f"Pipeline task failed: {e}")
        
        async with async_session_factory() as session:
            result = await session.execute(
                select(GeneratedVideo).where(GeneratedVideo.id == video_id)
            )
            video = result.scalar_one()
            video.status = ContentStatus.FAILED
            video.metadata = {"error": str(e)}
            await session.commit()


@router.get("/job/{job_id}")
async def get_pipeline_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get status of pipeline job."""
    
    result = await db.execute(
        select(GeneratedVideo).where(GeneratedVideo.job_id == job_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    return {
        "job_id": job_id,
        "video_id": video.id,
        "brief_id": video.content_brief_id,
        "status": video.status.value,
        "file_path": video.file_path,
        "thumbnail_path": video.thumbnail_path,
        "duration": video.duration_seconds,
        "metadata": video.metadata,
        "created_at": video.created_at.isoformat(),
    }


# =========== Preview Endpoint ===========

@router.post("/preview/{brief_id}")
async def preview_sequence(
    brief_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Preview planned sequence without full rendering.
    
    Returns clip plan showing:
    - Number of clips
    - Duration of each clip
    - Visual types
    - Narrative structure
    """
    result = await db.execute(
        select(ContentBrief).where(ContentBrief.id == brief_id)
    )
    brief = result.scalar_one_or_none()
    
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brief not found",
        )
    
    orchestrator = PipelineOrchestrator()
    preview = await orchestrator.preview_sequence(brief=brief)
    
    return preview


# =========== Competitor Monitoring Endpoints ===========

class AddChannelRequest(BaseModel):
    """Request to add custom channel to monitor."""
    name: str
    youtube_url: str
    content_type: str = "mixed"


@router.get("/monitor/channels")
async def list_monitored_channels():
    """List all monitored channels."""
    
    monitor = CompetitorMonitor()
    stats = monitor.get_channel_stats()
    
    return stats


@router.post("/monitor/channels")
async def add_monitored_channel(request: AddChannelRequest):
    """Add custom channel to monitoring list."""
    
    monitor = CompetitorMonitor()
    channel = monitor.add_custom_channel(
        name=request.name,
        youtube_url=request.youtube_url,
        content_type=request.content_type,
    )
    
    return {
        "success": True,
        "channel": {
            "name": channel.name,
            "url": channel.url,
            "content_type": channel.content_type,
        },
    }


@router.get("/monitor/uploads")
async def list_monitored_uploads(
    limit: int = Query(50, le=200),
    downloaded_only: bool = False,
):
    """List uploads from monitored channels."""
    
    monitor = CompetitorMonitor()
    
    # In production, would query database
    uploads = list(monitor.upload_cache.values())
    
    if downloaded_only:
        uploads = [u for u in uploads if u.downloaded]
    
    return {
        "uploads": [
            {
                "id": u.id,
                "title": u.title,
                "channel": u.channel,
                "url": u.url,
                "duration": u.duration,
                "published_at": u.published_at.isoformat(),
                "downloaded": u.downloaded,
                "download_path": u.download_path,
            }
            for u in uploads[:limit]
        ],
        "total": len(uploads),
    }


@router.post("/monitor/check")
async def check_for_new_uploads():
    """Manually trigger check for new uploads."""
    
    monitor = CompetitorMonitor()
    new_uploads = await monitor.check_all_channels()
    
    return {
        "success": True,
        "new_uploads": [
            {
                "id": u.id,
                "title": u.title,
                "channel": u.channel,
                "url": u.url,
                "published_at": u.published_at.isoformat(),
            }
            for u in new_uploads
        ],
        "count": len(new_uploads),
    }


@router.post("/monitor/download")
async def download_monitored_upload(upload_id: str):
    """Download specific monitored upload."""
    
    monitor = CompetitorMonitor()
    
    upload = monitor.upload_cache.get(upload_id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )
    
    download_path = await monitor.download_upload(upload)
    
    return {
        "success": download_path is not None,
        "upload_id": upload_id,
        "download_path": download_path,
    }


# =========== Content Suggestions ===========

@router.get("/suggestions")
async def get_content_suggestions(limit: int = 10):
    """Get content suggestions based on monitored channels."""
    
    monitor = CompetitorMonitor()
    engine = ContentSuggestionEngine(monitor)
    
    suggestions = engine.suggest_content_ideas(limit=limit)
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
    }


# =========== Verification Endpoints ===========

class VerifyVideoRequest(BaseModel):
    """Request to verify video for copyright."""
    video_path: str
    source_paths: Optional[List[str]] = None
    script: Optional[str] = None


@router.post("/verify")
async def verify_video(request: VerifyVideoRequest):
    """
    Run copyright verification on video.
    
    Checks:
    - Fair use four factors
    - Audio fingerprint similarity
    - Visual similarity
    - Transformative content
    """
    
    checker = CopyrightSafetyChecker()
    
    report = await checker.verify_fair_use(
        video_path=request.video_path,
        source_materials=request.source_paths,
        script=request.script,
    )
    
    return {
        "approved": report.approved,
        "overall_score": report.overall_score,
        "risk_level": report.risk_level.value,
        "factors": {
            factor.value: score
            for factor, score in report.factors.items()
        },
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "score": c.score,
                "details": c.details,
            }
            for c in report.checks
        ],
        "recommendations": report.recommendations,
    }


# =========== Pipeline Status ===========

@router.get("/status")
async def get_pipeline_status():
    """Get pipeline status and configuration."""
    
    orchestrator = PipelineOrchestrator()
    status = orchestrator.get_pipeline_status()
    
    return status


# =========== Batch Processing ===========

class BatchCreateRequest(BaseModel):
    """Request to create multiple videos."""
    brief_ids: List[str] = Field(..., description="Brief IDs to process")
    platform: str = "youtube_shorts"
    max_concurrent: int = 3


@router.post("/batch")
async def batch_create_videos(
    request: BatchCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple videos from briefs."""
    
    # Verify briefs exist
    result = await db.execute(
        select(ContentBrief).where(ContentBrief.id.in_(request.brief_ids))
    )
    briefs = result.scalars().all()
    
    if len(briefs) != len(request.brief_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some briefs not found",
        )
    
    # Create job IDs
    job_ids = [str(uuid.uuid4()) for _ in request.brief_ids]
    
    # Schedule batch task
    background_tasks.add_task(
        _run_batch_pipeline,
        job_ids=job_ids,
        brief_ids=request.brief_ids,
        platform=request.platform,
        max_concurrent=request.max_concurrent,
    )
    
    return {
        "success": True,
        "jobs": [
            {"job_id": jid, "brief_id": bid}
            for jid, bid in zip(job_ids, request.brief_ids)
        ],
        "estimated_time_seconds": len(request.brief_ids) * 180,
    }


async def _run_batch_pipeline(
    job_ids: List[str],
    brief_ids: List[str],
    platform: str,
    max_concurrent: int,
):
    """Run batch pipeline."""
    from app.core.database import async_session_factory
    from loguru import logger
    
    config = PipelineConfig(platform=platform)
    orchestrator = PipelineOrchestrator(config=config)
    
    async with async_session_factory() as session:
        # Get briefs
        result = await session.execute(
            select(ContentBrief).where(ContentBrief.id.in_(brief_ids))
        )
        briefs = result.scalars().all()
        
        # Run batch pipeline
        results = await orchestrator.create_batch(
            briefs=list(briefs),
            max_concurrent=max_concurrent,
        )
        
        # Update records
        for job_id, result in zip(job_ids, results):
            video_result = await session.execute(
                select(GeneratedVideo).where(GeneratedVideo.job_id == job_id)
            )
            video = video_result.scalar_one_or_none()
            
            if video:
                if result.success:
                    video.file_path = result.video_path
                    video.thumbnail_path = result.thumbnail_path
                    video.status = ContentStatus.GENERATED
                else:
                    video.status = ContentStatus.FAILED
                    video.metadata = {"errors": result.errors}
        
        await session.commit()
    
    logger.info(f"Batch pipeline complete: {len(results)} videos")


# Import CopyrightSafetyChecker for verify endpoint
from app.core.copyright_checker import CopyrightSafetyChecker