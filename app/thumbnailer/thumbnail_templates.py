"""
Thumbnail Templates - Pre-designed styles for quick thumbnails.
"""
from typing import Dict, List, Any


class ThumbnailTemplates:
    """
    Pre-designed thumbnail templates for different content types.
    
    Templates include:
    - Color schemes
    - Text styles
    - Layouts
    - Effects
    """
    
    TEMPLATES = {
        "football_goal": {
            "name": "⚽ Goal Highlight",
            "description": "For goal highlights and amazing strikes",
            "colors": {
                "title": "#FFFFFF",
                "title_outline": "#000000",
                "subtitle": "#FBBF24",
                "accent": "#22C55E",
                "background_overlay": "rgba(26, 77, 46, 0.4)",
            },
            "style": "bold",
            "text_size_multiplier": 1.2,
            "effects": ["high_contrast", "saturation_boost", "vignette"],
        },
        "football_card": {
            "name": "🟥 Red Card/Controversy",
            "description": "For red cards, fouls, controversial moments",
            "colors": {
                "title": "#FFFFFF",
                "title_outline": "#000000",
                "subtitle": "#EF4444",
                "accent": "#DC2626",
                "background_overlay": "rgba(220, 38, 38, 0.3)",
            },
            "style": "dramatic",
            "text_size_multiplier": 1.3,
            "effects": ["high_contrast", "color_grade_dramatic"],
        },
        "football_transfer": {
            "name": "🔄 Transfer News",
            "description": "For transfer announcements and rumors",
            "colors": {
                "title": "#FFFFFF",
                "title_outline": "#000000",
                "subtitle": "#3B82F6",
                "accent": "#2563EB",
                "background_overlay": "rgba(59, 130, 246, 0.3)",
            },
            "style": "bold",
            "text_size_multiplier": 1.1,
            "effects": ["moderate_contrast", "sharpen"],
        },
        "world_cup": {
            "name": "🏆 World Cup Special",
            "description": "For World Cup content with gold theme",
            "colors": {
                "title": "#FCD34D",
                "title_outline": "#000000",
                "subtitle": "#FFFFFF",
                "accent": "#FBBF24",
                "background_overlay": "rgba(251, 191, 36, 0.25)",
            },
            "style": "dramatic",
            "text_size_multiplier": 1.4,
            "effects": ["gold_gradient", "high_contrast", "glow"],
        },
        "breaking_news": {
            "name": "🚨 Breaking News",
            "description": "For urgent news and announcements",
            "colors": {
                "title": "#FFFFFF",
                "title_outline": "#DC2626",
                "subtitle": "#FBBF24",
                "accent": "#EF4444",
                "background_overlay": "rgba(239, 68, 68, 0.35)",
            },
            "style": "bold",
            "text_size_multiplier": 1.3,
            "effects": ["flash_overlay", "high_contrast"],
        },
        "interview": {
            "name": "🎤 Interview/Quote",
            "description": "For player quotes and interviews",
            "colors": {
                "title": "#FFFFFF",
                "title_outline": "#000000",
                "subtitle": "#A855F7",
                "accent": "#9333EA",
                "background_overlay": "rgba(168, 85, 247, 0.25)",
            },
            "style": "minimal",
            "text_size_multiplier": 1.0,
            "effects": ["soft_blur", "moderate_contrast"],
        },
        "champions_league": {
            "name": "⭐ Champions League",
            "description": "For UCL content with dark blue theme",
            "colors": {
                "title": "#FFFFFF",
                "title_outline": "#1E3A8A",
                "subtitle": "#3B82F6",
                "accent": "#1E40AF",
                "background_overlay": "rgba(30, 64, 175, 0.4)",
            },
            "style": "dramatic",
            "text_size_multiplier": 1.2,
            "effects": ["star_overlay", "blue_grade", "high_contrast"],
        },
        "compilation": {
            "name": "🎬 Compilation/Top 10",
            "description": "For compilation videos and top 10s",
            "colors": {
                "title": "#FBBF24",
                "title_outline": "#000000",
                "subtitle": "#FFFFFF",
                "accent": "#F59E0B",
                "background_overlay": "rgba(245, 158, 11, 0.3)",
            },
            "style": "bold",
            "text_size_multiplier": 1.2,
            "effects": ["film_grain", "saturation_boost"],
        },
    }
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available templates."""
        return [
            {
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "style": template["style"],
            }
            for template_id, template in self.TEMPLATES.items()
        ]
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get a specific template by ID."""
        if template_id not in self.TEMPLATES:
            return self.TEMPLATES["football_goal"]  # Default
        
        return self.TEMPLATES[template_id]