"""Video effects engine for World Cup Autoposter.

Provides 7 effect skills that enhance downloaded/clipped videos:
1. Shot Visuals — Impact & camera effects
2. Motion Visuals — Flow & movement effects
3. Celebration Visuals — Goal & victory overlays
4. Emotion Visuals — Feeling & intensity effects
5. Scream Visuals — Audio-reactive effects
6. Animated Overlays — Data-driven graphics
7. Style Presets — Signature look packages
"""

from app.effects.registry import EffectRegistry, get_registry
from app.effects.base import BaseEffect, EffectContext, EffectResult

__all__ = [
    "EffectRegistry",
    "get_registry",
    "BaseEffect",
    "EffectContext",
    "EffectResult",
]
