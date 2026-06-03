"""
Health check and system status endpoints.
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness_check(db=Depends(get_db)):
    """Readiness check - verifies database connection."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ready" if db_status == "connected" else "not_ready",
        "database": db_status,
        "nvidia_api_configured": bool(settings.NVIDIA_API_KEY),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/status")
async def system_status(db=Depends(get_db)):
    """Detailed system status."""
    from sqlalchemy import func
    from app.models import ContentBrief, ScrapedContent, GeneratedVideo, CompetitorAccount
    
    try:
        # Count records
        briefs_count = await db.execute(
            text("SELECT COUNT(*) FROM content_briefs")
        )
        briefs_count = briefs_count.scalar()
        
        content_count = await db.execute(
            text("SELECT COUNT(*) FROM scraped_content")
        )
        content_count = content_count.scalar()
        
        videos_count = await db.execute(
            text("SELECT COUNT(*) FROM generated_videos")
        )
        videos_count = videos_count.scalar()
        
        competitors_count = await db.execute(
            text("SELECT COUNT(*) FROM competitor_accounts")
        )
        competitors_count = competitors_count.scalar()
        
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        briefs_count = 0
        content_count = 0
        videos_count = 0
        competitors_count = 0
    
    return {
        "database": {
            "status": db_status,
            "content_briefs": briefs_count,
            "scraped_content": content_count,
            "generated_videos": videos_count,
            "competitor_accounts": competitors_count,
        },
        "configuration": {
            "nvidia_api": bool(settings.NVIDIA_API_KEY),
            "pexels_api": bool(settings.PEXELS_API_KEY),
            "pixabay_api": bool(settings.PIXABAY_API_KEY),
            "meta_api": bool(settings.META_ACCESS_TOKEN),
            "youtube_api": bool(settings.YOUTUBE_API_KEY),
        },
        "timestamp": datetime.now().isoformat(),
    }