"""
Instagram scraper using Instaloader.
Scrapes Reels, descriptions, and engagement metrics from competitor accounts.
"""
import asyncio
import instaloader
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger

from app.core.database import async_session_factory
from app.models import CompetitorAccount, ScrapedContent, Platform, ContentType
from app.core.utils import calculate_viral_score, clean_text, generate_content_hash


class InstagramScraper:
    """
    Instagram scraper using Instaloader.
    
    Uses dummy accounts or session files to avoid rate limiting.
    Follows Agent-Reach approach: CLI-driven, bypasses expensive APIs.
    """
    
    def __init__(self, session_file: Optional[str] = None):
        """
        Initialize Instagram scraper.
        
        Args:
            session_file: Path to Instaloader session file for authenticated scraping
        """
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=True,
            download_comments=False,
            compress_json=False,
        )
        
        self.session_file = session_file
    
    async def login(self, username: str, password: str) -> bool:
        """
        Login to Instagram to enable higher rate limits.
        
        Args:
            username: Instagram username
            password: Instagram password
            
        Returns:
            True if login successful
        """
        try:
            # Login and save session
            self.loader.login(username, password)
            self.loader.save_session_to_file(self.session_file)
            logger.info(f"Instagram login successful for {username}")
            return True
        except Exception as e:
            logger.error(f"Instagram login failed: {e}")
            return False
    
    async def load_session(self, session_file: Optional[str] = None) -> bool:
        """
        Load existing session file to avoid re-login.
        
        Args:
            session_file: Path to session file
        """
        session_file = session_file or self.session_file
        if session_file:
            try:
                self.loader.load_session_from_file(session_file)
                logger.info(f"Loaded Instagram session from {session_file}")
                return True
            except Exception as e:
                logger.warning(f"Failed to load session: {e}")
        return False
    
    async def scrape_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Scrape profile information for a competitor account.
        
        Args:
            username: Instagram username
            
        Returns:
            Profile data dictionary
        """
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            return {
                "username": profile.username,
                "display_name": profile.full_name,
                "profile_url": f"https://instagram.com/{username}",
                "follower_count": profile.followers,
                "following_count": profile.followees,
                "total_posts": profile.mediacount,
                "biography": profile.biography,
                "is_verified": profile.is_verified,
                "is_private": profile.is_private,
            }
        except Exception as e:
            logger.error(f"Failed to scrape profile {username}: {e}")
            return None
    
    async def scrape_recent_posts(
        self,
        username: str,
        limit: int = 50,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Scrape recent posts/reels from a competitor account.
        
        Args:
            username: Instagram username
            limit: Maximum number of posts to scrape
            days_back: Only scrape posts from last N days
            
        Returns:
            List of post data dictionaries
        """
        posts_data = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            posts = profile.get_posts()
            
            count = 0
            for post in posts:
                if count >= limit:
                    break
                
                # Check date
                if post.date_utc and post.date_utc < cutoff_date:
                    break
                
                # Only process video posts (Reels)
                if not post.is_video:
                    continue
                
                post_data = {
                    "platform": Platform.INSTAGRAM,
                    "content_type": ContentType.REEL if post.is_video else ContentType.CAROUSEL,
                    "external_id": post.shortcode,
                    "url": f"https://instagram.com/p/{post.shortcode}/",
                    "title": post.title[:500] if post.title else None,
                    "description": clean_text(post.caption) if post.caption else None,
                    "thumbnail_url": post.thumbnail_url,
                    "views": post.video_view_count if post.is_video else None,
                    "likes": post.likes,
                    "comments": post.comments,
                    "shares": None,  # Instagram doesn't expose share count via Instaloader
                    "duration_seconds": int(post.video_duration) if post.is_video else None,
                    "published_at": post.date_utc,
                    "scraped_at": datetime.now(),
                }
                
                posts_data.append(post_data)
                count += 1
                
                logger.debug(f"Scraped Instagram post {post.shortcode} from @{username}")
            
            logger.info(f"Scraped {count} posts from @{username}")
            
        except Exception as e:
            logger.error(f"Failed to scrape posts from @{username}: {e}")
        
        return posts_data
    
    async def save_to_database(
        self,
        username: str,
        posts_data: List[Dict[str, Any]],
        profile_data: Optional[Dict[str, Any]] = None
    ) -> tuple[Optional[CompetitorAccount], int]:
        """
        Save scraped data to database.
        
        Args:
            username: Instagram username
            posts_data: List of post data
            profile_data: Optional profile data
            
        Returns:
            Tuple of (CompetitorAccount, number of posts saved)
        """
        async with async_session_factory() as session:
            # Update or create competitor account
            result = await session.execute(
                db_select(CompetitorAccount).where(
                    CompetitorAccount.platform == Platform.INSTAGRAM,
                    CompetitorAccount.username == username,
                )
            )
            competitor = result.scalar_one_or_none()
            
            if not competitor:
                competitor = CompetitorAccount(
                    platform=Platform.INSTAGRAM,
                    username=username,
                )
                session.add(competitor)
            
            # Update profile data
            if profile_data:
                competitor.display_name = profile_data.get("display_name")
                competitor.profile_url = profile_data.get("profile_url")
                competitor.follower_count = profile_data.get("follower_count")
                competitor.following_count = profile_data.get("following_count")
                competitor.total_posts = profile_data.get("total_posts")
                competitor.last_scraped_at = datetime.now()
            
            # Save posts
            saved_count = 0
            for post_data in posts_data:
                # Check for duplicates
                existing = await session.execute(
                    db_select(ScrapedContent).where(
                        ScrapedContent.platform == Platform.INSTAGRAM,
                        ScrapedContent.external_id == post_data["external_id"],
                    )
                )
                
                if existing.scalar_one_or_none():
                    continue
                
                # Calculate viral score
                if profile_data and profile_data.get("follower_count"):
                    viral_score = calculate_viral_score(
                        likes=post_data.get("likes") or 0,
                        comments=post_data.get("comments") or 0,
                        shares=post_data.get("shares") or 0,
                        views=post_data.get("views") or 0,
                        follower_count=profile_data.get("follower_count", 0),
                    )
                    post_data["viral_score"] = viral_score
                
                scraped_content = ScrapedContent(
                    competitor_id=competitor.id,
                    **post_data,
                )
                session.add(scraped_content)
                saved_count += 1
            
            await session.commit()
            logger.info(f"Saved {saved_count} posts for @{username}")
            
            return competitor, saved_count


# SQLAlchemy import helper
from sqlalchemy import select as db_select