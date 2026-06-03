"""
Utility functions for the application.
"""
import re
import hashlib
from datetime import datetime
from typing import Optional, List
from slugify import slugify


def generate_slug(text: str) -> str:
    """Generate a URL-friendly slug from text."""
    return slugify(text)


def generate_content_hash(content: str) -> str:
    """Generate a unique hash for content deduplication."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def calculate_viral_score(
    likes: int,
    comments: int,
    shares: int,
    views: int,
    follower_count: int
) -> float:
    """
    Calculate viral score based on engagement rate.
    
    Formula: (Engagement / Followers) * (Engagement Quality Multiplier)
    """
    if follower_count == 0 or views == 0:
        return 0.0
    
    engagement = likes + comments + shares
    engagement_rate = (engagement / views) * 100
    
    # Quality multiplier: shares weighted higher
    quality_score = (likes * 1 + comments * 2 + shares * 3) / engagement if engagement > 0 else 0
    
    viral_score = engagement_rate * (quality_score / 6)  # Normalize
    
    return round(viral_score, 2)


def parse_duration(duration_str: str) -> int:
    """Parse duration string (e.g., '1:30', '00:01:30') to seconds."""
    if not duration_str:
        return 0
    
    parts = duration_str.split(":")
    parts = [int(p) for p in parts]
    
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    
    return 0


def format_views_count(views: int) -> str:
    """Format view count for display (e.g., 1500000 -> '1.5M')."""
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    elif views >= 1_000:
        return f"{views / 1_000:.1f}K"
    return str(views)


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep emojis
    text = re.sub(r'[^\w\s\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF.!,?\'\"@#$%&*()\[\]{}\-–—:"/\\–—]', '', text, flags=re.UNICODE)
    
    return text.strip()


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text."""
    hashtags = re.findall(r'#\w+', text)
    return hashtags


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in seconds."""
    word_count = len(text.split())
    return max(1, int((word_count / words_per_minute) * 60))


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL."""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(url_pattern.match(url)) if url else False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = f"{name[:255-len(ext)-1]}.{ext}" if ext else sanitized[:255]
    
    return sanitized


def parse_iso_datetime(iso_string: Optional[str]) -> Optional[datetime]:
    """Parse ISO format datetime string."""
    if not iso_string:
        return None
    
    try:
        # Handle various ISO formats
        iso_string = iso_string.replace('Z', '+00:00')
        return datetime.fromisoformat(iso_string)
    except (ValueError, AttributeError):
        return None