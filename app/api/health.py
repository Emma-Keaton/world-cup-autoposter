"""
Health check and system status endpoints.
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings
from app.core.settings_service import get_setting

router = APIRouter()


@router.get("")
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

    # Check NVIDIA API from env or database
    nvidia_api = bool(settings.NVIDIA_API_KEY) or bool(await get_setting("nvidia_api_key", ""))

    return {
        "status": "ready" if db_status == "connected" else "not_ready",
        "database": db_status,
        "nvidia_api_configured": nvidia_api,
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

    # Check all API configurations from env or database
    pexels_api = bool(settings.PEXELS_API_KEY) or bool(await get_setting("pexels_api_key", ""))
    pixabay_api = bool(settings.PIXABAY_API_KEY) or bool(await get_setting("pixabay_api_key", ""))
    meta_api = bool(settings.META_ACCESS_TOKEN) or bool(await get_setting("meta_access_token", ""))
    youtube_api = bool(settings.YOUTUBE_API_KEY) or bool(await get_setting("youtube_api_key", ""))
    buffer_api = bool(await get_setting("buffer_api_key", ""))
    instagram_account = bool(await get_setting("instagram_business_account_id", ""))
    youtube_channel = bool(await get_setting("youtube_channel_id", ""))

    return {
        "database": {
            "status": db_status,
            "content_briefs": int(briefs_count) if briefs_count else 0,
            "scraped_content": int(content_count) if content_count else 0,
            "generated_videos": int(videos_count) if videos_count else 0,
            "competitor_accounts": int(competitors_count) if competitors_count else 0,
        },
        "configuration": {
            "nvidia_api": bool(settings.NVIDIA_API_KEY) or bool(await get_setting("nvidia_api_key", "")),
            "pexels_api": pexels_api,
            "pixabay_api": pixabay_api,
            "meta_api": meta_api,
            "youtube_api": youtube_api,
            "buffer_api": buffer_api,
            "instagram_account": instagram_account,
            "youtube_channel": youtube_channel,
        },
        "timestamp": datetime.now().isoformat(),
    }