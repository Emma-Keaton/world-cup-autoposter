"""Skill 1: Shot Visuals — Impact & camera effects.

Adds punch to key moments: zoom snaps, screen shake, chromatic aberration,
strobe flash, speed ramp, and directional motion blur.

Inspired by: GSAP easing/scrub, PixiJS displacement/chromatic shaders, Three.js bloom.
"""

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType
from app.effects.easing import (
    ffmpeg_shake_expr,
    ffmpeg_spring_zoom_expr,
    power2_out,
    expo_out,
)


class ImpactZoomEffect(BaseEffect):
    """Spring-eased zoom punch — fast snap in, slow settle out."""

    name = "impact_zoom"
    label = "Impact Zoom Punch"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Fast zoom snap with spring-settle, for goals and big saves"
    handled_tags = ["zoom_in", "dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        intensity = ctx.intensity
        peak = 1.0 + self.scale(0.35, intensity)
        settle = 1.0 + self.scale(0.18, intensity)
        punch_frames = max(int(6 * (1 - intensity * 0.3)), 3)
        settle_frames = max(int(25 * intensity), 10)
        expr = ffmpeg_spring_zoom_expr(
            start_zoom=1.0,
            peak_zoom=peak,
            settle_zoom=settle,
            punch_frames=punch_frames,
            settle_frames=settle_frames,
        )
        return EffectResult(
            filters=[f"zoompan=z='{expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={ctx.width}x{ctx.height}"],
            metadata={"peak_zoom": peak, "settle_zoom": settle},
        )


class ScreenShakeEffect(BaseEffect):
    """Decaying screen shake on hard shots, fouls, collisions."""

    name = "screen_shake"
    label = "Screen Shake"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Decaying random shake for impact moments"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        amplitude = self.scale(10, ctx.intensity)
        frequency = 15 + ctx.intensity * 10
        decay = 3 + ctx.intensity * 2
        dur_frames = int(15 + 10 * ctx.intensity)
        shake_x = ffmpeg_shake_expr("x", amplitude, frequency, decay, 0, dur_frames)
        shake_y = ffmpeg_shake_expr("y", amplitude * 0.7, frequency * 1.1, decay, 0, dur_frames)
        return EffectResult(
            pre_filters=[f"pad={ctx.width + int(amplitude * 2)}:{ctx.height + int(amplitude * 2)}:(ow-iw)/2:(oh-ih)/2"],
            filters=[f"crop={ctx.width}:{ctx.height}:'{shake_x}':'{shake_y}'"],
        )


class ChromaticAberrationEffect(BaseEffect):
    """Split R/B channel offset with exponential decay — glitch/impact feel."""

    name = "chromatic_aberration"
    label = "Chromatic Aberration Flash"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "RGB channel split with decay for red cards, penalties"
    handled_tags = ["dramatic_pause", "freeze_frame"]

    def build(self, ctx: EffectContext) -> EffectResult:
        max_offset = max(int(self.scale(6, ctx.intensity)), 1)
        decay_frames = int(20 + 15 * ctx.intensity)
        # Use libswscale channel extraction + merge via geq
        expr_r = f"if(lte(on,{decay_frames}),p({max_offset},0),p(0,0))"
        expr_g = "p(0,0)"
        expr_b = f"if(lte(on,{decay_frames}),p(-{max_offset},0),p(0,0))"
        return EffectResult(
            pre_filters=["format=rgba"],
            filters=[
                f"geq=r='{expr_r}':g='{expr_g}':b='{expr_b}':a='alpha(X,Y)'"
            ],
        )


class StrobeFlashEffect(BaseEffect):
    """Rapid brightness pulsing — strobe on dramatic moments."""

    name = "strobe_flash"
    label = "Strobe Flash"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Rapid brightness pulses for dramatic moments"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        pulse_count = max(int(3 + 2 * ctx.intensity), 2)
        pulse_dur = 0.05 + 0.03 * (1 - ctx.intensity)
        total_dur = pulse_count * pulse_dur * 2
        # Build expression: brightness oscillates 1.0 ↔ 1.8 at high frequency for total_dur seconds
        expr = (
            f"if(lt(t,{total_dur:.3f}),"
            f"1+{self.scale(0.8, ctx.intensity):.2f}*0.5*(1+sin(2*PI*{pulse_count}/{total_dur:.3f}*t)),1)"
        )
        return EffectResult(filters=[f"eq=brightness='{expr}'"])


class SpeedRampEffect(BaseEffect):
    """Exponential speed ramp — ease-in acceleration then hard cut to normal."""

    name = "speed_ramp"
    label = "Speed Ramp"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Smooth acceleration then snap to normal speed"
    handled_tags = ["speed_ramp", "fast_pace"]

    def build(self, ctx: EffectContext) -> EffectResult:
        max_speed = 1.0 + self.scale(0.4, ctx.intensity)
        ramp_duration = 0.3 + 0.2 * (1 - ctx.intensity)
        # Use setpts with time-dependent speed: starts fast, decays to 1.0
        expr = (
            f"if(lt(T,{ramp_duration:.2f}),"
            f"{max_speed:.2f}-{max_speed - 1:.2f}*T/{ramp_duration:.2f},"
            f"1.0)"
        )
        return EffectResult(
            filters=[f"setpts=PTS/{expr}"],
            audio_filters=[f"atempo={min(max_speed, 2.0):.2f}"],
        )


class MotionBlurEffect(BaseEffect):
    """Directional motion blur via frame blending — streaks on fast movement."""

    name = "motion_blur"
    label = "Directional Motion Blur"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Directional streak blur on fast passes, sprints"
    handled_tags = ["motion_blur"]

    def build(self, ctx: EffectContext) -> EffectResult:
        blur_amount = int(self.scale(4, ctx.intensity))
        if blur_amount < 1:
            return EffectResult()
        return EffectResult(
            filters=[
                f"tblend=all_mode=difference128",
                f"minterpolate=fps={ctx.fps}",
            ],
        )


# ---------------------------------------------------------------------------
# All effects in this skill — imported by registry auto-discovery
# ---------------------------------------------------------------------------

ALL_SHOT_EFFECTS = [
    ImpactZoomEffect,
    ScreenShakeEffect,
    ChromaticAberrationEffect,
    StrobeFlashEffect,
    SpeedRampEffect,
    MotionBlurEffect,
]
