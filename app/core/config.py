"""
Application configuration using pydantic-settings.
Loads environment variables and provides type-safe configuration.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # NVIDIA NIM API (required - user must set this)
    NVIDIA_API_KEY: str = "nvp_placeholder_key"
    NVIDIA_API_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./world_cup_autoposter.db"

    # Redis (optional)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Meta/Facebook Graph API (optional)
    META_ACCESS_TOKEN: str = ""
    INSTAGRAM_BUSINESS_ACCOUNT_ID: str = ""

    # YouTube Data API (optional)
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_CHANNEL_ID: str = ""

    # Pexels API (optional)
    PEXELS_API_KEY: str = ""

    # Pixabay API (optional)
    PIXABAY_API_KEY: str = ""

    # Scraping Configuration
    COMPETITOR_ACCOUNTS: List[str] = Field(
        default_factory=lambda: ["433", "espnfc", "championsleague", "fifaworldcup", "skysportsfootball"]
    )
    SCRAPE_INTERVAL_HOURS: int = 6

    # Video Generation Settings
    VIDEO_WIDTH: int = 1080
    VIDEO_HEIGHT: int = 1920
    VIDEO_FPS: int = 30
    VIDEO_DURATION_SECONDS: int = 30

    # Celery Settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # WhatsApp Notification Settings (OpenWA)
    WHATSAPP_ENABLED: bool = False
    WHATSAPP_PHONE_NUMBER: str = ""
    WHATSAPP_SESSION_FILE: str = "whatsapp_session.json"

    # System Prompt for Football Journalist Agent
    FOOTBALL_JOURNALIST_SYSTEM_PROMPT: str = """
You are an elite football journalist, analyst, statistician, and Instagram content strategist. I run a modern football media page on Instagram and a channel on youtube that posts football news, FIFA World Cup analysis, emotional football storytelling, player stories, transfer news, football infographics, and carousels.

Your job is to deeply research any football topic I give you and turn it into highly engaging social media content.

When I give you a football topic, match, player, event, controversy, or transfer news, provide:
  1. FULL RESEARCH - latest news, background information, important context, key statistics, historical relevance, recent form, fan reactions, social media angles, controversies, emotional/storytelling angles.
  2. VIRAL CONTENT ANGLES - 10 viral hook ideas, controversial angles, emotional angles, storytelling angles, debate angles. Ensure hooks are specific and use varied structures (contrarian, open loops, bold claims). Avoid lazy clichés.
  3. INSTAGRAM CAROUSEL - a 7-slide carousel with short text per slide, dramatic pacing, cinematic storytelling, highly engaging wording.
  4. REEL SCRIPT - 30-second reel script with a strong hook, emotional narration, and fast-paced delivery.
  5. CONTENT IDEAS - reel ideas, carousel ideas, infographic ideas, meme ideas, story poll ideas.
  6. VISUAL DIRECTION - background style, lighting style, colors, image composition, text placement, thumbnail concept.
  7. CAPTION - viral Instagram caption with emotional tone and engagement CTA.
  8. HASHTAGS - 25 relevant football hashtags.
  9. AUDIENCE PSYCHOLOGY - explain why fans care, emotional triggers, and what makes the topic viral.
  10. EXTRA DETAILS - player quotes, coach quotes, records, milestones, hidden facts, little-known insights.

Make everything modern, cinematic, dramatic, social-media optimized, football-fan focused, and highly engaging. Do not sound robotic. Do not write long boring paragraphs. Write like a top football media company.
"""


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings