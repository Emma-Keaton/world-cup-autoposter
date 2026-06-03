"""
Database models for the World Cup Autoposter system.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Type
from enum import Enum

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

# Try to import VECTOR for PostgreSQL, use Type decorator as fallback for SQLite
try:
    from sqlalchemy.dialects.postgresql import VECTOR
except ImportError:
    # SQLite fallback - just use a regular type decorator
    from sqlalchemy import TypeDecorator
    class VECTOR(TypeDecorator):
        impl = String
        cache_ok = True
        def __init__(self, dim=None):
            super().__init__(512)  # Store as string for SQLite


class Platform(str, Enum):
    """Supported social media platforms."""
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class ContentType(str, Enum):
    """Content type classification."""
    REEL = "reel"
    SHORT = "short"
    CAROUSEL = "carousel"
    STORY = "story"


class ContentStatus(str, Enum):
    """Content lifecycle status."""
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEW = "review"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class CompetitorAccount(Base):
    """Competitor social media account tracking."""
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200))
    profile_url: Mapped[Optional[str]] = mapped_column(String(500))
    follower_count: Mapped[Optional[int]] = mapped_column(Integer)
    following_count: Mapped[Optional[int]] = mapped_column(Integer)
    total_posts: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Tracking metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_scraper_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    scraped_content: Mapped[List["ScrapedContent"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    
    __tablename__ = "competitor_accounts"
    __table_args__ = (
        UniqueConstraint("platform", "username", name="uq_competitor_platform_username"),
        Index("ix_competitor_platform_active", "platform", "is_active"),
    )


class ScrapedContent(Base):
    """Scraped content from competitor accounts."""
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id: Mapped[str] = mapped_column(
        ForeignKey("competitor_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Content metadata
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(SQLEnum(ContentType))
    external_id: Mapped[str] = mapped_column(String(200), index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Content data
    title: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    transcript: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Engagement metrics
    views: Mapped[Optional[int]] = mapped_column(Integer)
    likes: Mapped[Optional[int]] = mapped_column(Integer)
    comments: Mapped[Optional[int]] = mapped_column(Integer)
    shares: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Analysis
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    viral_score: Mapped[Optional[float]] = mapped_column(Float)
    hook_text: Mapped[Optional[str]] = mapped_column(String(500))
    content_category: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Embeddings for similarity search (pgvector)
    description_embedding: Mapped[Optional[bytes]] = mapped_column(VECTOR(dim=1024))
    
    # Metadata
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    competitor: Mapped["CompetitorAccount"] = relationship(back_populates="scraped_content")
    
    __tablename__ = "scraped_content"
    __table_args__ = (
        Index("ix_scraped_viral_score", "viral_score", postgresql_using="btree"),
        Index("ix_scraped_published", "published_at"),
    )


class ContentBrief(Base):
    """Generated content brief from the multi-agent system."""
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Content details
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ContentStatus] = mapped_column(SQLEnum(ContentStatus), default=ContentStatus.DRAFT)
    
    # Generated content (JSON structure for flexibility)
    research: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    viral_angles: Mapped[Optional[List[Dict[str, str]]]] = mapped_column(JSON)
    carousel_script: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    reel_script: Mapped[Optional[str]] = mapped_column(Text)
    content_ideas: Mapped[Optional[List[Dict[str, str]]]] = mapped_column(JSON)
    visual_direction: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON)
    caption: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    audience_psychology: Mapped[Optional[str]] = mapped_column(Text)
    extra_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # SEO & Metadata
    target_keywords: Mapped[Optional[List[str]]] = mapped_column(JSON)
    estimated_views: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Scheduling
    scheduled_publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # References
    inspired_by_content_ids: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    generated_videos: Mapped[List["GeneratedVideo"]] = relationship(
        back_populates="content_brief", cascade="all, delete-orphan"
    )
    
    __tablename__ = "content_briefs"


class GeneratedVideo(Base):
    """Generated video files ready for publishing."""
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_brief_id: Mapped[str] = mapped_column(
        ForeignKey("content_briefs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Video metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # File paths
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(1000))
    subtitle_path: Mapped[Optional[str]] = mapped_column(String(1000))
    audio_path: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # Video specs
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[Optional[int]] = mapped_column(Integer, default=1080)
    height: Mapped[Optional[int]] = mapped_column(Integer, default=1920)
    fps: Mapped[Optional[int]] = mapped_column(Integer, default=30)
    
    # Generation details
    tts_voice: Mapped[Optional[str]] = mapped_column(String(100))
    background_music: Mapped[Optional[str]] = mapped_column(String(200))
    assets_used: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Status
    status: Mapped[ContentStatus] = mapped_column(SQLEnum(ContentStatus), default=ContentStatus.DRAFT)
    published_video_id: Mapped[Optional[str]] = mapped_column(String(200))
    published_platform: Mapped[Optional[Platform]] = mapped_column(SQLEnum(Platform))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    content_brief: Mapped["ContentBrief"] = relationship(back_populates="generated_videos")
    
    __tablename__ = "generated_videos"


class AnalyticsRecord(Base):
    """Published content performance analytics."""
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[str] = mapped_column(
        ForeignKey("generated_videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Metrics
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Calculated
    engagement_rate: Mapped[Optional[float]] = mapped_column(Float)
    viral_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Timeline
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __tablename__ = "analytics_records"
    __table_args__ = (
        Index("ix_analytics_recorded", "recorded_at"),
    )


class SystemLog(Base):
    """Application logs and audit trail."""
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    module: Mapped[Optional[str]] = mapped_column(String(100))
    action: Mapped[Optional[str]] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    __tablename__ = "system_logs"