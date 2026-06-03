"""
Content analyzer for extracting viral patterns from scraped content.
Uses NVIDIA NIM API to analyze transcripts and identify successful hooks.
"""
import json
from typing import List, Dict, Any, Optional
from loguru import logger

from app.core.config import settings


class ContentAnalyzer:
    """
    Analyzes scraped content to extract viral patterns.
    
    Uses NVIDIA NIM API to:
    - Extract hook structures from transcripts
    - Identify content categories and themes
    - Analyze successful content patterns
    """
    
    def __init__(self):
        """Initialize the content analyzer."""
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = settings.NVIDIA_API_BASE_URL
    
    async def analyze_content(
        self,
        transcript: str,
        description: Optional[str] = None,
        title: Optional[str] = None,
        metrics: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Analyze content to extract viral elements.
        
        Args:
            transcript: Video transcript text
            description: Video description/caption
            title: Video title
            metrics: Engagement metrics (likes, views, etc.)
            
        Returns:
            Dictionary with extracted patterns and analysis
        """
        prompt = self._build_analysis_prompt(transcript, description, title, metrics)
        
        try:
            analysis = await self._call_nvidia_api(prompt)
            return analysis
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return self._fallback_analysis(transcript, description)
    
    def _build_analysis_prompt(
        self,
        transcript: str,
        description: Optional[str],
        title: Optional[str],
        metrics: Optional[Dict[str, int]]
    ) -> str:
        """Build the analysis prompt for the LLM."""
        
        metrics_text = ""
        if metrics:
            metrics_text = f"""
Engagement Metrics:
- Views: {metrics.get('views', 'N/A')}
- Likes: {metrics.get('likes', 'N/A')}
- Comments: {metrics.get('comments', 'N/A')}
"""
        
        return f"""You are a viral content analyst. Analyze this football/soccer social media content and extract the key elements that made it successful.

{metrics_text}
Title: {title or 'N/A'}
Description: {description or 'N/A'}

Transcript/Content:
{transcript or 'N/A'}

Extract and return JSON with this exact structure:
{{
    "hook": "The exact opening hook sentence (first 5-10 seconds)",
    "hook_type": "Type of hook (contrarian, question, bold claim, open loop, emotional)",
    "core_conflict": "The main conflict, controversy, or tension in the content",
    "emotional_triggers": ["list of emotional triggers used"],
    "content_structure": "Brief description of how the content flows",
    "cta": "Call-to-action used (if any)",
    "key_topics": ["main topics covered"],
    "content_category": "Category (news, analysis, storytelling, controversy, highlights, infographic)",
    "narrative_style": "First person, third person, dramatic, casual, etc.",
    "pacing": "Fast, medium, or slow paced delivery",
    "why_viral": "Explanation of why this content likely performed well",
    "viral_elements": ["specific elements that drove engagement"]
}}

Be specific and actionable. Focus on what makes this content shareable and engaging."""
    
    async def _call_nvidia_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call NVIDIA NIM API for content analysis.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            Parsed JSON response
        """
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a viral content analyst specializing in football/soccer social media. Return only valid JSON with no markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            return self._parse_json_response(content)
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM response."""
        # Clean markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return self._empty_analysis()
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure."""
        return {
            "hook": "",
            "hook_type": "unknown",
            "core_conflict": "",
            "emotional_triggers": [],
            "content_structure": "",
            "cta": "",
            "key_topics": [],
            "content_category": "unknown",
            "narrative_style": "",
            "pacing": "medium",
            "why_viral": "",
            "viral_elements": [],
        }
    
    def _fallback_analysis(
        self,
        transcript: Optional[str],
        description: Optional[str]
    ) -> Dict[str, Any]:
        """Fallback analysis when LLM fails."""
        text = (transcript or "") + " " + (description or "")
        text = text.lower()
        
        # Simple keyword detection
        emotional_triggers = []
        if "shocking" in text:
            emotional_triggers.append("shock")
        if "amazing" in text or "incredible" in text:
            emotional_triggers.append("amazement")
        if "controvers" in text:
            emotional_triggers.append("controversy")
        
        return {
            "hook": "",
            "hook_type": "unknown",
            "core_conflict": "",
            "emotional_triggers": emotional_triggers,
            "content_structure": "",
            "cta": "",
            "key_topics": [],
            "content_category": "unknown",
            "narrative_style": "",
            "pacing": "medium",
            "why_viral": "",
            "viral_elements": [],
        }
    
    async def extract_trending_topics(
        self,
        scraped_contents: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract trending topics from multiple scraped content items.
        
        Args:
            scraped_contents: List of ScrapedContent objects
            
        Returns:
            List of trending topics with frequency and viral scores
        """
        # Group by topics/categories
        topic_counts = {}
        topic_viral_scores = {}
        
        for content in scraped_contents:
            category = getattr(content, "content_category", "unknown") or "unknown"
            viral_score = getattr(content, "viral_score", 0) or 0
            
            if category not in topic_counts:
                topic_counts[category] = 0
                topic_viral_scores[category] = []
            
            topic_counts[category] += 1
            topic_viral_scores[category].append(viral_score)
        
        # Calculate average viral score per topic
        trending = []
        for topic, count in topic_counts.items():
            avg_viral = sum(topic_viral_scores[topic]) / len(topic_viral_scores[topic])
            trending.append({
                "topic": topic,
                "count": count,
                "avg_viral_score": round(avg_viral, 2),
            })
        
        # Sort by viral score
        trending.sort(key=lambda x: x["avg_viral_score"], reverse=True)
        
        return trending
    
    async def get_viral_hook_examples(
        self,
        scraped_contents: List[Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get examples of viral hooks from scraped content.
        
        Args:
            scraped_contents: List of ScrapedContent objects
            limit: Maximum number of examples
            
        Returns:
            List of hook examples with metadata
        """
        # Filter for high-performing content
        high_performers = [
            c for c in scraped_contents
            if getattr(c, "viral_score", 0) and c.viral_score > 5.0
        ]
        
        # Sort by viral score
        high_performers.sort(key=lambda x: x.viral_score, reverse=True)
        
        examples = []
        for content in high_performers[:limit]:
            examples.append({
                "hook": getattr(content, "hook_text", "") or "N/A",
                "title": getattr(content, "title", ""),
                "viral_score": content.viral_score,
                "views": getattr(content, "views"),
                "engagement_rate": self._calculate_engagement_rate(content),
                "platform": getattr(content, "platform", "").value,
            })
        
        return examples
    
    def _calculate_engagement_rate(self, content: Any) -> Optional[float]:
        """Calculate engagement rate for content."""
        views = getattr(content, "views", 0) or 0
        if views == 0:
            return None
        
        likes = getattr(content, "likes", 0) or 0
        comments = getattr(content, "comments", 0) or 0
        shares = getattr(content, "shares", 0) or 0
        
        return round(((likes + comments + shares) / views) * 100, 2)