"""
Content Orchestrator - coordinates all agents in the content generation pipeline.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.core.database import async_session_factory
from app.models import ContentBrief, ContentStatus, ScrapedContent, Platform
from app.llm.agents import StrategyAgent, JournalistAgent, SEOAgent, ProductionAgent
from app.llm.nvidia_client import NVIDIAClient
from sqlalchemy import select, func


class ContentOrchestrator:
    """
    Orchestrates the multi-agent content generation system.
    
    Pipeline:
    1. Strategy Agent analyzes trends and competitor content
    2. Journalist Agent generates creative brief
    3. SEO Agent optimizes metadata
    4. Production Agent reviews and approves
    """
    
    def __init__(self):
        self.strategy_agent = StrategyAgent()
        self.journalist_agent = JournalistAgent()
        self.seo_agent = SEOAgent()
        self.production_agent = ProductionAgent()
        self.nvidia = NVIDIAClient()
    
    async def generate_content(
        self,
        topic: str,
        auto_approve: bool = False,
        include_trend_analysis: bool = True,
    ) -> ContentBrief:
        """
        Generate complete content brief for a topic.
        
        Args:
            topic: Football topic to create content about
            auto_approve: Skip production review if True
            include_trend_analysis: Include trend analysis in generation
            
        Returns:
            Generated ContentBrief object
        """
        logger.info(f"Starting content generation for topic: {topic}")
        
        async with async_session_factory() as session:
            # Step 1: Get relevant competitor content
            if include_trend_analysis:
                result = await session.execute(
                    select(ScrapedContent)
                    .where(ScrapedContent.viral_score.isnot(None))
                    .order_by(ScrapedContent.viral_score.desc())
                    .limit(50)
                )
                scraped_content = result.scalars().all()
                
                # Step 2: Strategy Agent analyzes trends
                trend_context = await self.strategy_agent.analyze_trends(
                    scraped_content=scraped_content,
                    topic=topic
                )
                
                # Step 3: Find similar content for reference
                similar_content = await self.strategy_agent.get_similar_content(
                    topic=topic,
                    scraped_content=scraped_content,
                    limit=5
                )
            else:
                trend_context = None
                similar_content = None
            
            # Step 4: Journalist Agent generates creative brief
            creative_brief = await self.journalist_agent.generate_creative_brief(
                topic=topic,
                trend_context=trend_context,
                similar_content=similar_content,
            )
            
            # Step 5: SEO Agent optimizes metadata
            seo_optimized = await self.seo_agent.optimize_metadata(
                topic=topic,
                content=creative_brief,
                platform="instagram",
            )
            
            # Merge SEO improvements
            creative_brief["caption"] = seo_optimized.get("description", creative_brief.get("caption", ""))
            creative_brief["target_keywords"] = seo_optimized.get("tags", [])
            
            # Step 6: Production Agent review (if not auto-approve)
            if not auto_approve:
                review = await self.production_agent.review_content(
                    content_brief=creative_brief
                )
                
                # Apply suggestions if any
                if review.get("suggestions"):
                    logger.info(f"Production suggestions: {len(review['suggestions'])} items")
                    creative_brief["production_notes"] = review
            
            # Create database record
            brief = ContentBrief(
                topic=topic,
                status=ContentStatus.GENERATED if auto_approve else ContentStatus.REVIEW,
                research=creative_brief.get("research"),
                viral_angles=creative_brief.get("viral_angles"),
                carousel_script=creative_brief.get("carousel_script"),
                reel_script=creative_brief.get("reel_script"),
                content_ideas=creative_brief.get("content_ideas"),
                visual_direction=creative_brief.get("visual_direction"),
                caption=creative_brief.get("caption"),
                hashtags=creative_brief.get("hashtags"),
                audience_psychology=creative_brief.get("audience_psychology"),
                extra_details=creative_brief.get("extra_details"),
                target_keywords=creative_brief.get("target_keywords"),
                inspired_by_content_ids=[c.get("id") for c in (similar_content or [])],
            )
            
            session.add(brief)
            await session.commit()
            await session.refresh(brief)
            
            logger.info(f"Content brief created: {brief.id}")
            return brief
    
    async def generate_batch(
        self,
        topics: List[str],
        max_concurrent: int = 3,
    ) -> List[ContentBrief]:
        """
        Generate content for multiple topics concurrently.
        
        Args:
            topics: List of topics
            max_concurrent: Maximum concurrent generations
            
        Returns:
            List of generated ContentBrief objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(topic: str) -> ContentBrief:
            async with semaphore:
                return await self.generate_content(topic)
        
        tasks = [generate_with_semaphore(topic) for topic in topics]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        briefs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate for topic '{topics[i]}': {result}")
            else:
                briefs.append(result)
        
        return briefs
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current content queue status.
        
        Returns:
            Queue statistics and pending items
        """
        async with async_session_factory() as session:
            # Count by status
            result = await session.execute(
                select(ContentBrief.status, func.count(ContentBrief.id))
                .group_by(ContentBrief.status)
            )
            
            status_counts = {
                str(row.status): count
                for row in result.all()
            }
            
            # Get pending items
            pending = await session.execute(
                select(ContentBrief)
                .where(ContentBrief.status == ContentStatus.REVIEW)
                .order_by(ContentBrief.created_at.desc())
                .limit(10)
            )
            
            pending_items = [{
                "id": brief.id,
                "topic": brief.topic,
                "created_at": brief.created_at.isoformat(),
                "status": brief.status.value,
            } for brief in pending.scalars().all()]
            
            return {
                "total": sum(status_counts.values()),
                "by_status": status_counts,
                "pending_review": pending_items,
            }
    
    async def approve_brief(self, brief_id: str) -> ContentBrief:
        """
        Approve a content brief for production.
        
        Args:
            brief_id: ContentBrief ID
            
        Returns:
            Updated ContentBrief
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(ContentBrief).where(ContentBrief.id == brief_id)
            )
            brief = result.scalar_one_or_none()
            
            if not brief:
                raise ValueError(f"Brief not found: {brief_id}")
            
            brief.status = ContentStatus.GENERATED
            await session.commit()
            await session.refresh(brief)
            
            logger.info(f"Brief approved: {brief_id}")
            return brief
    
    async def reject_brief(
        self,
        brief_id: str,
        reason: Optional[str] = None
    ) -> ContentBrief:
        """
        Reject a content brief.
        
        Args:
            brief_id: ContentBrief ID
            reason: Rejection reason
            
        Returns:
            Updated ContentBrief
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(ContentBrief).where(ContentBrief.id == brief_id)
            )
            brief = result.scalar_one_or_none()
            
            if not brief:
                raise ValueError(f"Brief not found: {brief_id}")
            
            brief.status = ContentStatus.FAILED
            if reason:
                brief.production_notes = {"rejection_reason": reason}
            
            await session.commit()
            await session.refresh(brief)
            
            logger.info(f"Brief rejected: {brief_id} - {reason}")
            return brief
    
    async def get_trending_feed(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get trending topics based on competitor analysis.
        
        Args:
            limit: Maximum topics to return
            
        Returns:
            List of trending topics with metadata
        """
        async with async_session_factory() as session:
            # Get recent high-performing content
            result = await session.execute(
                select(ScrapedContent)
                .where(
                    ScrapedContent.published_at >= func.now() - func.interval('30 days'),
                    ScrapedContent.viral_score >= 5.0,
                )
                .order_by(ScrapedContent.viral_score.desc())
                .limit(limit)
            )
            
            content_items = result.scalars().all()
            
            # Extract topics from titles/descriptions
            # (Would use NLP in production, simple keyword extraction here)
            topics = []
            seen = set()
            
            for content in content_items:
                # Use title as topic proxy
                topic = getattr(content, "title", "")[:50]
                if topic and topic not in seen:
                    topics.append({
                        "topic": topic,
                        "viral_score": content.viral_score,
                        "platform": content.platform.value if hasattr(content.platform, "value") else str(content.platform),
                        "url": content.url,
                    })
                    seen.add(topic)
            
            return topics