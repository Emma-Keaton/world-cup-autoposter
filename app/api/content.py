"""
Content generation and management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import ContentBrief, ContentStatus, GeneratedVideo
from app.llm.orchestrator import ContentOrchestrator

router = APIRouter()


class GenerateContentRequest(BaseModel):
    """Request to generate content for a topic."""
    topic: str = Field(..., description="Football topic to create content about", min_length=3)
    auto_approve: bool = Field(False, description="Skip production review")
    include_trends: bool = Field(True, description="Include trend analysis")


class ContentBriefResponse(BaseModel):
    """Response with content brief details."""
    id: str
    topic: str
    status: str
    reel_script: Optional[str]
    caption: Optional[str]
    hashtags: Optional[List[str]]
    created_at: str
    
    class Config:
        from_attributes = True


class ContentQueueResponse(BaseModel):
    """Content queue status."""
    total: int
    by_status: dict
    pending_review: List[dict]


@router.post("/generate", response_model=ContentBriefResponse)
async def generate_content(
    request: GenerateContentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate content brief for a football topic.
    
    Uses the multi-agent system to create:
    - Research and viral angles
    - Reel script (30 seconds)
    - Instagram caption and hashtags
    - Visual direction
    """
    orchestrator = ContentOrchestrator()
    
    try:
        brief = await orchestrator.generate_content(
            topic=request.topic,
            auto_approve=request.auto_approve,
            include_trend_analysis=request.include_trends,
        )
        
        return ContentBriefResponse(
            id=brief.id,
            topic=brief.topic,
            status=brief.status.value,
            reel_script=brief.reel_script,
            caption=brief.caption,
            hashtags=brief.hashtags,
            created_at=brief.created_at.isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}",
        )


@router.post("/generate/batch")
async def generate_content_batch(
    topics: List[str],
    max_concurrent: int = Query(3, le=10),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate content for multiple topics concurrently.
    
    Returns list of generated brief IDs.
    """
    orchestrator = ContentOrchestrator()
    
    try:
        briefs = await orchestrator.generate_batch(
            topics=topics,
            max_concurrent=max_concurrent,
        )
        
        return {
            "generated": len(briefs),
            "brief_ids": [b.id for b in briefs],
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch generation failed: {str(e)}",
        )


@router.get("/queue")
async def get_content_queue(db: AsyncSession = Depends(get_db)):
    """Get current content queue status."""
    orchestrator = ContentOrchestrator()
    status = await orchestrator.get_queue_status()
    
    return ContentQueueResponse(**status)


@router.get("/briefs")
async def list_briefs(
    status: Optional[ContentStatus] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List content briefs with optional status filter."""
    query = select(ContentBrief).order_by(ContentBrief.created_at.desc())
    
    if status:
        query = query.where(ContentBrief.status == status)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    briefs = result.scalars().all()
    
    return {
        "briefs": [
            {
                "id": b.id,
                "topic": b.topic,
                "status": b.status.value,
                "created_at": b.created_at.isoformat(),
            }
            for b in briefs
        ],
        "total": len(briefs),
        "offset": offset,
        "limit": limit,
    }


@router.get("/briefs/{brief_id}")
async def get_brief(brief_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific content brief."""
    result = await db.execute(
        select(ContentBrief).where(ContentBrief.id == brief_id)
    )
    brief = result.scalar_one_or_none()
    
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brief not found",
        )
    
    return {
        "id": brief.id,
        "topic": brief.topic,
        "status": brief.status.value,
        "research": brief.research,
        "viral_angles": brief.viral_angles,
        "carousel_script": brief.carousel_script,
        "reel_script": brief.reel_script,
        "content_ideas": brief.content_ideas,
        "visual_direction": brief.visual_direction,
        "caption": brief.caption,
        "hashtags": brief.hashtags,
        "audience_psychology": brief.audience_psychology,
        "extra_details": brief.extra_details,
        "created_at": brief.created_at.isoformat(),
        "updated_at": brief.updated_at.isoformat(),
    }


@router.post("/briefs/{brief_id}/approve")
async def approve_brief(brief_id: str, db: AsyncSession = Depends(get_db)):
    """Approve a content brief for production."""
    orchestrator = ContentOrchestrator()
    
    try:
        brief = await orchestrator.approve_brief(brief_id)
        
        return {
            "id": brief.id,
            "status": brief.status.value,
            "message": "Brief approved for production",
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/briefs/{brief_id}/reject")
async def reject_brief(
    brief_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Reject a content brief."""
    orchestrator = ContentOrchestrator()
    
    try:
        brief = await orchestrator.reject_brief(brief_id, reason)
        
        return {
            "id": brief.id,
            "status": brief.status.value,
            "message": "Brief rejected",
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/trending")
async def get_trending_feed(
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get trending topics based on competitor analysis."""
    orchestrator = ContentOrchestrator()
    trending = await orchestrator.get_trending_feed(limit)
    
    return {"trending": trending}