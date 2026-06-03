"""
Competitor scraping and management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import CompetitorAccount, Platform, ScrapedContent
from app.scraping.instagram import InstagramScraper
from app.scraping.youtube import YouTubeScraper
from app.scraping.analyzer import ContentAnalyzer

router = APIRouter()


class CreateCompetitorRequest(BaseModel):
    """Request to add a competitor account."""
    platform: str = Field(..., description="Platform: instagram or youtube")
    username: str = Field(..., description="Username/handle", min_length=1)
    is_scraper_enabled: bool = Field(True, description="Enable scraping for this account")


class ScrapeCompetitorRequest(BaseModel):
    """Request to scrape a competitor."""
    limit: int = Field(50, ge=1, le=200, description="Max posts to scrape")
    days_back: int = Field(30, ge=1, le=365, description="Days of content to scrape")


class CompetitorResponse(BaseModel):
    """Competitor account response."""
    id: str
    platform: str
    username: str
    display_name: Optional[str]
    follower_count: Optional[int]
    is_active: bool
    is_scraper_enabled: bool
    last_scraped_at: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/accounts")
async def list_competitors(
    platform: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all competitor accounts."""
    query = select(CompetitorAccount).order_by(CompetitorAccount.created_at.desc())
    
    if platform:
        platform_enum = Platform(platform.lower())
        query = query.where(CompetitorAccount.platform == platform_enum)
    
    if active_only:
        query = query.where(CompetitorAccount.is_active == True)
    
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return {
        "accounts": [
            CompetitorResponse(
                id=acc.id,
                platform=acc.platform.value,
                username=acc.username,
                display_name=acc.display_name,
                follower_count=acc.follower_count,
                is_active=acc.is_active,
                is_scraper_enabled=acc.is_scraper_enabled,
                last_scraped_at=acc.last_scraped_at.isoformat() if acc.last_scraped_at else None,
            )
            for acc in accounts
        ],
        "total": len(accounts),
    }


@router.post("/accounts", response_model=CompetitorResponse)
async def create_competitor(
    request: CreateCompetitorRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add a new competitor account to track."""
    try:
        platform = Platform(request.platform.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform: {request.platform}. Must be 'instagram' or 'youtube'",
        )
    
    # Check for duplicates
    result = await db.execute(
        select(CompetitorAccount).where(
            CompetitorAccount.platform == platform,
            CompetitorAccount.username == request.username,
        )
    )
    
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Competitor already exists",
        )
    
    # Create new account
    account = CompetitorAccount(
        platform=platform,
        username=request.username,
        is_scraper_enabled=request.is_scraper_enabled,
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    return CompetitorResponse(
        id=account.id,
        platform=account.platform.value,
        username=account.username,
        display_name=account.display_name,
        follower_count=account.follower_count,
        is_active=account.is_active,
        is_scraper_enabled=account.is_scraper_enabled,
        last_scraped_at=None,
    )


@router.delete("/accounts/{account_id}")
async def delete_competitor(
    account_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Remove a competitor account."""
    result = await db.execute(
        select(CompetitorAccount).where(CompetitorAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    
    await db.delete(account)
    await db.commit()
    
    return {"message": "Competitor deleted"}


@router.post("/accounts/{account_id}/scrape")
async def scrape_competitor(
    account_id: str,
    request: ScrapeCompetitorRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Scrape content from a competitor account.
    
    Runs in background to avoid timeout.
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
    
    if not account.is_scraper_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scraping is disabled for this account",
        )
    
    # Schedule scraping task
    background_tasks.add_task(
        _run_scraping_task,
        account_id=account_id,
        platform=account.platform.value,
        username=account.username,
        limit=request.limit,
        days_back=request.days_back,
    )
    
    return {
        "message": "Scraping started",
        "account": account.username,
        "estimated_time": "2-5 minutes",
    }


async def _run_scraping_task(
    account_id: str,
    platform: str,
    username: str,
    limit: int,
    days_back: int,
):
    """Background task to scrape competitor content."""
    from app.core.database import async_session_factory
    from datetime import datetime
    
    try:
        if platform == "instagram":
            scraper = InstagramScraper()
            
            # Try to load session
            await scraper.load_session()
            
            # Scrape profile
            profile_data = await scraper.scrape_profile(username)
            
            # Scrape posts
            posts_data = await scraper.scrape_recent_posts(
                username=username,
                limit=limit,
                days_back=days_back,
            )
            
            # Save to database
            async with async_session_factory() as session:
                result = await session.execute(
                    select(CompetitorAccount).where(CompetitorAccount.id == account_id)
                )
                account = result.scalar_one()
                
                # Update account
                if profile_data:
                    account.display_name = profile_data.get("display_name")
                    account.follower_count = profile_data.get("follower_count")
                    account.last_scraped_at = datetime.now()
                
                # Save posts
                for post_data in posts_data:
                    scraped = ScrapedContent(
                        competitor_id=account_id,
                        **post_data,
                    )
                    session.add(scraped)
                
                await session.commit()
        
        elif platform == "youtube":
            scraper = YouTubeScraper()
            
            channel_url = f"https://youtube.com/@{username}"
            
            # Scrape videos
            videos_data = await scraper.scrape_channel_videos(
                channel_url=channel_url,
                limit=limit,
                days_back=days_back,
            )
            
            # Save to database
            async with async_session_factory() as session:
                result = await session.execute(
                    select(CompetitorAccount).where(CompetitorAccount.id == account_id)
                )
                account = result.scalar_one()
                account.last_scraped_at = datetime.now()
                
                for video_data in videos_data:
                    scraped = ScrapedContent(
                        competitor_id=account_id,
                        **video_data,
                    )
                    session.add(scraped)
                
                await session.commit()
        
    except Exception as e:
        # Log error but don't fail silently
        import logging
        logging.error(f"Scraping task failed for {username}: {e}")


@router.get("/content")
async def list_scraped_content(
    platform: Optional[str] = None,
    min_viral_score: Optional[float] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List scraped content with filters."""
    query = select(ScrapedContent).order_by(
        ScrapedContent.scraped_at.desc()
    )
    
    if platform:
        platform_enum = Platform(platform.lower())
        query = query.where(ScrapedContent.platform == platform_enum)
    
    if min_viral_score is not None:
        query = query.where(ScrapedContent.viral_score >= min_viral_score)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    content_items = result.scalars().all()
    
    # Get total count
    count_query = select(ScrapedContent)
    if platform:
        count_query = count_query.where(ScrapedContent.platform == platform_enum)
    if min_viral_score is not None:
        count_query = count_query.where(ScrapedContent.viral_score >= min_viral_score)
    
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    return {
        "content": [
            {
                "id": c.id,
                "platform": c.platform.value,
                "title": c.title,
                "url": c.url,
                "views": c.views,
                "likes": c.likes,
                "comments": c.comments,
                "viral_score": c.viral_score,
                "published_at": c.published_at.isoformat() if c.published_at else None,
            }
            for c in content_items
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/analysis/trends")
async def analyze_trends(
    days_back: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Analyze trending content from scraped data."""
    analyzer = ContentAnalyzer()
    
    # Get recent high-performing content
    from datetime import timedelta, datetime
    cutoff = datetime.now() - timedelta(days=days_back)
    
    result = await db.execute(
        select(ScrapedContent).where(
            ScrapedContent.published_at >= cutoff,
            ScrapedContent.viral_score >= 5.0,
        )
        .order_by(ScrapedContent.viral_score.desc())
        .limit(50)
    )
    
    content_items = result.scalars().all()
    
    # Analyze trending topics
    trending = await analyzer.extract_trending_topics(content_items)
    
    # Get hook examples
    hook_examples = await analyzer.get_viral_hook_examples(content_items)
    
    return {
        "trending_topics": trending[:10],
        "hook_examples": hook_examples[:10],
        "analyzed_count": len(content_items),
        "period_days": days_back,
    }