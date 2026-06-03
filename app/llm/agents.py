"""
Multi-agent system for content generation.
Each agent has a specialized role in the content creation pipeline.
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.core.config import settings
from app.llm.nvidia_client import NVIDIAClient
from app.models import ContentBrief, ContentStatus


class StrategyAgent:
    """
    Strategy/Trends Agent.
    
    Analyzes competitor data and identifies viral topics and patterns.
    Manages the database of successful hooks and content structures.
    """
    
    def __init__(self):
        self.nvidia = NVIDIAClient()
    
    async def analyze_trends(
        self,
        scraped_content: List[Any],
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze scraped content to identify trending patterns.
        
        Args:
            scraped_content: List of ScrapedContent objects
            topic: Optional specific topic to focus on
            
        Returns:
            Trend analysis with topics, hooks, and recommendations
        """
        # Extract high-performing content
        high_performers = [
            c for c in scraped_content
            if getattr(c, "viral_score", 0) and c.viral_score > 5.0
        ][:20]
        
        # Prepare data for analysis
        content_summaries = []
        for content in high_performers:
            summary = {
                "title": getattr(content, "title", ""),
                "hook": getattr(content, "hook_text", ""),
                "viral_score": content.viral_score,
                "views": getattr(content, "views", 0),
                "platform": getattr(content, "platform", "").value if hasattr(content.platform, "value") else str(content.platform),
                "category": getattr(content, "content_category", ""),
            }
            content_summaries.append(summary)
        
        prompt = f"""Analyze these top-performing football content pieces and identify trends.

{'Focus topic: ' + topic if topic else 'Analyze all content categories.'}

Top performing content:
{json.dumps(content_summaries, indent=2)}

Return JSON with:
{{
    "trending_topics": ["list of trending topics/themes"],
    "successful_hook_patterns": ["hook structures that work"],
    "optimal_content_length": "recommended duration in seconds",
    "best_posting_times": ["recommended posting times"],
    "content_gaps": ["topics not being covered that could perform well"],
    "recommended_angle": "suggested approach for new content on this topic",
    "viral_potential_topics": ["topics with high viral potential right now"]
}}"""
        
        try:
            result = await self.nvidia.generate_with_json_schema(
                prompt=prompt,
                json_schema={
                    "type": "object",
                    "properties": {
                        "trending_topics": {"type": "array", "items": {"type": "string"}},
                        "successful_hook_patterns": {"type": "array", "items": {"type": "string"}},
                        "optimal_content_length": {"type": "string"},
                        "best_posting_times": {"type": "array", "items": {"type": "string"}},
                        "content_gaps": {"type": "array", "items": {"type": "string"}},
                        "recommended_angle": {"type": "string"},
                        "viral_potential_topics": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["trending_topics", "successful_hook_patterns", "recommended_angle"],
                }
            )
            
            logger.info(f"Strategy analysis complete: {len(result.get('trending_topics', []))} trends identified")
            return result
            
        except Exception as e:
            logger.error(f"Strategy agent failed: {e}")
            return self._fallback_trends()
    
    def _fallback_trends(self) -> Dict[str, Any]:
        """Fallback trends when analysis fails."""
        return {
            "trending_topics": ["FIFA World Cup", "Transfer News", "Match Analysis"],
            "successful_hook_patterns": ["Contrarian takes", "Breaking news format"],
            "optimal_content_length": "30-45 seconds",
            "best_posting_times": ["6-9 PM local time"],
            "content_gaps": ["Behind-the-scenes content"],
            "recommended_angle": "Focus on emotional storytelling",
            "viral_potential_topics": ["World Cup predictions"],
        }
    
    async def get_similar_content(
        self,
        topic: str,
        scraped_content: List[Any],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar content from the database for a given topic.
        
        Args:
            topic: Topic to find similar content for
            scraped_content: List of ScrapedContent objects
            limit: Maximum results
            
        Returns:
            List of similar content with metadata
        """
        # Simple keyword matching (would use embeddings in production)
        topic_lower = topic.lower()
        
        results = []
        for content in scraped_content:
            title = getattr(content, "title", "").lower()
            description = getattr(content, "description", "").lower() or ""
            
            # Check for keyword overlap
            topic_words = set(topic_lower.split())
            title_words = set(title.split())
            
            overlap = len(topic_words & title_words)
            
            if overlap > 0 or any(word in description for word in topic_words):
                results.append({
                    "id": getattr(content, "id", ""),
                    "title": getattr(content, "title", ""),
                    "viral_score": getattr(content, "viral_score", 0),
                    "platform": str(getattr(content, "platform", "")),
                    "url": getattr(content, "url", ""),
                })
        
        # Sort by viral score and limit
        results.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
        return results[:limit]


class JournalistAgent:
    """
    Journalist/Scripting Agent.
    
    Uses the Elite Football Journalist System Prompt to write the 10-point creative brief.
    """
    
    def __init__(self):
        self.nvidia = NVIDIAClient()
        self.system_prompt = settings.FOOTBALL_JOURNALIST_SYSTEM_PROMPT
    
    async def generate_creative_brief(
        self,
        topic: str,
        trend_context: Optional[Dict[str, Any]] = None,
        similar_content: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete 10-point creative brief for a topic.
        
        Args:
            topic: Football topic to create content about
            trend_context: Trend analysis from Strategy Agent
            similar_content: Similar high-performing content examples
            
        Returns:
            Complete creative brief as dictionary
        """
        context = self._build_context(trend_context, similar_content)
        
        prompt = f"""{context}

TOPIC: {topic}

Generate a complete 10-point creative brief with:
1. FULL RESEARCH - latest news, context, statistics, historical relevance
2. VIRAL CONTENT ANGLES - 10 viral hook ideas (contrarian, questions, bold claims)
3. INSTAGRAM CAROUSEL - 7-slide carousel with short text, dramatic pacing
4. REEL SCRIPT - 30-second reel with strong hook, emotional narration
5. CONTENT IDEAS - reel, carousel, infographic, meme, poll ideas
6. VISUAL DIRECTION - background style, colors, composition, thumbnail concept
7. CAPTION - viral caption with emotional tone and CTA
8. HASHTAGS - 25 relevant football hashtags
9. AUDIENCE PSYCHOLOGY - why fans care, emotional triggers
10. EXTRA DETAILS - quotes, records, milestones, hidden facts

Return as JSON matching this structure:
{{
    "research": {{"news": [], "context": "", "statistics": [], "historical_relevance": ""}},
    "viral_angles": [{"hook": "", "type": "", "description": ""}],
    "carousel_script": {{"slide_1": "", "slide_2": "", "slide_3": "", "slide_4": "", "slide_5": "", "slide_6": "", "slide_7": ""}},
    "reel_script": "",
    "content_ideas": [{"type": "", "description": ""}],
    "visual_direction": {{"background": "", "colors": "", "composition": "", "thumbnail": ""}},
    "caption": "",
    "hashtags": [],
    "audience_psychology": "",
    "extra_details": {{"quotes": [], "records": [], "facts": []}}
}}"""
        
        try:
            result = await self.nvidia.generate_with_json_schema(
                prompt=prompt,
                json_schema={
                    "type": "object",
                    "properties": {
                        "research": {"type": "object"},
                        "viral_angles": {"type": "array", "items": {"type": "object"}},
                        "carousel_script": {"type": "object"},
                        "reel_script": {"type": "string"},
                        "content_ideas": {"type": "array", "items": {"type": "object"}},
                        "visual_direction": {"type": "object"},
                        "caption": {"type": "string"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "audience_psychology": {"type": "string"},
                        "extra_details": {"type": "object"},
                    },
                    "required": ["research", "viral_angles", "reel_script", "caption", "hashtags"],
                },
                system_prompt=self.system_prompt,
            )
            
            logger.info(f"Creative brief generated for topic: {topic}")
            return result
            
        except Exception as e:
            logger.error(f"Journalist agent failed: {e}")
            return self._fallback_brief(topic)
    
    def _build_context(
        self,
        trend_context: Optional[Dict[str, Any]],
        similar_content: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Build context from trends and similar content."""
        context_parts = ["You are creating viral football content for Instagram and YouTube."]
        
        if trend_context:
            context_parts.append(f"\nTREND INSIGHTS:")
            context_parts.append(f"- Recommended angle: {trend_context.get('recommended_angle', '')}")
            context_parts.append(f"- Successful hooks: {', '.join(trend_context.get('successful_hook_patterns', [])[:3])}")
        
        if similar_content:
            context_parts.append(f"\nSIMILAR HIGH-PERFORMING CONTENT:")
            for content in similar_content[:3]:
                context_parts.append(f"- \"{content.get('title', '')}\" (viral score: {content.get('viral_score', 0)})")
        
        context_parts.append("\nMake everything modern, cinematic, dramatic, and highly engaging. Write like a top football media company.")
        
        return "\n".join(context_parts)
    
    def _fallback_brief(self, topic: str) -> Dict[str, Any]:
        """Fallback brief when generation fails."""
        return {
            "research": {"news": [f"Latest updates on {topic}"], "context": topic, "statistics": [], "historical_relevance": ""},
            "viral_angles": [{"hook": f"Breaking: {topic} update", "type": "news", "description": topic}],
            "carousel_script": {"slide_1": topic, "slide_2": "Details", "slide_3": "Analysis", "slide_4": "Stats", "slide_5": "Reaction", "slide_6": "What's Next", "slide_7": "Follow for more"},
            "reel_script": f"Breaking news about {topic}. This changes everything. Follow for updates.",
            "content_ideas": [{"type": "reel", "description": topic}],
            "visual_direction": {"background": "stadium", "colors": "green and white", "composition": "centered", "thumbnail": topic},
            "caption": f"{topic} - what do you think? 🔥⚽",
            "hashtags": ["#football", "#soccer", "#worldcup", "#fifa"],
            "audience_psychology": "Fans want breaking news and analysis",
            "extra_details": {"quotes": [], "records": [], "facts": []},
        }


class SEOAgent:
    """
    SEO/Metadata Agent.
    
    Optimizes captions, hashtags, and metadata for discoverability.
    """
    
    def __init__(self):
        self.nvidia = NVIDIAClient()
    
    async def optimize_metadata(
        self,
        topic: str,
        content: Dict[str, Any],
        platform: str = "instagram"
    ) -> Dict[str, Any]:
        """
        Optimize metadata for a specific platform.
        
        Args:
            topic: Content topic
            content: Generated content brief
            platform: Target platform (instagram, youtube, tiktok)
            
        Returns:
            Optimized metadata
        """
        prompt = f"""Optimize this content for maximum discoverability on {platform}.

Topic: {topic}

Current caption: {content.get('caption', '')}
Current hashtags: {', '.join(content.get('hashtags', []))}

Generate optimized:
1. Title/hook (under 60 characters for YouTube, under 100 for Instagram)
2. Description (SEO-optimized with keywords naturally integrated)
3. Hashtags (platform-specific, mix of high-volume and niche)
4. Tags/keywords (for YouTube)
5. Posting time recommendation

Return as JSON:
{{
    "title": "",
    "description": "",
    "optimized_hashtags": [],
    "tags": [],
    "best_posting_time": "",
    "seo_score": 0-100
}}"""
        
        try:
            result = await self.nvidia.generate_with_json_schema(
                prompt=prompt,
                json_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "optimized_hashtags": {"type": "array", "items": {"type": "string"}},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "best_posting_time": {"type": "string"},
                        "seo_score": {"type": "number"},
                    },
                    "required": ["title", "description", "optimized_hashtags"],
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"SEO agent failed: {e}")
            return self._fallback_metadata(content)
    
    def _fallback_metadata(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback metadata."""
        return {
            "title": content.get('reel_script', '')[:60],
            "description": content.get('caption', ''),
            "optimized_hashtags": content.get('hashtags', []),
            "tags": [],
            "best_posting_time": "6:00 PM",
            "seo_score": 50,
        }


class ProductionAgent:
    """
    Production & Review Agent.
    
    Governs the video compilation pipeline and reviews outputs.
    """
    
    def __init__(self):
        self.nvidia = NVIDIAClient()
    
    async def review_content(
        self,
        content_brief: Dict[str, Any],
        video_specs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Review generated content before publishing.
        
        Args:
            content_brief: Generated creative brief
            video_specs: Video generation specifications
            
        Returns:
            Review results with approval status and suggestions
        """
        prompt = f"""Review this football content brief for quality and viral potential.

REEL SCRIPT:
{content_brief.get('reel_script', '')}

CAPTION:
{content_brief.get('caption', '')}

VISUAL DIRECTION:
{content_brief.get('visual_direction', {})}

Evaluate on:
1. Hook strength (does it grab attention in 3 seconds?)
2. Story flow (is there clear narrative arc?)
3. Emotional impact (will fans care?)
4. Shareability (would fans send this to friends?)
5. Platform optimization (right length, format, style?)

Return JSON:
{{
    "approved": true/false,
    "scores": {{"hook": 1-10, "flow": 1-10, "emotion": 1-10, "shareability": 1-10}},
    "overall_score": 1-100,
    "issues": ["list of issues to fix"],
    "suggestions": ["specific improvements"],
    "viral_potential": "low/medium/high"
}}"""
        
        try:
            result = await self.nvidia.generate_with_json_schema(
                prompt=prompt,
                json_schema={
                    "type": "object",
                    "properties": {
                        "approved": {"type": "boolean"},
                        "scores": {"type": "object"},
                        "overall_score": {"type": "number"},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "suggestions": {"type": "array", "items": {"type": "string"}},
                        "viral_potential": {"type": "string"},
                    },
                    "required": ["approved", "overall_score"],
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Production review failed: {e}")
            return {
                "approved": True,
                "overall_score": 70,
                "issues": [],
                "suggestions": [],
                "viral_potential": "medium",
            }
    
    async def generate_thumbnail_prompt(
        self,
        topic: str,
        visual_direction: Dict[str, Any]
    ) -> str:
        """
        Generate AI image generation prompt for thumbnail.
        
        Args:
            topic: Content topic
            visual_direction: Visual direction from brief
            
        Returns:
            Image generation prompt
        """
        prompt = f"""Create a thumbnail image prompt for this football content.

Topic: {topic}
Visual direction: {json.dumps(visual_direction)}

Generate a detailed image generation prompt for an AI image generator (Midjourney/DALL-E 3).
Include: subject, composition, lighting, colors, style, text placement.

Return ONLY the image prompt, no explanations."""
        
        try:
            result = await self.nvidia.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return result
        except Exception as e:
            logger.error(f"Thumbnail prompt generation failed: {e}")
            return f"Football thumbnail for {topic}, dramatic lighting, bold colors"