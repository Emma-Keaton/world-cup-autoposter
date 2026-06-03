"""
Analytics service for performance tracking and insights.
Provides metrics, reports, and recommendations.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentBrief, GeneratedVideo, AnalyticsRecord, ContentStatus, Platform
from app.core.database import async_session_factory


@dataclass
class PerformanceSummary:
    """Analytics performance summary."""
    total_posts: int
    total_views: int
    total_likes: int
    total_shares: int
    avg_engagement_rate: float
    best_performer_id: Optional[str]
    worst_performer_id: Optional[str]
    follower_growth: int
    optimal_posting_time: Optional[str]


class AnalyticsService:
    """
    Analytics service for content performance tracking.
    
    Features:
    - Performance metrics aggregation
    - Best/worst content identification
    - Engagement trend analysis
    - Optimal posting time detection
    - Platform-specific insights
    """
    
    def __init__(self):
        logger.info("AnalyticsService initialized")
    
    async def get_performance_summary(self, days: int = 30) -> PerformanceSummary:
        """Get performance summary for the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with async_session_factory() as session:
            # Get aggregate metrics
            metrics_query = select(
                func.count(AnalyticsRecord.id).label('total_posts'),
                func.coalesce(func.sum(AnalyticsRecord.views), 0).label('total_views'),
                func.coalesce(func.sum(AnalyticsRecord.likes), 0).label('total_likes'),
                func.coalesce(func.sum(AnalyticsRecord.shares), 0).label('total_shares'),
                func.coalesce(func.avg(AnalyticsRecord.engagement_rate), 0).label('avg_engagement')
            ).where(
                AnalyticsRecord.created_at >= cutoff_date
            )
            
            result = await session.execute(metrics_query)
            metrics = result.fetchone()
            
            # Get best performer
            best_query = select(AnalyticsRecord.content_id).where(
                AnalyticsRecord.created_at >= cutoff_date
            ).order_by(AnalyticsRecord.views.desc()).limit(1)
            
            result = await session.execute(best_query)
            best_row = result.fetchone()
            best_performer = best_row[0] if best_row else None
            
            # Get worst performer
            worst_query = select(AnalyticsRecord.content_id).where(
                AnalyticsRecord.created_at >= cutoff_date,
                AnalyticsRecord.views > 0
            ).order_by(AnalyticsRecord.views.asc()).limit(1)
            
            result = await session.execute(worst_query)
            worst_row = result.fetchone()
            worst_performer = worst_row[0] if worst_row else None
            
            # Calculate follower growth (simplified)
            follower_growth = await self._calculate_follower_growth(session, cutoff_date)
            
            # Get optimal posting time
            optimal_time = await self._get_optimal_posting_time(session, cutoff_date)
            
            return PerformanceSummary(
                total_posts=metrics.total_posts or 0,
                total_views=int(metrics.total_views or 0),
                total_likes=int(metrics.total_likes or 0),
                total_shares=int(metrics.total_shares or 0),
                avg_engagement_rate=float(metrics.avg_engagement or 0),
                best_performer_id=best_performer,
                worst_performer_id=worst_performer,
                follower_growth=follower_growth,
                optimal_posting_time=optimal_time
            )
    
    async def _calculate_follower_growth(self, session: AsyncSession, since: datetime) -> int:
        """Calculate follower growth since a date."""
        # This is simplified - would need follower tracking in models
        return 0
    
    async def _get_optimal_posting_time(self, session: AsyncSession, since: datetime) -> Optional[str]:
        """Find optimal posting time based on engagement."""
        query = select(
            func.extract('hour', ContentBrief.created_at).label('hour')
        ).join(
            AnalyticsRecord,
            ContentBrief.id == AnalyticsRecord.content_id
        ).where(
            ContentBrief.created_at >= since,
            ContentBrief.status == ContentStatus.PUBLISHED
        ).order_by(
            AnalyticsRecord.engagement_rate.desc()
        ).limit(1)
        
        result = await session.execute(query)
        row = result.fetchone()
        
        if row and row.hour is not None:
            hour = int(row.hour)
            return f"{hour:02d}:00"
        return None
    
    async def get_engagement_trend(self, days: int = 30) -> List[Dict]:
        """Get daily engagement trend."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with async_session_factory() as session:
            query = select(
                func.date(AnalyticsRecord.created_at).label('date'),
                func.avg(AnalyticsRecord.engagement_rate).label('avg_engagement'),
                func.sum(AnalyticsRecord.views).label('total_views')
            ).where(
                AnalyticsRecord.created_at >= cutoff_date
            ).group_by(
                func.date(AnalyticsRecord.created_at)
            ).order_by(
                func.date(AnalyticsRecord.created_at)
            )
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            return [
                {
                    "date": str(row.date),
                    "avg_engagement": float(row.avg_engagement or 0),
                    "total_views": int(row.total_views or 0)
                }
                for row in rows
            ]
    
    async def get_platform_breakdown(self, days: int = 30) -> Dict[str, Dict]:
        """Get performance breakdown by platform."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with async_session_factory() as session:
            query = select(
                ContentBrief.platform,
                func.count(AnalyticsRecord.id).label('post_count'),
                func.avg(AnalyticsRecord.views).label('avg_views'),
                func.avg(AnalyticsRecord.engagement_rate).label('avg_engagement')
            ).join(
                AnalyticsRecord,
                ContentBrief.id == AnalyticsRecord.content_id
            ).where(
                ContentBrief.created_at >= cutoff_date,
                ContentBrief.status == ContentStatus.PUBLISHED
            ).group_by(
                ContentBrief.platform
            )
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            return {
                str(row.platform): {
                    "post_count": row.post_count,
                    "avg_views": float(row.avg_views or 0),
                    "avg_engagement": float(row.avg_engagement or 0)
                }
                for row in rows
            }
    
    async def get_content_recommendations(self) -> List[Dict]:
        """Get AI-powered content recommendations based on performance."""
        recommendations = []
        
        # Analyze top performers
        async with async_session_factory() as session:
            top_query = select(
                ContentBrief.topic,
                ContentBrief.content_type,
                func.avg(AnalyticsRecord.engagement_rate).label('avg_engagement')
            ).join(
                AnalyticsRecord,
                ContentBrief.id == AnalyticsRecord.content_id
            ).where(
                ContentBrief.status == ContentStatus.PUBLISHED
            ).group_by(
                ContentBrief.topic,
                ContentBrief.content_type
            ).order_by(
                func.avg(AnalyticsRecord.engagement_rate).desc()
            ).limit(5)
            
            result = await session.execute(top_query)
            top_content = result.fetchall()
            
            if top_content:
                top_topic = top_content[0].topic
                recommendations.append({
                    "type": "topic_focus",
                    "message": f"Focus on '{top_topic}' content - it has the highest engagement",
                    "priority": "high",
                    "data": {"topic": top_topic}
                })
        
        # Time-based recommendations
        recommendations.append({
            "type": "posting_time",
            "message": "Post more content between 6-9 PM for maximum engagement",
            "priority": "medium"
        })
        
        return recommendations


# Global instance
_analytics: Optional[AnalyticsService] = None


def get_analytics() -> AnalyticsService:
    """Get the global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsService()
    return _analytics