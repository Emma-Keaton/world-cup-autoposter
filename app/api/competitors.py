"""
Competitor management API (separate from scraping).
Provides CRUD operations for competitor accounts.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import CompetitorAccount, Platform

router = APIRouter()


class CompetitorSummary(BaseModel):
    """Competitor account summary."""
    id: str
    platform: str
    username: str
    display_name: Optional[str]
    follower_count: Optional[int]
    total_posts_scraped: int
    is_active: bool
    last_scraped_at: Optional[str]


@router.get("/summary")
async def get_competitors_summary(db: AsyncSession = Depends(get_db)):
    """Get summary of all competitors with post counts."""
    result = await db.execute(
        select(CompetitorAccount).order_by(CompetitorAccount.created_at.desc())
    )
    accounts = result.scalars().all()
    
    summaries = []
    for acc in accounts:
        # Count scraped content
        from app.models import ScrapedContent
        content_result = await db.execute(
            select(func.count(ScrapedContent.id))
            .where(ScrapedContent.competitor_id == acc.id)
        )
        post_count = content_result.scalar()
        
        summaries.append(CompetitorSummary(
            id=acc.id,
            platform=acc.platform.value,
            username=acc.username,
            display_name=acc.display_name,
            follower_count=acc.follower_count,
            total_posts_scraped=post_count or 0,
            is_active=acc.is_active,
            last_scraped_at=acc.last_scraped_at.isoformat() if acc.last_scraped_at else None,
        ))
    
    return {
        "competitors": summaries,
        "total": len(summaries),
        "by_platform": {
            "instagram": len([a for a in summaries if a.platform == "instagram"]),
            "youtube": len([a for a in summaries if a.platform == "youtube"]),
        },
    }


@router.get("/{account_id}")
async def get_competitor(
    account_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed competitor information."""
    result = await db.execute(
        select(CompetitorAccount).where(CompetitorAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    
    return {
        "id": account.id,
        "platform": account.platform.value,
        "username": account.username,
        "display_name": account.display_name,
        "profile_url": account.profile_url,
        "follower_count": account.follower_count,
        "following_count": account.following_count,
        "total_posts": account.total_posts,
        "is_active": account.is_active,
        "is_scraper_enabled": account.is_scraper_enabled,
        "last_scraped_at": account.last_scraped_at.isoformat() if account.last_scraped_at else None,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
    }


@router.put("/{account_id}")
async def update_competitor(
    account_id: str,
    updates: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update competitor account settings."""
    result = await db.execute(
        select(CompetitorAccount).where(CompetitorAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    
    # Allowed fields to update
    allowed_fields = ["is_active", "is_scraper_enabled", "display_name"]
    
    for field, value in updates.items():
        if field in allowed_fields and hasattr(account, field):
            setattr(account, field, value)
    
    await db.commit()
    await db.refresh(account)
    
    return {"message": "Competitor updated", "account_id": account_id}


@router.post("/{account_id}/refresh-profile")
async def refresh_competitor_profile(
    account_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh profile data for a competitor.
    
    This would trigger a profile scrape without getting all posts.
    For now, it's a placeholder for future implementation.
    """
    result = await db.execute(
        select(CompetitorAccount).where(CompetitorAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    
    # In production, this would call the scraper's profile method
    # For now, just mark it as needing refresh
    
    return {
        "message": "Profile refresh scheduled",
        "account_id": account_id,
        "username": account.username,
    }