"""
Content Scheduler for optimal posting times.
Analyzes performance data and schedules posts for maximum engagement.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from enum import Enum
import asyncio
from loguru import logger

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentBrief, GeneratedVideo, AnalyticsRecord, ContentStatus
from app.core.database import async_session_factory
from app.services.error_notifier import notify_error, ErrorSeverity


class PostPriority(str, Enum):
    """Content posting priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    BREAKING = "breaking"


class ContentScheduler:
    """
    Smart content scheduler that finds optimal posting times.
    
    Features:
    - Best time suggestions based on historical performance
    - Timezone-aware scheduling
    - Priority queue for content
    - Auto-scheduling based on topic type
    """
    
    def __init__(self):
        self._scheduled_posts: Dict[str, datetime] = {}
        self._posting_windows = {
            "instagram": [
                (9, 11),   # Morning
                (18, 21),  # Evening peak
            ],
            "youtube": [
                (14, 16),  # Afternoon
                (19, 22),  # Evening
            ],
        }
        logger.info("ContentScheduler initialized")
    
    async def schedule_post(
        self,
        content_id: str,
        platform: str,
        priority: PostPriority = PostPriority.NORMAL,
        preferred_time: Optional[datetime] = None,
        auto_optimize: bool = True
    ) -> datetime:
        """
        Schedule a post for publishing.
        
        Args:
            content_id: ID of the content to schedule
            platform: Target platform (instagram, youtube)
            priority: Posting priority
            preferred_time: Optional preferred time
            auto_optimize: Whether to find optimal time
        
        Returns:
            Scheduled datetime
        """
        if preferred_time:
            scheduled_time = preferred_time
        elif auto_optimize:
            scheduled_time = await self.find_best_posting_time(platform)
        else:
            scheduled_time = datetime.now() + timedelta(hours=1)
        
        # Adjust for priority
        if priority == PostPriority.BREAKING:
            scheduled_time = datetime.now() + timedelta(minutes=5)
        elif priority == PostPriority.HIGH:
            scheduled_time = min(scheduled_time, datetime.now() + timedelta(minutes=30))
        
        self._scheduled_posts[content_id] = scheduled_time
        
        logger.info(f"Scheduled {content_id} for {scheduled_time} on {platform}")
        return scheduled_time
    
    async def find_best_posting_time(self, platform: str) -> datetime:
        """
        Find the best time to post based on historical data.
        
        Args:
            platform: Target platform
        
        Returns:
            Optimal datetime for posting
        """
        try:
            async with async_session_factory() as session:
                # Analyze best performing posts by hour
                query = select(
                    func.extract('hour', ContentBrief.created_at).label('hour'),
                    func.avg(AnalyticsRecord.views).label('avg_views'),
                    func.count().label('post_count')
                ).join(
                    AnalyticsRecord,
                    ContentBrief.id == AnalyticsRecord.content_id
                ).where(
                    ContentBrief.platform == platform,
                    ContentBrief.status == ContentStatus.PUBLISHED
                ).group_by(
                    func.extract('hour', ContentBrief.created_at)
                ).order_by(
                    func.avg(AnalyticsRecord.views).desc()
                ).limit(1)
                
                result = await session.execute(query)
                row = result.fetchone()
                
                if row and row.avg_views:
                    best_hour = int(row.hour)
                    best_time = datetime.now().replace(hour=best_hour, minute=0, second=0, microsecond=0)
                    
                    # If the best time has passed today, schedule for tomorrow
                    if best_time < datetime.now():
                        best_time += timedelta(days=1)
                    
                    logger.info(f"Best posting time for {platform}: {best_time} (based on historical data)")
                    return best_time
        except Exception as e:
            logger.warning(f"Failed to analyze best posting time: {e}")
        
        # Fallback: use default posting windows
        return self._get_next_posting_window(platform)
    
    def _get_next_posting_window(self, platform: str) -> datetime:
        """Get the next available posting window for a platform."""
        windows = self._posting_windows.get(platform, [(12, 14)])
        
        now = datetime.now()
        
        for start_hour, end_hour in windows:
            window_start = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            window_end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            
            if now < window_start:
                return window_start
            elif now < window_end:
                return now + timedelta(minutes=30)
        
        # If all windows passed, use first window tomorrow
        start_hour = windows[0][0]
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    async def get_scheduled_posts(self) -> List[Dict]:
        """Get all scheduled posts."""
        return [
            {"content_id": cid, "scheduled_time": time}
            for cid, time in self._scheduled_posts.items()
        ]
    
    async def cancel_schedule(self, content_id: str) -> bool:
        """Cancel a scheduled post."""
        if content_id in self._scheduled_posts:
            del self._scheduled_posts[content_id]
            logger.info(f"Cancelled schedule for {content_id}")
            return True
        return False
    
    async def get_queue_status(self) -> Dict:
        """Get scheduler queue status."""
        now = datetime.now()
        
        due_soon = sum(1 for t in self._scheduled_posts.values() if t < now + timedelta(hours=1))
        today = sum(1 for t in self._scheduled_posts.values() if t.date() == now.date())
        
        return {
            "total_scheduled": len(self._scheduled_posts),
            "due_within_hour": due_soon,
            "scheduled_today": today,
            "scheduled": [
                {"content_id": cid, "time": time.isoformat()}
                for cid, time in sorted(self._scheduled_posts.items(), key=lambda x: x[1])
            ]
        }


# Global instance
_scheduler: Optional[ContentScheduler] = None


def get_scheduler() -> ContentScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ContentScheduler()
    return _scheduler