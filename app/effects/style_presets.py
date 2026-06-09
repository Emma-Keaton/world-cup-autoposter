"""Skill 7: Style Presets — Signature look packages.

One-click visual style presets applying coordinated effect sets across
the entire video. Each preset creates a distinctive look so reposted
videos don't look identical to the source.

Inspired by: PixiJS ColorMatrixFilter presets, Three.js PBR materials,
Vanta.js color themes, Modern Web Design trends, Blender texture baking.
"""

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType


# ---------------------------------------------------------------------------
# Preset definitions  (PixiJS ColorMatrixFilter pattern)
# ---------------------------------------------------------------------------

PRESETS = {
    "broadcast_pro": {
        "label": "Broadcast Pro",
        "filters": [
            # Subtle vignette
            "vignette=angle=0.3",
            # Warm color grade
            "colorbalance=rs=0.02:gs=0.01",
            # Slight sharpness
            "unsharp=5:5:0.8:5:5:0",
            # Letterbox bars (2.35:1 aspect via pad)
        ],
        "pre_filters": [],
        "description": "Clean broadcast look with subtle vignette and warm grade",
    },
    "dramatic_cinema": {
        "label": "Dramatic Cinema",
        "filters": [
            # Teal-orange split tone (shadows cool, highlights warm)
            "colorbalance=rs=0.05:gs=-0.02:bs=-0.06:rh=0.04:gh=-0.01:bh=0.03",
            # Heavy vignette
            "vignette=angle=0.5",
            # Contrast boost
            "eq=contrast=1.15:saturation=0.85",
            # Film grain via noise
            "noise=c0s=3:c0f=t+u",
        ],
        "pre_filters": [],
        "description": "Teal-orange cinema look with grain and heavy vignette",
    },
    "neon_night": {
        "label": "Neon Night",
        "filters": [
            # Boosted saturation
            "eq=saturation=1.4",
            # Dark crushed blacks
            "eq=gamma=0.85",
            # Glow on brights (unsharp with high amount)
            "unsharp=6:6:3:6:6:0",
            # Chromatic edge highlights
            "colorbalance=rs=0.04:bs=0.03",
        ],
        "pre_filters": [],
        "description": "High-saturation neon look for night matches",
    },
    "vintage_film": {
        "label": "Vintage Film",
        "filters": [
            # Kodachrome-style desaturation + warmth
            "eq=saturation=0.7:contrast=1.1",
            "colorbalance=rs=0.06:gs=0.02:bs=-0.04",
            # Film grain
            "noise=c0s=5:c0f=t+u",
            # Slight vertical jitter (crop oscillation)
        ],
        "pre_filters": [],
        "description": "Kodachrome vintage look with grain and warm desaturation",
    },
    "high_energy": {
        "label": "High Energy",
        "filters": [
            # Saturation + contrast pop
            "eq=saturation=1.3:contrast=1.2",
            # Color vibrance
            "colorbalance=rs=0.03:gs=0.01",
            # Slight vignette
            "vignette=angle=0.25",
        ],
        "pre_filters": [],
        "description": "Punchy high-contrast look for TikTok/Reels",
    },
    "clean_minimal": {
        "label": "Clean Minimal",
        "filters": [
            # Neutral grade — just tiny contrast bump
            "eq=contrast=1.05",
            # Subtle shadow lift
            "eq=brightness=0.02",
        ],
        "pre_filters": [],
        "description": "Clean neutral grade with minimal processing",
    },
}


class StylePresetEffect(BaseEffect):
    """Applies a named style preset — coordinated filter chain for a signature look."""

    name = "style_preset"
    label = "Style Preset"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "One-click visual style preset"
    handled_tags = []  # Applied explicitly, not via tags

    def build(self, ctx: EffectContext) -> EffectResult:
        preset_name = ctx.extra_data.get("style_preset", "broadcast_pro")
        preset = PRESETS.get(preset_name, PRESETS["broadcast_pro"])

        # Scale filter intensity based on ctx.intensity
        filters = list(preset.get("filters", []))
        pre_filters = list(preset.get("pre_filters", []))

        # If intensity is low, skip the heaviest filters
        if ctx.intensity < 0.3:
            # Remove grain and glow for light editing
            filters = [f for f in filters if "noise" not in f and "unsharp=6:6:3" not in f]
        elif ctx.intensity < 0.6:
            # Moderate: keep everything but reduce parameters
            pass  # Full filter chain applies

        return EffectResult(
            pre_filters=pre_filters,
            filters=filters,
            metadata={"preset": preset_name, "label": preset["label"]},
        )


ALL_STYLE_EFFECTS = [StylePresetEffect]
