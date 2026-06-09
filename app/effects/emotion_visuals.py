"""Skill 4: Emotion Visuals — Feeling & intensity effects.

Adds visual intensity matching emotional tone: tension, anger, joy,
heartbreak, shock. Inferred from ClipPlan.narrative_role and visual_type.

Inspired by: Framer Motion variant state machine, React Spring damping,
GSAP ease curves, PixiJS vignette/glow filters, Lottie segment playback.
"""

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType
from app.effects.easing import ffmpeg_sine_expr, ffmpeg_vignette_expr


# ---------------------------------------------------------------------------
# Emotion state machine  (Framer Motion variant pattern)
# ---------------------------------------------------------------------------

EMOTION_PROFILES = {
    "tension": {"brightness_amp": 0.12, "brightness_freq": 3.0, "sat_shift": -0.1, "vig_base": 0.45, "vig_pulse": 0.1},
    "anger":   {"red_boost": 0.1, "contrast_boost": 0.3, "shake_amp": 4},
    "joy":     {"warm_r": 0.04, "warm_g": 0.02, "brightness_lift": 0.05, "sharpness": 2.0},
    "heartbreak": {"blue_shift": 0.05, "desat": 0.3, "blur": 1.5, "speed_factor": 0.5},
    "shock":  {"freeze_duration": 0.5, "flash_peak": 0.5},
    "energy": {"hue_rate": 2, "sat_boost": 0.15},
}

# Map narrative_role + visual_type → emotion
_ROLE_EMOTION = {
    "hook": "energy",
    "setup": "tension",
    "build": "tension",
    "climax": "shock",
    "resolution": "joy",
    "payoff": "joy",
}

_VISUAL_EMOTION = {
    "action": "energy",
    "reaction": "shock",
    "crowd": "energy",
    "closeup": "tension",
}


def infer_emotion(ctx: EffectContext) -> str:
    """Infer dominant emotion from clip context."""
    if ctx.extra_data.get("emotion"):
        return ctx.extra_data["emotion"]
    vis = _VISUAL_EMOTION.get(ctx.visual_type)
    role = _ROLE_EMOTION.get(ctx.narrative_role)
    return vis or role or "tension"


class TensionPulseEffect(BaseEffect):
    """Slow brightness oscillation + tightening vignette + desaturation."""

    name = "tension_pulse"
    label = "Tension Pulse"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Pulsing brightness/vignette for build-up tension"
    handled_tags = ["dramatic_pause", "slow_motion"]

    def build(self, ctx: EffectContext) -> EffectResult:
        profile = EMOTION_PROFILES["tension"]
        b_amp = self.scale(profile["brightness_amp"], ctx.intensity)
        b_freq = profile["brightness_freq"]
        sat_shift = self.scale(profile["sat_shift"], ctx.intensity)
        vig_base = profile["vig_base"] * ctx.intensity
        vig_pulse = self.scale(profile["vig_pulse"], ctx.intensity)
        bright_expr = f"1+{b_amp:.3f}*sin({b_freq:.1f}*2*PI*T)"
        vig_expr = ffmpeg_vignette_expr("T", vig_base, vig_pulse, 1.5)
        return EffectResult(
            filters=[
                f"eq=brightness='{bright_expr}':saturation='{1 + sat_shift:.2f}'",
                f"vignette=angle='{vig_expr}'",
            ],
        )


class AngerIntensifyEffect(BaseEffect):
    """Red channel boost + high contrast + slight shake."""

    name = "anger_intensify"
    label = "Anger Intensify"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Red tint + contrast for fouls, red cards"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        profile = EMOTION_PROFILES["anger"]
        red = self.scale(profile["red_boost"], ctx.intensity)
        contrast = 1.0 + self.scale(profile["contrast_boost"], ctx.intensity)
        return EffectResult(
            filters=[
                f"colorbalance=rs={red:.3f}",
                f"eq=contrast={contrast:.2f}",
            ],
        )


class HeartbreakEffect(BaseEffect):
    """Slow-mo + blur + cold blue tint + noise overlay for losses."""

    name = "heartbreak"
    label = "Heartbreak Slow-Mo"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Slow, cold, blurred look for losses and misses"
    handled_tags = ["slow_motion", "dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        profile = EMOTION_PROFILES["heartbreak"]
        speed = 1.0 - self.scale(1.0 - profile["speed_factor"], ctx.intensity)
        blue = self.scale(profile["blue_shift"], ctx.intensity)
        desat = self.scale(profile["desat"], ctx.intensity)
        blur = max(int(self.scale(profile["blur"], ctx.intensity)), 1)
        return EffectResult(
            filters=[
                f"setpts={1 / speed:.2f}*PTS",
                f"eq=saturation={1 - desat:.2f}",
                f"colorbalance=bs={blue:.3f}",
                f"boxblur={blur}:{blur}",
            ],
        )


class JoyBloomEffect(BaseEffect):
    """Warm color shift + glow + brightness lift for celebrations."""

    name = "joy_bloom"
    label = "Joy Bloom"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Warm glow for goals, wins, celebrations"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        profile = EMOTION_PROFILES["joy"]
        wr = self.scale(profile["warm_r"], ctx.intensity)
        wg = self.scale(profile["warm_g"], ctx.intensity)
        bl = self.scale(profile["brightness_lift"], ctx.intensity)
        sh = self.scale(profile["sharpness"], ctx.intensity)
        return EffectResult(
            filters=[
                f"colorbalance=rs={wr:.3f}:gs={wg:.3f}",
                f"eq=brightness={bl:.3f}",
                f"unsharp=6:6:{sh:.1f}:6:6:0",
            ],
        )


class ShockFreezeEffect(BaseEffect):
    """Freeze-frame hold then spring-snap back to motion."""

    name = "shock_freeze"
    label = "Shock Freeze-Frame"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Hold a single frame then snap back for upsets"
    handled_tags = ["freeze_frame", "dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        profile = EMOTION_PROFILES["shock"]
        freeze_s = self.scale(profile["freeze_duration"], ctx.intensity)
        # setpts: freeze for freeze_s seconds, then resume at 1.5x to catch up
        expr = (
            f"if(lt(T,{freeze_s:.2f}),"
            f"{freeze_s:.2f},"
            f"T-({freeze_s:.2f})*(1-1/{1.5:.1f}))"
        )
        return EffectResult(filters=[f"setpts={expr}*PTS"])


class CrowdEnergyEffect(BaseEffect):
    """Hue rotation cycling + saturation boost for crowd/stadium shots."""

    name = "crowd_energy"
    label = "Crowd Energy Wave"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Subtle hue cycling and saturation boost for crowd shots"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        profile = EMOTION_PROFILES["energy"]
        hue_rate = self.scale(profile["hue_rate"], ctx.intensity)
        sat_boost = self.scale(profile["sat_boost"], ctx.intensity)
        return EffectResult(
            filters=[
                f"hue=h={hue_rate:.1f}*sin(2*PI*T/3)",
                f"eq=saturation={1 + sat_boost:.2f}",
            ],
        )


# ---------------------------------------------------------------------------
# Auto-apply helper — emotion effects activate based on context, not just tags
# ---------------------------------------------------------------------------

EMOTION_EFFECT_MAP = {
    "tension": [TensionPulseEffect],
    "anger": [AngerIntensifyEffect],
    "joy": [JoyBloomEffect],
    "heartbreak": [HeartbreakEffect],
    "shock": [ShockFreezeEffect],
    "energy": [CrowdEnergyEffect],
}


def get_emotion_effects_for_context(ctx: EffectContext) -> list:
    """Return the emotion effect class(es) matching this clip's inferred emotion."""
    emotion = infer_emotion(ctx)
    return EMOTION_EFFECT_MAP.get(emotion, [])


ALL_EMOTION_EFFECTS = [
    TensionPulseEffect,
    AngerIntensifyEffect,
    HeartbreakEffect,
    JoyBloomEffect,
    ShockFreezeEffect,
    CrowdEnergyEffect,
]
