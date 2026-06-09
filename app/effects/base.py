"""Base classes for the video effects system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EffectStage(str, Enum):
    """When in the pipeline the effect is applied."""
    PER_CLIP = "per_clip"           # During _process_individual_clip
    POST_CONCAT = "post_concat"     # After concatenation, before final render
    FINAL = "final"                 # During final rendering pass


class EffectType(str, Enum):
    """What kind of visual effect this is."""
    FILTER = "filter"               # FFmpeg -vf filter chain addition
    OVERLAY = "overlay"             # Pillow-rendered frame sequence composited via overlay
    AUDIO_REACTIVE = "audio_reactive"  # Audio-analysis-driven filter params
    DATA_DRIVEN = "data_driven"     # Data-bound animated overlays (scores, names)


@dataclass
class EffectContext:
    """Everything an effect needs to know about the clip it's being applied to."""

    clip_path: str
    duration: float
    fps: int = 30
    width: int = 1080
    height: int = 1920
    intensity: float = 0.5         # 0.0–1.0, mapped from edit_style
    narrative_role: str = "build"  # hook/setup/build/climax/resolution/payoff
    visual_type: str = "action"    # action/reaction/crowd/wide/closeup/graphic/stock/tactical/archive
    effect_tags: List[str] = field(default_factory=list)  # from ClipPlan.effects
    audio_path: Optional[str] = None
    # Data for animated overlays
    team_home: str = ""
    team_away: str = ""
    score_home: int = 0
    score_away: int = 0
    player_name: str = ""
    player_number: int = 0
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EffectResult:
    """What an effect produces."""

    filters: List[str] = field(default_factory=list)
    # FFmpeg -vf filter strings to append

    overlay_frames_dir: Optional[str] = None
    # Path to directory of PNG frames for Pillow-rendered overlays

    overlay_blend: str = "normal"
    # Blend mode for overlay compositing (normal, additive, screen, multiply)

    pre_filters: List[str] = field(default_factory=list)
    # Filters that must come BEFORE the main filter chain (e.g. format conversion)

    audio_filters: List[str] = field(default_factory=list)
    # FFmpeg -af audio filter strings

    metadata: Dict[str, Any] = field(default_factory=dict)
    # Effect-specific metadata for pipeline coordination


class BaseEffect:
    """Abstract base class for all video effects.

    Subclass this, set class attributes, and implement ``build()``.
    """

    name: str = "base"
    label: str = "Base Effect"
    stage: EffectStage = EffectStage.PER_CLIP
    effect_type: EffectType = EffectType.FILTER
    description: str = ""

    # Which ClipPlan.effects tags this effect responds to
    handled_tags: List[str] = []

    def build(self, ctx: EffectContext) -> EffectResult:
        """Generate FFmpeg filter strings and/or overlay frames for the given context.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    def matches(self, effect_tags: List[str]) -> bool:
        """Return True if this effect should activate given the clip's effect tags."""
        return bool(set(self.handled_tags) & set(effect_tags))

    @staticmethod
    def scale(base: float, intensity: float) -> float:
        """Scale a parameter value by intensity (0.0–1.0)."""
        return base * intensity
