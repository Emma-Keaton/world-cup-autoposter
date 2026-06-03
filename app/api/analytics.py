"""
Analytics and feedback loop endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import AnalyticsRecord, GeneratedVideo, ContentBrief, ContentStatus

router = APIRouter()


class AnalyticsUpdateRequest(BaseModel):
    """Request to update analytics for a video."""
    video_id: str
    views: int = Field(0, ge=0)
    likes: int = Field(0, ge=0)
    comments: int = Field(0, ge=0)
    shares: int = Field(0, ge=0)
    saves: Optional[int] = Field(0, ge=0)


class AnalyticsResponse(BaseModel):
    """Analytics response."""
    video_id: str
    views: int
    likes: int
    comments: int
    shares: int
    engagement_rate: Optional[float]
    viral_score: Optional[float]
    recorded_at: str


@router.post("/record")
async def record_analytics(
    request: AnalyticsUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Record analytics data for a published video."""
    # Verify video exists
    result = await db.execute(
        select(GeneratedVideo).where(GeneratedVideo.id == request.video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    
    # Calculate metrics
    total_engagement = request.likes + request.comments + request.shares
    engagement_rate = None
    viral_score = None
    
    if request.views > 0:
        engagement_rate = round((total_engagement / request.views) * 100, 2)
        
        # Viral score formula (same as scraping module)
        quality_score = (
            request.likes * 1 + 
            request.comments * 2 + 
            request.shares * 3
        ) / total_engagement if total_engagement > 0 else 0
        
        viral_score = round(engagement_rate * (quality_score / 6), 2)
    
    # Create analytics record
    record = AnalyticsRecord(
        video_id=request.video_id,
        views=request.views,
        likes=request.likes,
        comments=request.comments,
        shares=request.shares,
        saves=request.saves or 0,
        engagement_rate=engagement_rate,
        viral_score=viral_score,
    )
    
    db.add(record)
    await db.commit()
    await db.refresh(record)
    
    return AnalyticsResponse(
        video_id=request.video_id,
        views=request.views,
        likes=request.likes,
        comments=request.comments,
        shares=request.shares,
        engagement_rate=engagement_rate,
        viral_score=viral_score,
        recorded_at=record.recorded_at.isoformat(),
    )


@router.get("/videos/{video_id}")
async def get_video_analytics(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get analytics history for a video."""
    result = await db.execute(
        select(AnalyticsRecord)
        .where(AnalyticsRecord.video_id == video_id)
        .order_by(AnalyticsRecord.recorded_at.desc())
        .limit(30)
    )
    
    records = result.scalars().all()
    
    if not records:
        return {
            "video_id": video_id,
            "records": [],
            "latest": None,
        }
    
    # Get latest metrics
    latest = records[0]
    
    return {
        "video_id": video_id,
        "records": [
            {
                "views": r.views,
                "likes": r.likes,
                "comments": r.comments,
                "shares": r.shares,
                "engagement_rate": r.engagement_rate,
                "viral_score": r.viral_score,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in records
        ],
        "latest": {
            "views": latest.views,
            "likes": latest.likes,
            "comments": latest.comments,
            "shares": latest.shares,
            "engagement_rate": latest.engagement_rate,
            "viral_score": latest.viral_score,
            "recorded_at": latest.recorded_at.isoformat(),
        },
    }


@router.get("/overview")
async def get_analytics_overview(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get overall analytics summary."""
    cutoff = datetime.now() - timedelta(days=days)
    
    # Get all records in period
    result = await db.execute(
        select(AnalyticsRecord)
        .where(AnalyticsRecord.recorded_at >= cutoff)
        .order_by(AnalyticsRecord.recorded_at.desc())
    )
    
    records = result.scalars().all()
    
    if not records:
        return {
            "period_days": days,
            "total_videos": 0,
            "total_views": 0,
            "total_likes": 0,
            "avg_engagement_rate": 0,
            "avg_viral_score": 0,
            "best_performer": None,
        }
    
    # Aggregate metrics
    total_videos = len(set(r.video_id for r in records))
    total_views = sum(r.views for r in records)
    total_likes = sum(r.likes for r in records)
    total_comments = sum(r.comments for r in records)
    total_shares = sum(r.shares for r in records)
    
    # Get latest record per video for averages
    video_latest = {}
    for r in records:
        if r.video_id not in video_latest:
            video_latest[r.video_id] = r
    
    latest_records = list(video_latest.values())
    
    avg_engagement = sum(r.engagement_rate or 0 for r in latest_records) / len(latest_records)
    avg_viral = sum(r.viral_score or 0 for r in latest_records) / len(latest_records)
    
    # Find best performer
    best = max(latest_records, key=lambda r: r.viral_score or 0)
    
    # Get video title for best performer
    video_result = await db.execute(
        select(GeneratedVideo).where(GeneratedVideo.id == best.video_id)
    )
    best_video = video_result.scalar_one_or_none()
    
    return {
        "period_days": days,
        "total_videos": total_videos,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "avg_engagement_rate": round(avg_engagement, 2),
        "avg_viral_score": round(avg_viral, 2),
        "best_performer": {
            "video_id": best.video_id,
            "title": best_video.title if best_video else "Unknown",
            "viral_score": best.viral_score,
            "views": best.views,
        } if best_video else None,
    }


@router.get("/feedback")
async def get_feedback_for_generation(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance feedback to inform new content generation.
    
    Returns insights about what content structures are working.
    """
    # Get recent videos with analytics
    result = await db.execute(
        select(GeneratedVideo, AnalyticsRecord)
        .join(AnalyticsRecord, GeneratedVideo.id == AnalyticsRecord.video_id)
        .where(AnalyticsRecord.recorded_at >= datetime.now() - timedelta(days=60))
        .order_by(AnalyticsRecord.recorded_at.desc())
        .limit(limit)
    )
    
    rows = result.all()
    
    if not rows:
        return {
            "feedback": [],
            "summary": "No performance data available yet",
        }
    
    # Group by performance
    high_performers = []
    low_performers = []
    
    for video, analytics in rows:
        entry = {
            "video_id": video.id,
            "title": video.title,
            "topic": video.title,  # Topic is stored in title
            "viral_score": analytics.viral_score,
            "views": analytics.views,
            "engagement_rate": analytics.engagement_rate,
        }
        
        if analytics.viral_score and analytics.viral_score > 5:
            high_performers.append(entry)
        elif analytics.viral_score and analytics.viral_score < 3:
            low_performers.append(entry)
    
    # Generate feedback summary
    feedback_items = []
    
    if high_performers:
        feedback_items.append({
            "type": "success",
            "message": f"{len(high_performers)} content pieces scored above average",
            "examples": [p["title"][:50] for p in high_performers[:3]],
        })
    
    if low_performers:
        feedback_items.append({
            "type": "improvement",
            "message": f"{len(low_performers)} content pieces scored below average",
            "suggestion": "Consider adjusting hook style and posting times",
        })
    
    # Calculate averages
    all_scores = [a.viral_score for _, a in rows if a.viral_score]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    
    return {
        "feedback": feedback_items,
        "average_viral_score": round(avg_score, 2),
        "analyzed_videos": len(rows),
        "recommendation": "Prioritize emotional storytelling and contrarian hooks" if avg_score > 4 else "Focus on trending topics and stronger opening hooks",
    }


@router.delete("/videos/{video_id}")
async def clear_analytics(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Clear analytics records for a video."""
    result = await db.execute(
        select(AnalyticsRecord).where(AnalyticsRecord.video_id == video_id)
    )
    records = result.scalars().all()
    
    for record in records:
        await db.delete(record)
    
    await db.commit()
    
    return {"message": f"Deleted {len(records)} analytics records"}